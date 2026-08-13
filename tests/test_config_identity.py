from __future__ import annotations

import json
from pathlib import Path

import pytest

from vcf_sv_stats.config import load_config, validate_config_text
from vcf_sv_stats.engine import stats
from vcf_sv_stats.exceptions import UsageError, ValidationFailure
from vcf_sv_stats.identity import load_identity_context, report_id, validate_sample_mappings
from vcf_sv_stats.models import OperationRequest


def test_strict_yaml_rejects_duplicate_and_unknown_keys(tmp_path: Path) -> None:
    assert validate_config_text("io:\n  threads: 1\n  threads: 2\n")
    assert validate_config_text("unexpected: true\n")

    path = tmp_path / "config.yaml"
    path.write_text("validation:\n  mode: strict\nio:\n  threads: 2\n", encoding="utf-8")
    config = load_config(path)
    assert config["validation"]["mode"] == "strict"
    assert config["io"]["threads"] == 2


def test_identity_context_is_explicit_and_sample_checked(tmp_path: Path) -> None:
    value = {
        "schema_name": "vcf-sv-stats.identity",
        "schema_version": "1.0.0",
        "analysis_units": [
            {
                "analysis_unit_id": "analysis-1",
                "display_id": "display-1",
                "algorithm_id": "algorithm-1",
                "mapped_vcf_sample_ids": ["HG002"],
                "external_identifiers": [{"namespace": "doi", "value": "example"}],
            }
        ],
    }
    path = tmp_path / "identity.json"
    path.write_text(json.dumps(value), encoding="utf-8")

    units = load_identity_context(path)
    validate_sample_mappings(units, ("HG002",))
    assert units[0].analysis_unit_id == "analysis-1"
    assert report_id("a" * 64, "analysis-1") == report_id("a" * 64, "analysis-1")
    with pytest.raises(ValidationFailure, match="unknown VCF sample"):
        validate_sample_mappings(units, ("sample-elsewhere",))


def test_identity_context_never_infers_from_filename(tmp_path: Path) -> None:
    misleading = tmp_path / "HG002.json"
    misleading.write_text("{}", encoding="utf-8")
    with pytest.raises(ValidationFailure):
        load_identity_context(misleading)
    with pytest.raises(UsageError):
        load_identity_context(tmp_path / "missing.json")


def test_multiple_analysis_units_remain_distinct(valid_vcf: Path, tmp_path: Path) -> None:
    context = {
        "schema_name": "vcf-sv-stats.identity",
        "schema_version": "1.0.0",
        "analysis_units": [
            {
                "analysis_unit_id": "analysis-a",
                "display_id": "first",
                "algorithm_id": "algorithm-a",
                "mapped_vcf_sample_ids": ["HG002"],
            },
            {
                "analysis_unit_id": "analysis-b",
                "display_id": "second",
                "algorithm_id": "algorithm-b",
                "mapped_vcf_sample_ids": ["HG002"],
            },
        ],
    }
    context_path = tmp_path / "identity.json"
    context_path.write_text(json.dumps(context), encoding="utf-8")

    reports = stats(OperationRequest(valid_vcf, identity_context=context_path)).summary["reports"]

    assert [report["analysis_unit"]["analysis_unit_id"] for report in reports] == [
        "analysis-a",
        "analysis-b",
    ]
    assert reports[0]["report_id"] != reports[1]["report_id"]
    assert all(report["mapped_vcf_sample_ids"] == ["HG002"] for report in reports)
