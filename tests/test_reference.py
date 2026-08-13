from __future__ import annotations

import json
from pathlib import Path

import pytest

from vcf_sv_stats.exceptions import ReferenceError, UsageError
from vcf_sv_stats.reference import REFERENCE_PROFILE, fetch_reference


def test_reference_fetch_is_pinned_confirmed_and_dry_runnable(tmp_path: Path) -> None:
    with pytest.raises(UsageError, match="confirmation"):
        fetch_reference(
            assembly="GRCh38.p14",
            distribution="ncbi-refseq",
            cache_dir=tmp_path,
            yes=False,
            offline=False,
            dry_run=False,
        )
    planned = fetch_reference(
        assembly="GCF_000001405.40",
        distribution="ncbi-refseq",
        cache_dir=tmp_path,
        yes=True,
        offline=False,
        dry_run=True,
    )
    assert planned["status"] == "planned"
    assert planned["url"] == REFERENCE_PROFILE["url"]
    assert planned["expected_size"] == REFERENCE_PROFILE["expected_size"]
    assert not any(tmp_path.iterdir())


def test_reference_offline_cache_verification(tmp_path: Path) -> None:
    with pytest.raises(ReferenceError, match="offline cache"):
        fetch_reference(
            assembly="GRCh38.p14",
            distribution="ncbi-refseq",
            cache_dir=tmp_path,
            yes=False,
            offline=True,
            dry_run=False,
        )
    target = tmp_path / "GCF_000001405.40-ncbi-refseq"
    target.mkdir()
    fasta = target / "reference.fasta"
    fasta.write_text(">chr1\nACGT\n")
    (target / "reference.fasta.fai").write_text("chr1\t4\t6\t4\t5\n")
    from vcf_sv_stats.serialization import file_sha256

    (target / "manifest.json").write_text(json.dumps({"fasta_sha256": file_sha256(fasta)}))
    verified = fetch_reference(
        assembly="GRCh38.p14",
        distribution="ncbi-refseq",
        cache_dir=tmp_path,
        yes=False,
        offline=True,
        dry_run=False,
    )
    assert verified["status"] == "verified"
