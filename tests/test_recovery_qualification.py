from __future__ import annotations

import os
from pathlib import Path

import pytest

from tools.generate_benchmark_vcf import generate
from tools.qualify_recovery import SCENARIOS, qualify
from vcf_sv_stats.exceptions import UsageError
from vcf_sv_stats.schemas import validate_artifact


@pytest.mark.skipif(os.name != "posix", reason="signals and RLIMIT_FSIZE are POSIX APIs")
def test_signal_resource_and_crash_qualification(tmp_path: Path) -> None:
    source = tmp_path / "qualification.vcf.gz"
    generate(
        source,
        tmp_path / "qualification.manifest.json",
        class_id="recovery",
        records=100_000,
        samples=1,
        contigs=4,
        contig_length=1_000_000,
        seed=23,
    )

    receipt = qualify(source, settle_seconds=0.05, source_commit="a" * 40)

    validate_artifact("recovery-qualification", receipt)
    assert [scenario["scenario"] for scenario in receipt["scenarios"]] == list(SCENARIOS)
    assert all(scenario["passed"] for scenario in receipt["scenarios"])
    assert all(scenario["output_absent"] for scenario in receipt["scenarios"])
    assert all(not scenario["publication_directory_entries"] for scenario in receipt["scenarios"])
    assert all(not scenario["transient_output_entries"] for scenario in receipt["scenarios"])
    assert receipt["environment"]["source_commit"] == "a" * 40


def test_recovery_qualification_rejects_nonpositive_settle_time(tmp_path: Path) -> None:
    source = tmp_path / "qualification.vcf.gz"
    generate(
        source,
        tmp_path / "qualification.manifest.json",
        class_id="recovery",
        records=1,
        samples=1,
        contigs=1,
        contig_length=1_000_000,
        seed=23,
    )
    with pytest.raises(UsageError, match="settle_seconds"):
        qualify(source, settle_seconds=0, source_commit="a" * 40)
