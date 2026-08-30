from __future__ import annotations

from pathlib import Path
from typing import Any

import pysam
import pytest
from typer.testing import CliRunner

from vcf_sv_stats.canonical import iter_canonical
from vcf_sv_stats.cli import app
from vcf_sv_stats.engine import stats
from vcf_sv_stats.exceptions import UsageError
from vcf_sv_stats.io import iter_record_texts
from vcf_sv_stats.models import OperationRequest
from vcf_sv_stats.normalize import normalize


def _capture_read_threads(monkeypatch: pytest.MonkeyPatch) -> list[int | None]:
    real_variant_file = pysam.VariantFile
    read_threads: list[int | None] = []

    def variant_file(*args: Any, **kwargs: Any) -> pysam.VariantFile:
        mode = args[1] if len(args) > 1 else kwargs.get("mode")
        if mode in {None, "r", "rb"}:
            read_threads.append(kwargs.get("threads"))
        return real_variant_file(*args, **kwargs)

    monkeypatch.setattr(pysam, "VariantFile", variant_file)
    return read_threads


def test_analysis_threads_reach_all_variant_reads(
    valid_vcf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    read_threads = _capture_read_threads(monkeypatch)

    stats(OperationRequest(valid_vcf))
    assert read_threads == [1, 1]

    read_threads.clear()
    stats(OperationRequest(valid_vcf, threads=2))
    assert read_threads == [2, 2]

    read_threads.clear()
    tuple(iter_canonical(OperationRequest(valid_vcf, threads=2)))
    assert read_threads == [2]


def test_nonpositive_threads_are_rejected_by_api_and_cli(valid_vcf: Path) -> None:
    with pytest.raises(UsageError, match="threads must be positive"):
        stats(OperationRequest("missing.vcf", threads=0))

    result = CliRunner().invoke(app, ["stats", str(valid_vcf), "--threads", "0"])
    assert result.exit_code == 2
    assert "0 is not in the range x>=1" in result.stderr


def test_normalization_threads_only_its_variant_reads(
    valid_vcf: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    read_threads = _capture_read_threads(monkeypatch)

    normalize(
        OperationRequest(valid_vcf, threads=2),
        tmp_path / "normalized.vcf.gz",
    )

    assert read_threads == [2, 2, 2, 2, 2]


def test_scan_renders_each_record_once(
    valid_vcf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_variant_file = pysam.VariantFile
    render_count = 0

    class CountingRecord:
        def __init__(self, record: Any) -> None:
            self.record = record

        def __getattr__(self, name: str) -> Any:
            return getattr(self.record, name)

        def __str__(self) -> str:
            nonlocal render_count
            render_count += 1
            return str(self.record)

    class CountingVariantFile:
        def __init__(self, variant: pysam.VariantFile) -> None:
            self.variant = variant

        def __getattr__(self, name: str) -> Any:
            return getattr(self.variant, name)

        def __enter__(self) -> CountingVariantFile:
            self.variant.__enter__()
            return self

        def __exit__(self, *args: Any) -> Any:
            return self.variant.__exit__(*args)

        def __iter__(self) -> Any:
            return (CountingRecord(record) for record in self.variant)

    def variant_file(*args: Any, **kwargs: Any) -> CountingVariantFile:
        return CountingVariantFile(real_variant_file(*args, **kwargs))

    monkeypatch.setattr(pysam, "VariantFile", variant_file)

    summary = stats(OperationRequest(valid_vcf)).summary

    assert render_count == summary["statistics"]["source_records"]["total"] == 4


def test_bcf_record_text_reader_propagates_threads(monkeypatch: pytest.MonkeyPatch) -> None:
    read_threads = _capture_read_threads(monkeypatch)
    path = Path("test_data/vcf/manta.native.hg002.subset.bcf")

    records = list(iter_record_texts(path, threads=2))

    assert records
    assert all(len(record.split("\t")) >= 8 for record in records)
    assert read_threads == [2]
