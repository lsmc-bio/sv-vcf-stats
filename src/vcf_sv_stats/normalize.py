"""Conservative normalization and ordered transactional publication."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import pysam
import pysam.bcftools

from .adapters import detect_adapter, get_adapter
from .canonical import scan_variant
from .exceptions import OutputError, UsageError, ValidationFailure
from .io import assert_distinct_paths, input_metadata, materialize_input, open_variant
from .models import (
    Diagnostic,
    Fixability,
    NormalizationResult,
    OperationRequest,
    RunResult,
    Severity,
)
from .schemas import validate_artifact
from .serialization import file_sha256, payload_sha256, write_json_atomic


def _artifact_paths(output: Path, index_format: str) -> tuple[Path, Path, Path]:
    if output.name.endswith(".vcf.gz"):
        index = Path(str(output) + (".csi" if index_format == "csi" else ".tbi"))
    elif output.suffix == ".bcf":
        index = Path(str(output) + ".csi")
    else:
        raise UsageError("Normalized output must end in .vcf.gz or .bcf")
    manifest = Path(str(output) + ".transforms.json")
    receipt = Path(str(output) + ".receipt.json")
    return index, manifest, receipt


def _ensure_output_contract(
    source: Path,
    output: Path,
    index: Path,
    manifest: Path,
    receipt: Path,
    *,
    force: bool,
) -> None:
    if not output.parent.is_dir():
        raise OutputError(f"Output parent does not exist: {output.parent}")
    assert_distinct_paths(source, output)
    existing = [path for path in (output, index, manifest, receipt) if path.exists()]
    if not existing:
        return
    if not force:
        raise OutputError(f"Output artifact already exists: {existing[0]}")
    if not all(path.is_file() for path in (output, index, manifest, receipt)):
        raise OutputError("Force requires a complete prior owned artifact set")
    try:
        prior = json.loads(receipt.read_text(encoding="utf-8"))
        validate_artifact("receipt", prior)
    except Exception as exc:
        raise OutputError("Force refused because the prior receipt is not valid") from exc
    expected = {path.name for path in (output, index, manifest)}
    observed = {str(item.get("name")) for item in prior["artifacts"]}
    if expected != observed:
        raise OutputError("Force refused because prior receipt ownership does not match")


def _index_variant(path: Path, *, index_format: str) -> Path:
    if path.name.endswith(".vcf.gz"):
        use_csi = index_format == "csi"
        try:
            result = pysam.tabix_index(str(path), preset="vcf", force=True, csi=use_csi)
        except OSError as exc:
            raise OutputError(f"Unable to index normalized VCF: {exc}") from exc
        indexed_data = Path(result)
        if indexed_data != path:
            raise OutputError("Indexer unexpectedly changed the normalized VCF path")
        return Path(str(path) + (".csi" if use_csi else ".tbi"))
    try:
        pysam.bcftools.index("--csi", "--force", str(path), catch_stdout=False)
    except Exception as exc:
        raise OutputError(f"Unable to index normalized BCF: {exc}") from exc
    return Path(str(path) + ".csi")


def _write_streaming_manifest(
    path: Path,
    base: dict[str, Any],
    mappings_path: Path,
) -> None:
    with path.open("xb") as output:
        output.write(b"{\n")
        keys = sorted(base)
        for key in keys:
            rendered = json.dumps(key) + ": " + json.dumps(base[key], sort_keys=True)
            output.write(f"  {rendered},\n".encode())
        output.write(b'  "record_mappings": [')
        first = True
        with mappings_path.open("rb") as mappings:
            for line in mappings:
                if not first:
                    output.write(b",")
                output.write(b"\n    " + line.rstrip(b"\n"))
                first = False
        if not first:
            output.write(b"\n  ")
        output.write(b"]\n}\n")
        output.flush()
        os.fsync(output.fileno())


def _publish_assessment(path: str | Path | None, diagnostics: tuple[Diagnostic, ...]) -> None:
    if path is None:
        return
    value = {
        "schema_name": "vcf-sv-stats.diagnostics",
        "schema_version": "1.0.0",
        "content_signature": "vcf-sv-stats:diagnostics:1",
        "diagnostics": [item.as_dict() for item in diagnostics],
        "complete": True,
    }
    validate_artifact("diagnostics", value)
    write_json_atomic(path, value)


def normalize(
    request: OperationRequest,
    output_path: str | Path,
    *,
    profile: str = "conservative",
    output_format: str | None = None,
    index_format: str = "auto",
    authorize_loss: tuple[str, ...] = (),
    assessment_output: str | Path | None = None,
    force: bool = False,
) -> NormalizationResult:
    if request.regions:
        raise UsageError("Regional input selection is not permitted for normalization")
    if profile not in {"conservative", "caller-lossless", "canonical"}:
        raise UsageError(f"Unknown normalization profile: {profile}")
    if authorize_loss:
        raise UsageError("No lossy transformation codes are defined in v1")
    if index_format not in {"auto", "tbi", "csi"}:
        raise UsageError(f"Unknown index format: {index_format}")
    requested_output = Path(output_path)
    output = requested_output.parent.resolve(strict=True) / requested_output.name
    inferred = (
        "bcf" if output.suffix == ".bcf" else "vcf.gz" if output.name.endswith(".vcf.gz") else None
    )
    if inferred is None:
        raise UsageError("Normalized output must end in .vcf.gz or .bcf")
    if output_format is not None and output_format != inferred:
        raise UsageError("Output format conflicts with output suffix")
    effective_index = (
        "csi" if inferred == "bcf" else ("tbi" if index_format == "auto" else index_format)
    )
    index, manifest, receipt = _artifact_paths(output, effective_index)
    if assessment_output is not None:
        assessment = Path(assessment_output)
        if assessment.parent.resolve(strict=True) / assessment.name == output:
            raise OutputError("Assessment output must differ from normalized output")

    with materialize_input(
        request.input_path,
        temp_dir=request.temp_dir,
        max_input_bytes=request.max_input_bytes,
        max_uncompressed_bytes=request.max_uncompressed_bytes,
    ) as source:
        _ensure_output_contract(source, output, index, manifest, receipt, force=force)
        source_meta = input_metadata(source, display_name=Path(str(request.input_path)).name)
        with open_variant(source) as input_variant:
            header_text = str(input_variant.header)
        detection = detect_adapter(
            header_text,
            requested_adapter_id=request.adapter_id,
            accept_untested_version=request.accept_untested_producer_version,
        )
        descriptor = get_adapter(detection.selected.adapter_id)
        scan = scan_variant(
            source,
            temp_dir=request.temp_dir,
            adapter_id=detection.selected.adapter_id,
        )
        if profile != "conservative" and (
            not descriptor.rewrite_supported or detection.selected.status != "supported"
        ):
            diagnostic = Diagnostic(
                "VSS-NORMALIZATION-ADAPTER-UNPROVEN",
                Severity.ERROR,
                "normalization_safety",
                "The selected adapter does not prove this normalization profile safe",
                specification="normalization profile contract",
                fixability=Fixability.REQUIRES_SOURCE_EVIDENCE,
                blocks_normalization=True,
                adapter_id=descriptor.adapter_id,
                producer_version=detection.selected.version,
            )
            _publish_assessment(assessment_output, (*scan.diagnostics, diagnostic))
            raise ValidationFailure(
                f"Adapter does not support caller-specific rewriting: {descriptor.adapter_id}"
            )
        if profile != "conservative":
            diagnostic = Diagnostic(
                "VSS-NORMALIZATION-PROFILE-UNIMPLEMENTED",
                Severity.ERROR,
                "normalization_safety",
                "The requested representation-changing profile is not implemented",
                specification="normalization profile contract",
                fixability=Fixability.NOT_FIXABLE,
                blocks_normalization=True,
                adapter_id=descriptor.adapter_id,
                producer_version=detection.selected.version,
            )
            _publish_assessment(assessment_output, (*scan.diagnostics, diagnostic))
            raise ValidationFailure(f"Normalization profile is not implemented: {profile}")
        blockers = [item for item in scan.diagnostics if item.blocks_normalization]
        if blockers:
            _publish_assessment(assessment_output, scan.diagnostics)
            raise ValidationFailure(
                f"Normalization blocked by {len(blockers)} diagnostic finding(s)"
            )
        source_index = next(
            (
                candidate
                for candidate in (Path(str(source) + ".tbi"), Path(str(source) + ".csi"))
                if candidate.is_file()
            ),
            None,
        )
        reference_identity: dict[str, Any]
        if request.reference is None:
            reference_identity = {"status": "not_provided"}
        else:
            reference_path = Path(request.reference).resolve(strict=True)
            if not reference_path.is_file():
                raise UsageError("Reference must be a regular local file")
            reference_identity = {
                "status": "provided",
                "name": reference_path.name,
                "sha256": file_sha256(reference_path),
            }

        request_payload = {
            "schema": "vcf-sv-stats.normalize-request/1",
            "input_sha256": source_meta["sha256"],
            "adapter_id": detection.selected.adapter_id,
            "profile": profile,
            "output_format": inferred,
            "index_format": effective_index,
            "target_vcf": "4.5",
        }
        request_sha = payload_sha256(request_payload)
        stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.stage.", dir=output.parent))
        backup = stage / "prior"
        stage_data = stage / output.name
        mappings = stage / "record-mappings.jsonl"
        stage_manifest = stage / manifest.name
        stage_receipt = stage / receipt.name
        try:
            with open_variant(source) as input_variant:
                header = input_variant.header.copy()
                header.add_line(f"##VCFSVSTATS1_REQUEST_SHA256={request_sha}")
                mode = "wb" if inferred == "bcf" else "wz"
                with (
                    pysam.VariantFile(str(stage_data), mode, header=header) as output_variant,
                    mappings.open("x", encoding="utf-8") as mapping_handle,
                ):
                    for ordinal, record in enumerate(input_variant, start=1):
                        output_variant.write(record)
                        mapping_handle.write(
                            json.dumps(
                                {
                                    "source_ordinal": ordinal,
                                    "source_id": record.id,
                                    "output_id": record.id,
                                    "transform_codes": [],
                                },
                                sort_keys=True,
                            )
                            + "\n"
                        )
                    mapping_handle.flush()
                    os.fsync(mapping_handle.fileno())

            stage_index = _index_variant(stage_data, index_format=effective_index)
            with open_variant(stage_data) as check:
                output_records = sum(1 for _ in check)
            if output_records != int(scan.callset["record_count"]):
                raise OutputError("Normalized record count does not match the input")
            output_sha = file_sha256(stage_data)
            index_sha = file_sha256(stage_index)
            manifest_base = {
                "schema_name": "vcf-sv-stats.transforms",
                "schema_version": "1.0.0",
                "request_sha256": request_sha,
                "adapter": {
                    "adapter_id": detection.selected.adapter_id,
                    "producer": detection.selected.producer,
                    "producer_version": detection.selected.version,
                    "status": detection.selected.status,
                },
                "cardinality": {
                    "input_records": scan.callset["record_count"],
                    "output_records": output_records,
                    "record_mappings": output_records,
                },
                "input": {
                    "name": source_meta["display_name"],
                    "sha256": source_meta["sha256"],
                    "records": scan.callset["record_count"],
                    "index": (
                        None
                        if source_index is None
                        else {"name": source_index.name, "sha256": file_sha256(source_index)}
                    ),
                },
                "output": {"name": output.name, "sha256": output_sha, "records": output_records},
                "index": {"name": index.name, "sha256": index_sha},
                "normalization": {"profile": profile, "target_vcf": "4.5"},
                "reference": reference_identity,
                "schemas": {
                    "manifest": "urn:vcf-sv-stats:schema:transforms:1.0.0",
                    "receipt": "urn:vcf-sv-stats:schema:receipt:1.0.0",
                },
            }
            _write_streaming_manifest(stage_manifest, manifest_base, mappings)
            with stage_manifest.open(encoding="utf-8") as handle:
                validate_artifact("transforms", json.load(handle))
            manifest_sha = file_sha256(stage_manifest)
            receipt_value = {
                "schema_name": "vcf-sv-stats.receipt",
                "schema_version": "1.0.0",
                "request_sha256": request_sha,
                "manifest": {"name": manifest.name, "sha256": manifest_sha},
                "artifacts": [
                    {"name": output.name, "sha256": output_sha},
                    {"name": index.name, "sha256": index_sha},
                    {"name": manifest.name, "sha256": manifest_sha},
                ],
            }
            validate_artifact("receipt", receipt_value)
            write_json_atomic(stage_receipt, receipt_value)

            existing = [path for path in (output, index, manifest, receipt) if path.exists()]
            if existing:
                backup.mkdir(mode=0o700)
                moved_to_backup: list[Path] = []
                try:
                    for path in existing:
                        os.replace(path, backup / path.name)
                        moved_to_backup.append(path)
                except Exception:
                    for path in reversed(moved_to_backup):
                        os.replace(backup / path.name, path)
                    raise
            published: list[Path] = []
            try:
                for staged, final in (
                    (stage_index, index),
                    (stage_manifest, manifest),
                    (stage_receipt, receipt),
                    (stage_data, output),
                ):
                    os.replace(staged, final)
                    published.append(final)
                directory_fd = os.open(output.parent, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            except Exception:
                for path in published:
                    path.unlink(missing_ok=True)
                if backup.exists():
                    for path in backup.iterdir():
                        os.replace(path, output.parent / path.name)
                raise
            return NormalizationResult(
                output,
                index,
                manifest,
                receipt,
                output_sha,
                index_sha,
                manifest_sha,
                scan.diagnostics,
            )
        finally:
            shutil.rmtree(stage, ignore_errors=True)


def run_bundle(
    request: OperationRequest,
    output_dir: str | Path,
    *,
    include_normalized: bool = False,
    profile: str = "conservative",
) -> RunResult:
    from .engine import discrepancies, stats, validate

    target = Path(output_dir).resolve(strict=False)
    if target.exists():
        raise OutputError(f"Output directory already exists: {target}")
    if not target.parent.is_dir():
        raise OutputError(f"Output parent does not exist: {target.parent}")
    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}.stage.", dir=target.parent))
    try:
        summary = stats(request)
        validation = validate(request)
        write_json_atomic(stage / "summary.vcf-sv-stats.json", summary.summary)
        diagnostics_path = stage / "diagnostics.jsonl"
        discrepancies(request, output=diagnostics_path, output_format="jsonl")
        provenance = {
            "schema_name": "vcf-sv-stats.run-provenance",
            "schema_version": "1.0.0",
            "request_sha256": payload_sha256(
                {
                    "input_sha256": summary.summary["input"]["sha256"],
                    "include_normalized": include_normalized,
                    "profile": profile,
                }
            ),
            "validation_valid": validation.valid,
        }
        write_json_atomic(stage / "provenance.json", provenance)
        if include_normalized:
            suffix = ".normalized.vcf.gz"
            normalize(request, stage / f"callset{suffix}", profile=profile)
        os.replace(stage, target)
        artifacts = tuple(sorted((path for path in target.iterdir()), key=lambda path: path.name))
        return RunResult(target, artifacts)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
