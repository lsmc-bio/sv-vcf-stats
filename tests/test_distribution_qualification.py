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


def test_distribution_workflow_builds_one_universal_wheel() -> None:
    workflow = (ROOT / ".github/workflows/distribution.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "name: GitHub release wheel" in workflow
    assert "name: Build universal wheel" in workflow
    assert "uv build --wheel" in workflow
    assert "test \"$(find dist -maxdepth 1 -name '*.whl' | wc -l | tr -d ' ')\" = 1" in workflow
    assert 'vcf_sv_stats-${GITHUB_REF_NAME}-py3-none-any.whl' in workflow
    for retired_job in ("aggregate-install-matrix", "bioconda", "oci", "sigstore", "apptainer"):
        assert f"  {retired_job}:" not in workflow


def test_distribution_workflow_has_no_extra_release_formats_or_signing() -> None:
    workflow = (ROOT / ".github/workflows/distribution.yml").read_text(encoding="utf-8")
    assert "id-token:" not in workflow
    assert "cosign" not in workflow
    assert "sigstore" not in workflow


def test_one_wheel_workflow_requires_an_exact_tag_version() -> None:
    workflow = (ROOT / ".github/workflows/distribution.yml").read_text(encoding="utf-8")

    assert workflow.count('test "$GITHUB_REF_TYPE" = tag') == 1
    assert 'SETUPTOOLS_SCM_PRETEND_VERSION="$GITHUB_REF_NAME"' in workflow
    assert (
        'test "$(basename "$wheel")" = "vcf_sv_stats-${GITHUB_REF_NAME}-py3-none-any.whl"'
        in workflow
    )
    assert "uv build --sdist" not in workflow
    assert "docker build" not in workflow
