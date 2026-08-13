from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path
from typing import Any

from tools.audit_oci import PROVENANCE_PREFIX, SBOM_PREDICATE, audit
from vcf_sv_stats.schemas import validate_artifact


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode()


def _blob(root: Path, content: bytes) -> dict[str, Any]:
    digest = hashlib.sha256(content).hexdigest()
    destination = root / "blobs/sha256" / digest
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return {"digest": f"sha256:{digest}", "size": len(content)}


def _oci_archive(directory: Path) -> Path:
    layout = directory / "layout"
    layout.mkdir()
    (layout / "oci-layout").write_text('{"imageLayoutVersion":"1.0.0"}', encoding="utf-8")
    layer_buffer = io.BytesIO()
    with tarfile.open(fileobj=layer_buffer, mode="w:gz"):
        pass
    layer = _blob(layout, layer_buffer.getvalue())
    config_blob = _blob(layout, b"{}")
    descriptors = []
    for architecture in ("amd64", "arm64"):
        config = _blob(
            layout,
            _json_bytes(
                {
                    "architecture": architecture,
                    "os": "linux",
                    "config": {
                        "User": "app",
                        "WorkingDir": "/work",
                        "Entrypoint": ["vcf-sv-stats"],
                    },
                }
            ),
        )
        image_manifest = _blob(
            layout,
            _json_bytes(
                {
                    "schemaVersion": 2,
                    "config": {
                        **config,
                        "mediaType": "application/vnd.oci.image.config.v1+json",
                    },
                    "layers": [
                        {
                            **layer,
                            "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                        }
                    ],
                }
            ),
        )
        image_descriptor = {
            **image_manifest,
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "platform": {"os": "linux", "architecture": architecture},
        }
        descriptors.append(image_descriptor)
        subject_digest = image_manifest["digest"].removeprefix("sha256:")
        statements = []
        for predicate_type, predicate in (
            (SBOM_PREDICATE, {"spdxVersion": "SPDX-2.3"}),
            (f"{PROVENANCE_PREFIX}v1", {"buildDefinition": {}, "runDetails": {}}),
        ):
            statement = _blob(
                layout,
                _json_bytes(
                    {
                        "_type": "https://in-toto.io/Statement/v1",
                        "subject": [{"name": "", "digest": {"sha256": subject_digest}}],
                        "predicateType": predicate_type,
                        "predicate": predicate,
                    }
                ),
            )
            statements.append({**statement, "mediaType": "application/vnd.in-toto+json"})
        attestation_manifest = _blob(
            layout,
            _json_bytes(
                {
                    "schemaVersion": 2,
                    "config": {
                        **config_blob,
                        "mediaType": "application/vnd.oci.empty.v1+json",
                    },
                    "layers": statements,
                }
            ),
        )
        descriptors.append(
            {
                **attestation_manifest,
                "mediaType": "application/vnd.oci.image.manifest.v1+json",
                "platform": {"os": "unknown", "architecture": "unknown"},
                "annotations": {
                    "vnd.docker.reference.digest": image_manifest["digest"],
                    "vnd.docker.reference.type": "attestation-manifest",
                },
            }
        )
    (layout / "index.json").write_bytes(_json_bytes({"schemaVersion": 2, "manifests": descriptors}))
    destination = directory / "candidate.oci.tar"
    with tarfile.open(destination, "w") as archive:
        for source in sorted(layout.rglob("*")):
            archive.add(source, arcname=source.relative_to(layout), recursive=False)
    return destination


def test_multiarch_oci_audit_and_attestation_extraction(tmp_path: Path) -> None:
    archive = _oci_archive(tmp_path)
    attestations = tmp_path / "attestations"
    attestations.mkdir()

    receipt = audit(archive, attestation_dir=attestations)

    validate_artifact("oci-audit", receipt)
    assert receipt["checks"] == {
        "exact_platforms": True,
        "fixed_entrypoint": True,
        "non_root": True,
        "provenance_attestation_per_platform": True,
        "reference_absent": True,
        "spdx_attestation_per_platform": True,
    }
    assert {item["platform"] for item in receipt["platforms"]} == {
        "linux/amd64",
        "linux/arm64",
    }
    assert len(list(attestations.glob("*.spdx.json"))) == 2
    assert len(list(attestations.glob("*.provenance.json"))) == 2
