"""Dependency-free producer-side contract for a future native MultiQC module."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from .exceptions import ValidationFailure
from .schemas import validate_artifact
from .serialization import payload_sha256


@dataclass(frozen=True, slots=True)
class MultiqcRecord:
    report_id: str
    multiqc_sample: str
    source_path: Path
    report: dict[str, Any]
    report_payload_sha256: str


@dataclass(frozen=True, slots=True)
class MultiqcIngestion:
    records: tuple[MultiqcRecord, ...]
    duplicate_paths: tuple[Path, ...]


def _load_digest_bound_summary(path: Path) -> dict[str, Any]:
    if not path.name.endswith(".vcf-sv-stats.json"):
        raise ValidationFailure(f"MultiQC producer filename does not match: {path.name}")
    try:
        value = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationFailure(f"Unable to read MultiQC producer summary: {path.name}") from exc
    version = str(value.get("schema_version", ""))
    try:
        major = int(version.split(".", 1)[0])
    except ValueError as exc:
        raise ValidationFailure(f"Invalid summary schema version: {path.name}") from exc
    if major != 1:
        raise ValidationFailure(f"Unsupported summary schema major: {path.name}")
    if version == "1.0.0":
        validate_artifact("summary", value)
    if value.get("content_signature") != "vcf-sv-stats:summary:1":
        raise ValidationFailure(f"Summary content signature is missing: {path.name}")
    expected_digest = value.get("payload_sha256")
    deterministic_payload = dict(value)
    deterministic_payload.pop("payload_sha256", None)
    deterministic_payload.pop("execution", None)
    if expected_digest != payload_sha256(deterministic_payload):
        raise ValidationFailure(f"Summary payload digest does not match: {path.name}")
    return value


def ingest_summaries(paths: tuple[str | Path, ...]) -> MultiqcIngestion:
    records_by_id: dict[str, MultiqcRecord] = {}
    duplicates: list[Path] = []
    for supplied_path in sorted((Path(path) for path in paths), key=lambda path: str(path)):
        summary = _load_digest_bound_summary(supplied_path)
        for report in summary["reports"]:
            report_id = str(report.get("report_id", ""))
            if not report_id:
                raise ValidationFailure(f"Summary report_id is missing: {supplied_path.name}")
            report_digest = payload_sha256(report)
            candidate = MultiqcRecord(
                report_id=report_id,
                multiqc_sample=report_id,
                source_path=supplied_path,
                report=report,
                report_payload_sha256=report_digest,
            )
            prior = records_by_id.get(report_id)
            if prior is None:
                records_by_id[report_id] = candidate
            elif prior.report_payload_sha256 == report_digest:
                duplicates.append(supplied_path)
            else:
                raise ValidationFailure(
                    "Conflicting MultiQC report identifier in "
                    f"{prior.source_path.name} and {supplied_path.name}"
                )
    return MultiqcIngestion(
        tuple(records_by_id[key] for key in sorted(records_by_id)),
        tuple(sorted(duplicates, key=lambda path: str(path))),
    )
