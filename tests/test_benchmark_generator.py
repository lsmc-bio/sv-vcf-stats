from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.generate_benchmark_vcf import generate
from vcf_sv_stats.engine import stats
from vcf_sv_stats.exceptions import UsageError
from vcf_sv_stats.models import OperationRequest


def test_synthetic_benchmark_generator_is_deterministic_and_neutral(tmp_path: Path) -> None:
    first = generate(
        tmp_path / "first.vcf.gz",
        tmp_path / "first.manifest.json",
        class_id="representative",
        records=250,
        samples=3,
        contigs=2,
        contig_length=1_000_000,
        seed=23,
    )
    second = generate(
        tmp_path / "second.vcf.gz",
        tmp_path / "second.manifest.json",
        class_id="representative",
        records=250,
        samples=3,
        contigs=2,
        contig_length=1_000_000,
        seed=23,
    )

    assert first["source_derived"] is False
    assert first["output_sha256"] == second["output_sha256"]
    assert first["output_bytes"] == second["output_bytes"]
    assert json.loads((tmp_path / "first.manifest.json").read_text()) == first

    result = stats(OperationRequest(tmp_path / "first.vcf.gz"))
    assert result.summary["statistics"]["source_records"]["total"] == 250
    assert result.summary["callset"]["vcf_sample_ids"] == ["S0001", "S0002", "S0003"]
    assert result.summary["statistics"]["alleles"]["types"] == {"DEL": 200, "INS": 50}


def test_synthetic_benchmark_generator_rejects_unsafe_contract(tmp_path: Path) -> None:
    with pytest.raises(UsageError, match="positive"):
        generate(
            tmp_path / "invalid.vcf.gz",
            tmp_path / "invalid.manifest.json",
            class_id="invalid",
            records=0,
            samples=1,
            contigs=1,
            contig_length=1_000_000,
            seed=1,
        )
