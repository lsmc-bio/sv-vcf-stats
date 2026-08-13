"""Explicit, neutral analysis-context parsing."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from .exceptions import UsageError, ValidationFailure
from .models import AnalysisUnit, ExternalIdentifier
from .schemas import validate_artifact


def load_identity_context(path: str | Path) -> tuple[AnalysisUnit, ...]:
    source = Path(path)
    if not source.is_file():
        raise UsageError(f"Identity context does not exist: {source}")
    if source.suffix.casefold() == ".json":
        value = json.loads(source.read_text(encoding="utf-8"))
        validate_artifact("identity", value)
        units = []
        for row in value["analysis_units"]:
            units.append(
                AnalysisUnit(
                    analysis_unit_id=row["analysis_unit_id"],
                    display_id=row.get("display_id"),
                    algorithm_id=row.get("algorithm_id"),
                    mapped_vcf_sample_ids=tuple(row["mapped_vcf_sample_ids"]),
                    external_identifiers=tuple(
                        ExternalIdentifier(item["namespace"], item["value"])
                        for item in row.get("external_identifiers", [])
                    ),
                )
            )
        return _validate_units(units)
    if source.suffix.casefold() not in {".tsv", ".txt"}:
        raise UsageError("Identity context must be JSON or TSV")
    with source.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or not {
            "analysis_unit_id",
            "mapped_vcf_sample_ids",
        }.issubset(reader.fieldnames):
            raise UsageError(
                "Identity TSV requires analysis_unit_id and mapped_vcf_sample_ids columns"
            )
        units = [
            AnalysisUnit(
                analysis_unit_id=row["analysis_unit_id"],
                display_id=row.get("display_id") or None,
                algorithm_id=row.get("algorithm_id") or None,
                mapped_vcf_sample_ids=tuple(
                    item.strip() for item in row["mapped_vcf_sample_ids"].split(",") if item.strip()
                ),
            )
            for row in reader
        ]
    return _validate_units(units)


def _validate_units(units: list[AnalysisUnit]) -> tuple[AnalysisUnit, ...]:
    if not units:
        raise ValidationFailure("Identity context contains no analysis units")
    seen: set[str] = set()
    for unit in units:
        if not unit.analysis_unit_id.strip():
            raise ValidationFailure("analysis_unit_id must not be empty")
        if unit.analysis_unit_id in seen:
            raise ValidationFailure(f"Duplicate analysis_unit_id: {unit.analysis_unit_id}")
        seen.add(unit.analysis_unit_id)
    return tuple(units)


def validate_sample_mappings(units: tuple[AnalysisUnit, ...], samples: tuple[str, ...]) -> None:
    available = set(samples)
    for unit in units:
        unknown = set(unit.mapped_vcf_sample_ids) - available
        if unknown:
            unknown_sample = sorted(unknown)[0]
            raise ValidationFailure(
                f"Analysis unit {unit.analysis_unit_id} maps unknown VCF sample: {unknown_sample}"
            )


def report_id(callset_sha256: str, analysis_unit_id: str | None) -> str:
    preimage = f"vcf-sv-stats:report:1\n{callset_sha256}\n{analysis_unit_id or 'unresolved'}"
    return "vss1-" + hashlib.sha256(preimage.encode()).hexdigest()[:20]
