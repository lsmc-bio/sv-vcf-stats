from __future__ import annotations

from vcf_sv_stats.schemas import validate_artifact
from vcf_sv_stats.verify_install import verify


def test_self_contained_install_verification() -> None:
    receipt = verify()
    validate_artifact("install-verification", receipt)
    assert receipt["passed"] is True
    assert receipt["network_required"] is False
    assert {item["container"] for item in receipt["formats"]} == {"vcf.gz", "bcf"}
    assert {item["semantic_sha256"] for item in receipt["formats"]} == {receipt["semantic_sha256"]}
    assert {item["normalized_semantic_sha256"] for item in receipt["formats"]} == {
        receipt["semantic_sha256"]
    }
