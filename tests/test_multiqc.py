from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from vcf_sv_stats.engine import stats
from vcf_sv_stats.exceptions import ValidationFailure
from vcf_sv_stats.models import OperationRequest
from vcf_sv_stats.multiqc import ingest_summaries
from vcf_sv_stats.serialization import payload_sha256


def _write_summary(path: Path, value: dict[str, object]) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_multiqc_contract_discovers_signed_summaries_and_deduplicates(
    valid_vcf: Path, tmp_path: Path
) -> None:
    summary = stats(OperationRequest(valid_vcf)).summary
    first = _write_summary(tmp_path / "one.vcf-sv-stats.json", summary)
    second = _write_summary(tmp_path / "two.vcf-sv-stats.json", summary)
    result = ingest_summaries((second, first))
    assert len(result.records) == 1
    assert result.records[0].multiqc_sample == result.records[0].report_id
    assert result.duplicate_paths == (second,)


def test_multiqc_contract_rejects_unsigned_unknown_major_and_conflicts(
    valid_vcf: Path, tmp_path: Path
) -> None:
    summary = stats(OperationRequest(valid_vcf)).summary
    wrong_name = _write_summary(tmp_path / "summary.json", summary)
    with pytest.raises(ValidationFailure, match="filename"):
        ingest_summaries((wrong_name,))

    unknown = copy.deepcopy(summary)
    unknown["schema_version"] = "2.0.0"
    payload = dict(unknown)
    payload.pop("payload_sha256")
    unknown["payload_sha256"] = payload_sha256(payload)
    unknown_path = _write_summary(tmp_path / "unknown.vcf-sv-stats.json", unknown)
    with pytest.raises(ValidationFailure, match="schema major"):
        ingest_summaries((unknown_path,))

    first = _write_summary(tmp_path / "first.vcf-sv-stats.json", summary)
    conflict = copy.deepcopy(summary)
    conflict["reports"][0]["mapped_vcf_sample_ids"] = ["HG002"]
    payload = dict(conflict)
    payload.pop("payload_sha256")
    conflict["payload_sha256"] = payload_sha256(payload)
    second = _write_summary(tmp_path / "conflict.vcf-sv-stats.json", conflict)
    with pytest.raises(ValidationFailure, match="Conflicting"):
        ingest_summaries((first, second))
