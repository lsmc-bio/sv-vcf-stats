"""Public operation engine composed from safe, deterministic phases."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from . import __version__
from .adapters import detect_adapter
from .canonical import ScanResult, scan_variant
from .exceptions import UsageError, ValidationFailure
from .identity import load_identity_context, report_id, validate_sample_mappings
from .io import input_metadata, materialize_input, open_variant
from .models import (
    DiscrepancyResult,
    InspectionResult,
    OperationRequest,
    StatisticsResult,
    ValidationResult,
)
from .schemas import validate_artifact
from .serialization import payload_sha256, write_bytes_atomic, write_json_atomic


def _analyze(
    request: OperationRequest,
    *,
    max_records: int | None = None,
) -> tuple[dict[str, Any], Any, ScanResult]:
    display_name = "stdin" if str(request.input_path) == "-" else Path(request.input_path).name
    with materialize_input(
        request.input_path,
        temp_dir=request.temp_dir,
        max_input_bytes=request.max_input_bytes,
        max_uncompressed_bytes=request.max_uncompressed_bytes,
    ) as path:
        metadata = input_metadata(path, display_name=display_name)
        with open_variant(path) as variant:
            header_text = str(variant.header)
        detection = detect_adapter(
            header_text,
            requested_adapter_id=request.adapter_id,
            accept_untested_version=request.accept_untested_producer_version,
        )
        scan = scan_variant(
            path,
            temp_dir=request.temp_dir,
            max_records=max_records,
            adapter_id=detection.selected.adapter_id,
            regions=request.regions,
            regions_scan=request.regions_scan,
        )
    metadata["complete"] = scan.complete
    if request.regions:
        metadata["regions"] = list(request.regions)
        metadata["regional_scan"] = request.regions_scan
    return metadata, detection, scan


def inspect(request: OperationRequest, *, max_records: int | None = None) -> InspectionResult:
    if max_records is not None and max_records < 1:
        raise UsageError("max_records must be positive")
    metadata, detection, scan = _analyze(request, max_records=max_records)
    header = dict(scan.header)
    header.pop("text", None)
    return InspectionResult(
        input=metadata,
        header=header,
        detection=detection,
        callset=scan.callset,
        diagnostics=scan.diagnostics,
        complete=scan.complete,
    )


def _states(scan: ScanResult) -> dict[str, str]:
    errors = [item for item in scan.diagnostics if item.severity in {"error", "fatal"}]
    return {
        "container_state": "accepted",
        "parse_state": "accepted",
        "vcf_conformance_state": "nonconformant" if errors else "conformant",
        "sv_semantic_state": "inconsistent" if errors else "consistent",
        "operation_safety_state": "blocked"
        if any(d.blocks_normalization for d in errors)
        else "safe",
        "statistics_state": "complete" if scan.complete else "partial",
    }


def validate(request: OperationRequest) -> ValidationResult:
    metadata, detection, scan = _analyze(request)
    states = _states(scan)
    valid = not any(item.severity in {"error", "fatal"} for item in scan.diagnostics)
    return ValidationResult(valid, states, scan.diagnostics, metadata, detection)


def _build_reports(
    request: OperationRequest,
    input_sha256: str,
    samples: tuple[str, ...],
    statistics: dict[str, Any],
) -> list[dict[str, Any]]:
    if request.identity_context is None:
        return [
            {
                "report_id": report_id(input_sha256, None),
                "analysis_unit": {"status": "unresolved"},
                "mapped_vcf_sample_ids": [],
                "statistics": statistics,
            }
        ]
    units = load_identity_context(request.identity_context)
    validate_sample_mappings(units, samples)
    return [
        {
            "report_id": report_id(input_sha256, unit.analysis_unit_id),
            "analysis_unit": {
                "status": "resolved",
                "analysis_unit_id": unit.analysis_unit_id,
                "display_id": unit.display_id,
                "algorithm_id": unit.algorithm_id,
                "external_identifiers": [
                    {"namespace": item.namespace, "value": item.value}
                    for item in unit.external_identifiers
                ],
            },
            "mapped_vcf_sample_ids": list(unit.mapped_vcf_sample_ids),
            "statistics": statistics,
        }
        for unit in units
    ]


def stats(request: OperationRequest) -> StatisticsResult:
    metadata, detection, scan = _analyze(request)
    if any(item.blocks_statistics for item in scan.diagnostics):
        raise ValidationFailure("Input findings block statistics")
    validation = {
        "states": _states(scan),
        "diagnostic_counts": dict(
            sorted(Counter(item.severity.value for item in scan.diagnostics).items())
        ),
    }
    callset = {
        **scan.callset,
        "callset_id": f"sha256:{metadata['sha256']}",
        "producer": detection.selected.as_dict(),
        "producer_kind": (
            "unknown"
            if detection.selected.producer == "unknown"
            else "merger"
            if "jasmine" in detection.selected.adapter_id
            or "survivor" in detection.selected.adapter_id
            or "octopusv" in detection.selected.adapter_id
            or "trussv" in detection.selected.adapter_id
            else "caller"
        ),
    }
    payload: dict[str, Any] = {
        "schema_name": "vcf-sv-stats.summary",
        "schema_version": "1.0.0",
        "content_signature": "vcf-sv-stats:summary:1",
        "producer": {"name": "vcf-sv-stats", "version": __version__},
        "input": metadata,
        "callset": callset,
        "validation": validation,
        "statistics": scan.statistics,
        "reports": _build_reports(
            request,
            str(metadata["sha256"]),
            tuple(scan.callset["vcf_sample_ids"]),
            scan.statistics,
        ),
    }
    payload["payload_sha256"] = payload_sha256(payload)
    validate_artifact("summary", payload)
    return StatisticsResult(payload, scan.diagnostics)


def discrepancies(
    request: OperationRequest,
    *,
    output: str | Path | None = None,
    output_format: str = "json",
    force: bool = False,
) -> DiscrepancyResult:
    metadata, _detection, scan = _analyze(request)
    counts = dict(sorted(Counter(item.severity.value for item in scan.diagnostics).items()))
    result = DiscrepancyResult(scan.diagnostics, counts, scan.complete, None)
    if output is None:
        return result
    if output_format not in {"json", "jsonl", "tsv"}:
        raise UsageError(f"Unsupported discrepancies format: {output_format}")
    target = Path(output)
    if output_format == "json":
        artifact = {
            "schema_name": "vcf-sv-stats.discrepancies",
            "schema_version": "1.0.0",
            "content_signature": "vcf-sv-stats:discrepancies:1",
            "input": metadata,
            "counts": counts,
            "diagnostics": [item.as_dict() for item in scan.diagnostics],
            "complete": scan.complete,
        }
        validate_artifact("discrepancies", artifact)
        write_json_atomic(target, artifact, force=force)
    elif output_format == "jsonl":
        content = b"".join(
            (json.dumps(item.as_dict(), sort_keys=True) + "\n").encode()
            for item in scan.diagnostics
        )
        write_bytes_atomic(target, content, force=force)
    else:
        header = "code\tseverity\tcategory\trecord_ordinal\tchrom\tpos\tfield_name\tmessage\n"
        rows = [header]
        for item in scan.diagnostics:
            values = (
                item.code,
                item.severity.value,
                item.category,
                "" if item.record_ordinal is None else str(item.record_ordinal),
                item.chrom or "",
                "" if item.pos is None else str(item.pos),
                item.field_name or "",
                item.message.replace("\t", " ").replace("\n", " "),
            )
            rows.append("\t".join(values) + "\n")
        write_bytes_atomic(target, "".join(rows).encode(), force=force)
    return DiscrepancyResult(scan.diagnostics, counts, scan.complete, target)
