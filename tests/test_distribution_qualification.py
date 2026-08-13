from __future__ import annotations

import json
from pathlib import Path

from tools.aggregate_distribution_receipts import aggregate
from vcf_sv_stats.schemas import validate_artifact
from vcf_sv_stats.serialization import payload_sha256
from vcf_sv_stats.verify_install import verify

ROOT = Path(__file__).parents[1]


def test_complete_supported_distribution_matrix(tmp_path: Path) -> None:
    target_spec = json.loads((ROOT / "packaging/supported-targets.json").read_text())
    template = verify()
    for target in target_spec["targets"]:
        for python_version in target_spec["python_versions"]:
            for channel in target_spec["installation_channels"]:
                value = json.loads(json.dumps(template))
                value["environment"]["operating_system"] = target["operating_system"]
                value["environment"]["machine"] = target["machine"]
                value["environment"]["python_version"] = f"{python_version}.99"
                value.pop("receipt_sha256")
                value["receipt_sha256"] = payload_sha256(value)
                name = f"{target['id']}.py{python_version}.{channel}.json"
                (tmp_path / name).write_text(json.dumps(value), encoding="utf-8")

    receipt = aggregate(tmp_path, ROOT / "packaging/supported-targets.json")

    validate_artifact("distribution-qualification", receipt)
    assert receipt["case_count"] == 24
    assert receipt["wheel_sdist_parity"] is True
    assert receipt["all_supported_targets_passed"] is True


def test_distribution_workflow_scans_loaded_platform_images() -> None:
    workflow = (ROOT / ".github/workflows/distribution.yml").read_text(encoding="utf-8")

    assert 'syft "vcf-sv-stats:$architecture"' in workflow
    assert 'release/linux-$architecture.container.cyclonedx.json' in workflow
    assert "syft scan oci-archive:" not in workflow
    assert "release/CHECKSUMS.sha256" not in workflow
    assert "release/candidate.provenance.intoto.json" in workflow


def test_distribution_workflow_uses_exact_keyless_identity_on_default_branch() -> None:
    workflow = (ROOT / ".github/workflows/distribution.yml").read_text(encoding="utf-8")
    oci = workflow.split("\n  oci:\n", 1)[1].split("\n  sigstore:\n", 1)[0]
    sigstore = workflow.split("\n  sigstore:\n", 1)[1].split("\n  apptainer:\n", 1)[0]

    assert "id-token: write" not in oci
    assert "cosign" not in oci
    assert sigstore.count("id-token: write") == 1
    assert "publish_sigstore_entry:" in workflow
    assert "default: false" in workflow
    assert "github.event_name == 'workflow_dispatch'" in sigstore
    assert "inputs.publish_sigstore_entry" in sigstore
    assert "github.ref_name == github.event.repository.default_branch" in sigstore
    assert 'certificate_identity="$GITHUB_SERVER_URL/$GITHUB_WORKFLOW_REF"' in sigstore
    assert 'test "$certificate_identity" = "$expected_identity"' in sigstore
    assert "--certificate-identity \"$certificate_identity\"" in sigstore
    assert "--certificate-oidc-issuer https://token.actions.githubusercontent.com" in sigstore
    assert "cosign generate-key-pair" not in workflow
    assert "COSIGN_PASSWORD" not in workflow
    assert "candidate.cosign.pub" not in workflow
