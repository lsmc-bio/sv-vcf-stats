#!/usr/bin/env python3
"""Audit a multi-architecture OCI archive and its BuildKit attestations."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import tarfile
from pathlib import Path
from typing import Any, cast

from vcf_sv_stats.exceptions import UsageError
from vcf_sv_stats.schemas import validate_artifact
from vcf_sv_stats.serialization import file_sha256, payload_sha256, write_json_atomic

REFERENCE_PATH = re.compile(r"(?:^|/)(?:reference|genome)\.(?:fa|fasta|fna)(?:\.|$)", re.I)
SBOM_PREDICATE = "https://spdx.dev/Document"
PROVENANCE_PREFIX = "https://slsa.dev/provenance/"


class OciArchive:
    def __init__(self, path: Path):
        self.path = path
        self.archive = tarfile.open(path, "r")  # noqa: SIM115 - lifetime is managed by close()
        self.members = {member.name.removeprefix("./"): member for member in self.archive}

    def close(self) -> None:
        self.archive.close()

    def _read(self, name: str) -> bytes:
        try:
            member = self.members[name]
        except KeyError as exc:
            raise UsageError(f"OCI archive member is missing: {name}") from exc
        handle = self.archive.extractfile(member)
        if handle is None:
            raise UsageError(f"OCI archive member is unreadable: {name}")
        return handle.read()

    def index(self) -> tuple[bytes, dict[str, Any]]:
        content = self._read("index.json")
        return content, cast(dict[str, Any], json.loads(content))

    def blob_bytes(self, digest: str) -> bytes:
        algorithm, separator, value = digest.partition(":")
        if separator != ":" or algorithm != "sha256" or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise UsageError("OCI descriptor has an invalid digest")
        content = self._read(f"blobs/{algorithm}/{value}")
        if hashlib.sha256(content).hexdigest() != value:
            raise UsageError("OCI blob digest does not match its descriptor")
        return content

    def blob_json(self, digest: str) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(self.blob_bytes(digest)))


def _layer_paths(content: bytes) -> list[str]:
    paths: list[str] = []
    try:
        with tarfile.open(fileobj=io.BytesIO(content), mode="r:*") as layer:
            for member in layer:
                normalized = member.name.removeprefix("./")
                if REFERENCE_PATH.search(normalized):
                    paths.append(normalized)
    except tarfile.TarError as exc:
        raise UsageError("OCI filesystem layer is not a supported tar archive") from exc
    return sorted(paths)


def _attestation_statements(
    archive: OciArchive,
    descriptor: dict[str, Any],
) -> list[dict[str, Any]]:
    manifest = archive.blob_json(str(descriptor["digest"]))
    statements = []
    for layer in manifest.get("layers", []):
        if layer.get("mediaType") != "application/vnd.in-toto+json":
            continue
        content = archive.blob_bytes(str(layer["digest"]))
        value = cast(dict[str, Any], json.loads(content))
        statements.append(
            {
                "predicate_type": str(value.get("predicateType", "")),
                "statement_sha256": hashlib.sha256(content).hexdigest(),
                "statement": value,
            }
        )
    return statements


def audit(archive_path: Path, *, attestation_dir: Path | None = None) -> dict[str, Any]:
    """Verify image platforms, runtime config, layers, and per-platform attestations."""
    if attestation_dir is not None and not attestation_dir.is_dir():
        raise UsageError("attestation directory must already exist")
    archive_path = archive_path.resolve(strict=True)
    archive = OciArchive(archive_path)
    try:
        index_bytes, index = archive.index()
        layout_descriptors = cast(list[dict[str, Any]], index.get("manifests", []))
        if (
            len(layout_descriptors) == 1
            and layout_descriptors[0].get("mediaType")
            == "application/vnd.oci.image.index.v1+json"
        ):
            root_digest = str(layout_descriptors[0]["digest"])
            image_index = archive.blob_json(root_digest)
            descriptors = cast(list[dict[str, Any]], image_index.get("manifests", []))
        else:
            root_digest = f"sha256:{hashlib.sha256(index_bytes).hexdigest()}"
            descriptors = layout_descriptors
        image_descriptors = [
            item
            for item in descriptors
            if item.get("platform", {}).get("architecture") in {"amd64", "arm64"}
            and item.get("platform", {}).get("os") == "linux"
        ]
        attestation_descriptors = [
            item
            for item in descriptors
            if item.get("annotations", {}).get("vnd.docker.reference.type")
            == "attestation-manifest"
        ]
        if len(image_descriptors) != 2:
            raise UsageError("OCI archive must contain exactly linux/amd64 and linux/arm64 images")

        statements_by_subject: dict[str, list[dict[str, Any]]] = {}
        for descriptor in attestation_descriptors:
            subject = str(descriptor.get("annotations", {}).get("vnd.docker.reference.digest", ""))
            statements_by_subject.setdefault(subject, []).extend(
                _attestation_statements(archive, descriptor)
            )

        seen_layers: set[str] = set()
        platform_results = []
        for descriptor in sorted(
            image_descriptors, key=lambda item: str(item["platform"]["architecture"])
        ):
            manifest_digest = str(descriptor["digest"])
            manifest = archive.blob_json(manifest_digest)
            config = archive.blob_json(str(manifest["config"]["digest"]))
            runtime = cast(dict[str, Any], config.get("config", {}))
            user = str(runtime.get("User", ""))
            if user in {"", "0", "root"}:
                raise UsageError("OCI runtime user is not non-root")
            if runtime.get("WorkingDir") != "/work" or runtime.get("Entrypoint") != [
                "vcf-sv-stats"
            ]:
                raise UsageError("OCI runtime entry point or working directory differs")
            reference_paths = []
            for layer in manifest.get("layers", []):
                digest = str(layer["digest"])
                if digest in seen_layers:
                    continue
                seen_layers.add(digest)
                reference_paths.extend(_layer_paths(archive.blob_bytes(digest)))
            statements = statements_by_subject.get(manifest_digest, [])
            predicate_types = sorted({item["predicate_type"] for item in statements})
            if SBOM_PREDICATE not in predicate_types:
                raise UsageError("OCI platform is missing its SPDX attestation")
            if not any(value.startswith(PROVENANCE_PREFIX) for value in predicate_types):
                raise UsageError("OCI platform is missing its provenance attestation")
            if reference_paths:
                raise UsageError("OCI image contains a reference-like path")
            platform_name = f"linux-{descriptor['platform']['architecture']}"
            if attestation_dir is not None:
                for item in statements:
                    suffix = (
                        "spdx"
                        if item["predicate_type"] == SBOM_PREDICATE
                        else "provenance"
                        if item["predicate_type"].startswith(PROVENANCE_PREFIX)
                        else "attestation"
                    )
                    write_json_atomic(
                        attestation_dir / f"{platform_name}.container.{suffix}.json",
                        item["statement"],
                    )
            platform_results.append(
                {
                    "platform": f"linux/{descriptor['platform']['architecture']}",
                    "manifest_digest": manifest_digest,
                    "config_digest": str(manifest["config"]["digest"]),
                    "user": user,
                    "working_directory": str(runtime["WorkingDir"]),
                    "entrypoint": list(runtime["Entrypoint"]),
                    "layer_count": len(manifest.get("layers", [])),
                    "reference_like_paths": reference_paths,
                    "attestation_predicate_types": predicate_types,
                    "attestation_statement_sha256": sorted(
                        item["statement_sha256"] for item in statements
                    ),
                }
            )
    finally:
        archive.close()

    value: dict[str, Any] = {
        "schema_name": "vcf-sv-stats.oci-audit",
        "schema_version": "1.0.0",
        "archive_name": archive_path.name,
        "archive_bytes": archive_path.stat().st_size,
        "archive_sha256": file_sha256(archive_path),
        "root_digest": root_digest,
        "platforms": platform_results,
        "checks": {
            "exact_platforms": True,
            "non_root": True,
            "fixed_entrypoint": True,
            "reference_absent": True,
            "spdx_attestation_per_platform": True,
            "provenance_attestation_per_platform": True,
        },
    }
    value["receipt_sha256"] = payload_sha256(value)
    validate_artifact("oci-audit", value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--attestation-dir", type=Path)
    args = parser.parse_args()
    write_json_atomic(
        args.output,
        audit(args.archive, attestation_dir=args.attestation_dir),
    )


if __name__ == "__main__":
    main()
