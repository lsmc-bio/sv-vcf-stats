#!/usr/bin/env python3
"""Build aggregate SBOM, checksum, and SLSA/in-toto candidate evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tarfile
import uuid
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import IO, Any, cast

from tools.build_sbom import _wheel_version
from tools.verify_test_data import verify as verify_test_data
from vcf_sv_stats.exceptions import UsageError
from vcf_sv_stats.fixture_review import load_review, verify_review
from vcf_sv_stats.serialization import (
    file_sha256,
    write_bytes_atomic,
    write_json_atomic,
)

LOCK_PATTERN = re.compile(r"^([a-z0-9][a-z0-9-]*)==([^ ;]+)(?:\s*;\s*(.+))?$")


def _file_sha1(path: Path) -> str:
    digest = hashlib.sha1(usedforsecurity=False)
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _stream_sha256(handle: IO[bytes]) -> str:
    digest = hashlib.sha256()
    while chunk := handle.read(1024 * 1024):
        digest.update(chunk)
    return digest.hexdigest()


def _sdist_metadata_member(archive: tarfile.TarFile) -> tuple[str, tarfile.TarInfo]:
    members = archive.getmembers()
    candidates = []
    for member in members:
        parts = PurePosixPath(member.name).parts
        if len(parts) == 2 and parts[1] == "PKG-INFO":
            candidates.append((parts[0], member))
    if len(candidates) != 1:
        raise UsageError("source archive must contain exactly one PKG-INFO")
    package_root, member = candidates[0]
    if (
        re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", package_root) is None
        or member.name != f"{package_root}/PKG-INFO"
        or not member.isfile()
    ):
        raise UsageError("source archive package root is unsafe")
    observed: set[str] = set()
    for archive_member in members:
        archive_path = PurePosixPath(archive_member.name)
        canonical_name = archive_path.as_posix()
        supplied_name = (
            archive_member.name.rstrip("/") if archive_member.isdir() else archive_member.name
        )
        if (
            not archive_path.parts
            or archive_path.parts[0] != package_root
            or ".." in archive_path.parts
            or supplied_name != canonical_name
        ):
            raise UsageError("source archive contains an unsafe member path")
        if canonical_name in observed:
            raise UsageError("source archive contains a duplicate member path")
        observed.add(canonical_name)
        if not archive_member.isfile() and not archive_member.isdir():
            raise UsageError("source archive contains a non-regular member")
    return package_root, member


def _sdist_version(sdist: Path) -> str:
    with tarfile.open(sdist, "r:gz") as archive:
        _, metadata_member = _sdist_metadata_member(archive)
        handle = archive.extractfile(metadata_member)
        if handle is None:
            raise UsageError("source archive PKG-INFO is unreadable")
        with handle:
            text = handle.read().decode("utf-8")
    version_lines = [
        line.partition(":")[2].strip() for line in text.splitlines() if line.startswith("Version:")
    ]
    if len(version_lines) != 1:
        raise UsageError("source archive must declare exactly one version")
    return version_lines[0]


def _verify_sdist_fixture_tree(sdist: Path, fixture_root: Path) -> None:
    expected: dict[str, tuple[int, str]] = {}
    for path in sorted(fixture_root.rglob("*")):
        if path.is_symlink():
            raise UsageError("reviewed fixture corpus contains a symbolic link")
        if path.is_file():
            expected[path.relative_to(fixture_root).as_posix()] = (
                path.stat().st_size,
                file_sha256(path),
            )
    if not expected:
        raise UsageError("reviewed fixture corpus is empty")

    observed: set[str] = set()
    with tarfile.open(sdist, "r:gz") as archive:
        package_root, _ = _sdist_metadata_member(archive)
        prefix = f"{package_root}/test_data/"
        for member in archive.getmembers():
            if not member.name.startswith(prefix):
                continue
            relative_name = member.name.removeprefix(prefix)
            relative = PurePosixPath(relative_name)
            if (
                not relative_name
                or relative.is_absolute()
                or ".." in relative.parts
                or relative.as_posix() != relative_name
            ):
                raise UsageError("source archive fixture path is unsafe")
            if member.isdir():
                continue
            if not member.isfile():
                raise UsageError("source archive fixture member is not a regular file")
            if relative_name in observed:
                raise UsageError("source archive fixture path is duplicated")
            observed.add(relative_name)
            expected_entry = expected.get(relative_name)
            if expected_entry is None or member.size != expected_entry[0]:
                raise UsageError(
                    "source archive fixture corpus does not exactly match reviewed checkout"
                )
            handle = archive.extractfile(member)
            if handle is None:
                raise UsageError("source archive fixture member is unreadable")
            with handle:
                observed_digest = _stream_sha256(handle)
            if observed_digest != expected_entry[1]:
                raise UsageError(
                    "source archive fixture corpus does not exactly match reviewed checkout"
                )
    if observed != set(expected):
        raise UsageError("source archive fixture corpus does not exactly match reviewed checkout")


def _locked_packages(lock: Path) -> list[dict[str, str]]:
    packages = []
    for line in lock.read_text(encoding="utf-8").splitlines():
        match = LOCK_PATTERN.fullmatch(line.strip())
        if match is not None:
            value = {"name": match.group(1), "version": match.group(2)}
            if match.group(3) is not None:
                value["marker"] = match.group(3)
            packages.append(value)
    if not packages:
        raise UsageError("runtime lock contains no exact packages")
    return packages


def _inventory(inventory_path: Path, lock_path: Path) -> dict[str, Any]:
    value = cast(dict[str, Any], json.loads(inventory_path.read_text(encoding="utf-8")))
    locked = _locked_packages(lock_path)
    declared = [
        {key: item[key] for key in ("name", "version", "marker") if key in item}
        for item in value["python"]
    ]
    if declared != locked:
        raise UsageError("runtime license inventory does not exactly match the lock")
    return value


def _license(expression: str) -> dict[str, Any]:
    if " AND " in expression or " OR " in expression or expression.startswith("LicenseRef-"):
        return {"expression": expression}
    return {"license": {"id": expression}}


def _component(item: dict[str, Any], *, kind: str = "library") -> dict[str, Any]:
    purl = f"pkg:pypi/{item['name']}@{item['version']}" if kind == "library" else None
    value: dict[str, Any] = {
        "type": kind,
        "bom-ref": f"component:{item['name']}:{item['version']}",
        "name": item["name"],
        "version": item["version"],
        "licenses": [_license(item["license_expression"])],
    }
    if purl is not None:
        value["purl"] = purl
    if item.get("marker"):
        value["properties"] = [{"name": "vcf-sv-stats:environment-marker", "value": item["marker"]}]
    return value


def _spdx_package(item: dict[str, Any], ordinal: int, *, prefix: str) -> dict[str, Any]:
    return {
        "SPDXID": f"SPDXRef-{prefix}-{ordinal}",
        "name": item["name"],
        "versionInfo": item["version"],
        "downloadLocation": "NOASSERTION",
        "filesAnalyzed": False,
        "licenseConcluded": item["license_expression"],
        "licenseDeclared": item["license_expression"],
        "copyrightText": "NOASSERTION",
    }


def _artifact(path: Path, *, media_type: str) -> dict[str, Any]:
    return {
        "name": path.name,
        "sha256": file_sha256(path),
        "bytes": path.stat().st_size,
        "media_type": media_type,
    }


def build(
    *,
    wheel: Path,
    sdist: Path,
    output_dir: Path,
    source_commit: str,
    created: str,
    invocation_id: str,
    oci_archive: Path | None = None,
    oci_audit: Path | None = None,
) -> dict[str, Path]:
    """Build deterministic, unsigned release-candidate evidence."""
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise UsageError("source_commit must be a full lowercase Git commit digest")
    try:
        parsed_created = datetime.fromisoformat(created.replace("Z", "+00:00"))
    except ValueError as exc:
        raise UsageError("created must be an RFC 3339 timestamp") from exc
    if parsed_created.tzinfo is None:
        raise UsageError("created timestamp must include a timezone")
    canonical_created = parsed_created.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if not output_dir.is_dir():
        raise UsageError("output directory must already exist")
    version = _wheel_version(wheel)
    if _sdist_version(sdist) != version:
        raise UsageError("wheel and source archive versions differ")
    root = Path(__file__).parents[1]
    inventory = _inventory(root / "packaging/runtime-licenses.json", root / "requirements.lock.txt")
    try:
        verify_test_data(root / "test_data")
    except ValueError as exc:
        raise UsageError("fixture corpus failed strict release verification") from exc
    fixture_manifest = root / "test_data/manifest.json"
    fixture_value = cast(dict[str, Any], json.loads(fixture_manifest.read_text(encoding="utf-8")))
    try:
        verify_review(
            fixture_value,
            load_review(root / "test_data/redistribution-review.json"),
        )
    except ValueError as exc:
        raise UsageError("fixture redistribution review does not bind this manifest") from exc
    fixture_subjects = sorted(
        {
            str(item["subject"])
            for item in [*fixture_value["fixtures"], *fixture_value["derived_parity_artifacts"]]
        }
    )
    if fixture_subjects != ["HG002"]:
        raise UsageError("fixture license evidence is not terminal and single-subject")
    _verify_sdist_fixture_tree(sdist, root / "test_data")

    artifacts = [
        _artifact(wheel, media_type="application/vnd.python.wheel"),
        _artifact(sdist, media_type="application/gzip"),
    ]
    oci_value: dict[str, Any] | None = None
    if (oci_archive is None) != (oci_audit is None):
        raise UsageError("OCI archive and audit must be provided together")
    if oci_archive is not None and oci_audit is not None:
        oci_value = cast(dict[str, Any], json.loads(oci_audit.read_text(encoding="utf-8")))
        if file_sha256(oci_archive) != oci_value["archive_sha256"]:
            raise UsageError("OCI archive does not match its audit")
        artifacts.append(
            _artifact(oci_archive, media_type="application/vnd.oci.image.layout.v1.tar")
        )

    python_components = [_component(item) for item in inventory["python"]]
    native_components = [_component(item) for item in inventory["native"]]
    fixture_component = {
        "type": "data",
        "bom-ref": "component:sanitized-hg002-test-fixtures:1",
        "name": inventory["fixtures"]["name"],
        "version": "1",
        "hashes": [{"alg": "SHA-256", "content": file_sha256(fixture_manifest)}],
        "licenses": [_license(inventory["fixtures"]["license_expression"])],
        "properties": [
            {"name": "vcf-sv-stats:subject", "value": "HG002"},
            {"name": "vcf-sv-stats:public-release-review-required", "value": "false"},
        ],
    }
    artifact_components = [
        {
            "type": "file",
            "bom-ref": f"artifact:{item['sha256']}",
            "name": item["name"],
            "version": version,
            "hashes": [{"alg": "SHA-256", "content": item["sha256"]}],
        }
        for item in artifacts
    ]
    project_ref = f"pkg:pypi/vcf-sv-stats@{version}"
    cdx: dict[str, Any] = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, source_commit + version)}",
        "version": 1,
        "metadata": {
            "timestamp": canonical_created,
            "tools": {
                "components": [
                    {"type": "application", "name": "vcf-sv-stats release evidence", "version": "1"}
                ]
            },
            "component": {
                "type": "application",
                "bom-ref": project_ref,
                "name": "vcf-sv-stats",
                "version": version,
                "purl": project_ref,
                "licenses": [_license(inventory["project"]["license_expression"])],
            },
        },
        "components": [
            *python_components,
            *native_components,
            fixture_component,
            *artifact_components,
        ],
        "dependencies": [
            {
                "ref": project_ref,
                "dependsOn": [
                    item["bom-ref"]
                    for item in [*python_components, *native_components, fixture_component]
                ],
            }
        ],
    }
    cdx_path = output_dir / "candidate.cyclonedx.json"
    write_json_atomic(cdx_path, cdx)

    project_item = {"name": "vcf-sv-stats", "version": version, "license_expression": "Apache-2.0"}
    spdx_packages = [_spdx_package(project_item, 0, prefix="Project")]
    spdx_packages.extend(
        _spdx_package(item, ordinal, prefix="Python")
        for ordinal, item in enumerate(inventory["python"], start=1)
    )
    native_start = len(spdx_packages)
    spdx_packages.extend(
        _spdx_package(item, ordinal, prefix="Native")
        for ordinal, item in enumerate(inventory["native"], start=1)
    )
    fixture_spdx = {
        "SPDXID": "SPDXRef-Fixtures",
        "name": inventory["fixtures"]["name"],
        "versionInfo": "1",
        "downloadLocation": "NOASSERTION",
        "filesAnalyzed": False,
        "licenseConcluded": inventory["fixtures"]["license_expression"],
        "licenseDeclared": inventory["fixtures"]["license_expression"],
        "copyrightText": "NOASSERTION",
        "checksums": [{"algorithm": "SHA256", "checksumValue": file_sha256(fixture_manifest)}],
    }
    spdx_packages.append(fixture_spdx)
    spdx_files = [
        {
            "SPDXID": f"SPDXRef-Artifact-{ordinal}",
            "fileName": item["name"],
            "checksums": [
                {"algorithm": "SHA1", "checksumValue": _file_sha1(path)},
                {"algorithm": "SHA256", "checksumValue": item["sha256"]},
            ],
            "licenseConcluded": "NOASSERTION",
            "copyrightText": "NOASSERTION",
        }
        for ordinal, (item, path) in enumerate(
            zip(
                artifacts,
                (wheel, sdist, *(value for value in (oci_archive,) if value is not None)),
                strict=True,
            ),
            start=1,
        )
    ]
    dependency_ids = [item["SPDXID"] for item in spdx_packages[1:]]
    spdx: dict[str, Any] = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"vcf-sv-stats-{version}-candidate",
        "documentNamespace": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_OID, source_commit + version)}",
        "creationInfo": {
            "created": canonical_created,
            "creators": ["Tool: vcf-sv-stats-release-evidence-1"],
        },
        "packages": spdx_packages,
        "files": spdx_files,
        "relationships": [
            {
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relationshipType": "DESCRIBES",
                "relatedSpdxElement": "SPDXRef-Project-0",
            },
            *(
                {
                    "spdxElementId": "SPDXRef-Project-0",
                    "relationshipType": "DEPENDS_ON",
                    "relatedSpdxElement": identifier,
                }
                for identifier in dependency_ids
            ),
            *(
                {
                    "spdxElementId": "SPDXRef-Project-0",
                    "relationshipType": "GENERATES",
                    "relatedSpdxElement": item["SPDXID"],
                }
                for item in spdx_files
            ),
        ],
        "annotations": [
            {
                "annotationDate": canonical_created,
                "annotationType": "OTHER",
                "annotator": "Tool: vcf-sv-stats-release-evidence-1",
                "comment": (
                    f"Native component package index begins at {native_start}; "
                    "fixture redistribution is reviewed; publication approval remains required."
                ),
            }
        ],
        "hasExtractedLicensingInfos": [
            {
                "licenseId": "LicenseRef-Public-Data-Redistribution-Reviewed",
                "extractedText": (
                    "Public HG002-derived fixture redistribution was reviewed for this "
                    "public release candidate. Publication remains a separately approved gate."
                ),
                "name": "Public data redistribution review",
            }
        ],
    }
    spdx_path = output_dir / "candidate.spdx.json"
    write_json_atomic(spdx_path, spdx)

    subjects = [{"name": item["name"], "digest": {"sha256": item["sha256"]}} for item in artifacts]
    if oci_value is not None:
        subjects.append(
            {
                "name": "oci-image-index",
                "digest": {"sha256": oci_value["root_digest"].removeprefix("sha256:")},
            }
        )
    predicate = {
        "buildDefinition": {
            "buildType": "urn:vcf-sv-stats:build:release-candidate:1",
            "externalParameters": {"version": version, "publication": False},
            "internalParameters": {"source_commit": source_commit},
            "resolvedDependencies": [
                {"uri": "urn:vcf-sv-stats:source", "digest": {"gitCommit": source_commit}},
                {
                    "uri": "urn:vcf-sv-stats:runtime-lock",
                    "digest": {"sha256": file_sha256(root / "requirements.lock.txt")},
                },
                {
                    "uri": "urn:vcf-sv-stats:fixtures",
                    "digest": {"sha256": file_sha256(fixture_manifest)},
                },
            ],
        },
        "runDetails": {
            "builder": {"id": "urn:vcf-sv-stats:builder:github-actions"},
            "metadata": {
                "invocationId": invocation_id,
                "startedOn": canonical_created,
                "finishedOn": canonical_created,
            },
            "byproducts": [
                {"name": cdx_path.name, "digest": {"sha256": file_sha256(cdx_path)}},
                {"name": spdx_path.name, "digest": {"sha256": file_sha256(spdx_path)}},
            ],
        },
    }
    provenance = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": subjects,
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": predicate,
    }
    provenance_path = output_dir / "candidate.provenance.intoto.json"
    predicate_path = output_dir / "candidate.provenance-predicate.json"
    write_json_atomic(provenance_path, provenance)
    write_json_atomic(predicate_path, predicate)

    evidence_files = [
        wheel,
        sdist,
        *(value for value in (oci_archive, oci_audit) if value is not None),
        cdx_path,
        spdx_path,
        provenance_path,
        predicate_path,
    ]
    checksum_lines = [
        f"{file_sha256(item)}  {item.name}"
        for item in sorted(evidence_files, key=lambda item: item.name)
    ]
    checksum_path = output_dir / "candidate.checksums.txt"
    write_bytes_atomic(checksum_path, ("\n".join(checksum_lines) + "\n").encode())
    return {
        "cyclonedx": cdx_path,
        "spdx": spdx_path,
        "provenance": provenance_path,
        "predicate": predicate_path,
        "checksums": checksum_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--sdist", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--created", required=True)
    parser.add_argument("--invocation-id", required=True)
    parser.add_argument("--oci-archive", type=Path)
    parser.add_argument("--oci-audit", type=Path)
    args = parser.parse_args()
    result = build(
        wheel=args.wheel.resolve(strict=True),
        sdist=args.sdist.resolve(strict=True),
        output_dir=args.output_dir.resolve(strict=True),
        source_commit=args.source_commit,
        created=args.created,
        invocation_id=args.invocation_id,
        oci_archive=None if args.oci_archive is None else args.oci_archive.resolve(strict=True),
        oci_audit=None if args.oci_audit is None else args.oci_audit.resolve(strict=True),
    )
    print(json.dumps({key: value.name for key, value in result.items()}, sort_keys=True))


if __name__ == "__main__":
    main()
