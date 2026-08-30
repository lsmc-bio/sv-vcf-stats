"""Streaming canonical observations, diagnostics, event resolution, and aggregates."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .events import EventStore
from .exceptions import InputError
from .io import (
    has_variant_index,
    iter_record_texts,
    materialize_input,
    open_variant,
    parse_regions,
    record_in_regions,
    validate_threads,
)
from .models import CanonicalObservation, Diagnostic, Fixability, OperationRequest, Severity
from .vcf45 import (
    PhaseEvidenceStore,
    parse_header_contract,
    validate_header_contract,
    validate_record_text,
)


@dataclass(frozen=True, slots=True)
class ScanResult:
    header: dict[str, Any]
    callset: dict[str, Any]
    statistics: dict[str, Any]
    diagnostics: tuple[Diagnostic, ...]
    complete: bool


LENGTH_BINS: tuple[tuple[int, int | None], ...] = (
    (0, 50),
    (50, 100),
    (100, 500),
    (500, 1_000),
    (1_000, 5_000),
    (5_000, 10_000),
    (10_000, 50_000),
    (50_000, 100_000),
    (100_000, 1_000_000),
    (1_000_000, 10_000_000),
    (10_000_000, None),
)


def _first_info(record: Any, key: str, allele_index: int = 0) -> Any:
    if key not in record.info:
        return None
    value = record.info[key]
    if isinstance(value, tuple):
        if not value:
            return None
        return value[min(allele_index, len(value) - 1)]
    return value


def classify_allele(record: Any, alt: str, allele_index: int) -> tuple[str, str]:
    if "[" in alt or "]" in alt:
        return "BND", "breakend"
    if alt.startswith(".") or alt.endswith("."):
        return "SINGLE_BND", "single_breakend"
    if alt.startswith("<") and alt.endswith(">"):
        symbolic = alt[1:-1].split(":", 1)[0]
        if symbolic in {"DEL", "DUP", "INS", "INV", "CNV"}:
            return symbolic, "symbolic"
        if symbolic in {"NON_REF", "*"}:
            return "NON_SV", "symbolic"
        return "UNKNOWN", "symbolic"
    declared = _first_info(record, "SVTYPE", allele_index)
    if isinstance(declared, str) and declared.upper() in {
        "DEL",
        "DUP",
        "INS",
        "INV",
        "CNV",
        "BND",
        "TRA",
    }:
        return declared.upper(), "sequence"
    delta = len(alt) - len(record.ref)
    if abs(delta) >= 50:
        return ("INS" if delta > 0 else "DEL"), "sequence"
    return "NON_SV", "sequence"


def allele_length(record: Any, alt: str, allele_index: int, variant_type: str) -> int | None:
    value = _first_info(record, "SVLEN", allele_index)
    if isinstance(value, int):
        return abs(value)
    if isinstance(value, float) and math.isfinite(value):
        return abs(int(value))
    if variant_type in {"DEL", "DUP", "INV", "CNV"} and record.stop is not None:
        return abs(int(record.stop) - int(record.pos) + 1)
    if variant_type == "INS" and not alt.startswith("<"):
        return abs(len(alt) - len(record.ref))
    return None


@dataclass(slots=True)
class HistogramAccumulator:
    """Accumulate a fixed histogram without retaining source values."""

    boundaries: tuple[tuple[int | float, int | float | None], ...]
    counts: list[int] = field(init=False)
    n: int = 0
    minimum: int | float | None = None
    maximum: int | float | None = None

    def __post_init__(self) -> None:
        if not self.boundaries:
            raise ValueError("Histogram boundaries must not be empty")
        self.counts = [0 for _ in self.boundaries]

    def add(self, value: int | float) -> None:
        for index, (lower, upper) in enumerate(self.boundaries):
            if value >= lower and (upper is None or value < upper):
                self.counts[index] += 1
                self.n += 1
                self.minimum = value if self.minimum is None else min(self.minimum, value)
                self.maximum = value if self.maximum is None else max(self.maximum, value)
                return
        raise ValueError(f"Histogram value is outside declared boundaries: {value}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "boundaries": [[lower, upper] for lower, upper in self.boundaries],
            "counts": list(self.counts),
            "n": self.n,
            "minimum": self.minimum,
            "maximum": self.maximum,
        }


def _numeric_boundaries(
    values: tuple[int | float, ...],
) -> tuple[tuple[int | float, int | float | None], ...]:
    return tuple(
        (lower, values[index + 1] if index + 1 < len(values) else None)
        for index, lower in enumerate(values)
    )


def _support_scalar(value: Any) -> Any:
    if isinstance(value, tuple):
        return value[0] if value else None
    return value


def _support_count(value: Any) -> int | None:
    scalar = _support_scalar(value)
    if isinstance(scalar, bool):
        return None
    if isinstance(scalar, int) and scalar >= 0:
        return scalar
    if isinstance(scalar, str) and scalar.isdigit():
        return int(scalar)
    return None


def _support_vector(value: Any) -> str | None:
    scalar = _support_scalar(value)
    if not isinstance(scalar, str) or not scalar or set(scalar) - {"0", "1"}:
        return None
    return scalar


def _raw_record_fields(record_text: str) -> tuple[str, str]:
    columns = record_text.split("\t", 8)
    return columns[6], columns[7]


def _raw_filter_state(record: Any, raw_filter: str) -> tuple[str, tuple[str, ...]]:
    keys = tuple(str(key) for key in record.filter)
    if raw_filter == ".":
        return "missing", keys
    if not keys:
        return "unfiltered", keys
    if keys == ("PASS",):
        return "PASS", keys
    return "filtered_any", keys


def _mate_ids(record: Any) -> tuple[str, ...]:
    value = record.info.get("MATEID") if "MATEID" in record.info else ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, tuple):
        return tuple(str(item) for item in value)
    return ()


def iter_canonical(request: OperationRequest) -> Iterator[CanonicalObservation]:
    """Yield immutable, source-ordered allele observations without materializing records."""
    validate_threads(request.threads)
    regions = parse_regions(request.regions)
    with (
        materialize_input(
            request.input_path,
            temp_dir=request.temp_dir,
            max_input_bytes=request.max_input_bytes,
            max_uncompressed_bytes=request.max_uncompressed_bytes,
        ) as path,
        open_variant(path, threads=request.threads) as variant,
    ):
        if regions and not request.regions_scan and not has_variant_index(path):
            raise InputError("Regional iteration requires an index or explicit regions_scan")
        for record_ordinal, record in enumerate(variant, start=1):
            if not record_in_regions(record, regions):
                continue
            raw_filter, _raw_info = _raw_record_fields(str(record))
            filter_state, _keys = _raw_filter_state(record, raw_filter)
            mate_ids = _mate_ids(record)
            event_value = record.info.get("EVENT") if "EVENT" in record.info else None
            original = _first_info(record, "SVTYPE")
            for allele_index, alt in enumerate(record.alts or ()):
                normalized_type, representation = classify_allele(record, alt, allele_index)
                yield CanonicalObservation(
                    source_record_ordinal=record_ordinal,
                    allele_ordinal=allele_index + 1,
                    chrom=str(record.contig),
                    pos=int(record.pos),
                    record_id=None if record.id in {None, "."} else str(record.id),
                    original_svtype=(str(original) if original is not None else None),
                    normalized_type=normalized_type,
                    representation=representation,
                    length_bp=allele_length(record, alt, allele_index, normalized_type),
                    filter_state=filter_state,
                    mate_ids=mate_ids,
                    event_id=(None if event_value in {None, "."} else str(event_value)),
                )


def scan_variant(
    path: str | Path,
    *,
    temp_dir: str | Path | None = None,
    max_records: int | None = None,
    adapter_id: str | None = None,
    regions: tuple[str, ...] = (),
    regions_scan: bool = False,
    threads: int = 1,
) -> ScanResult:
    diagnostics: list[Diagnostic] = []
    record_count = 0
    allele_count = 0
    non_sv_records = 0
    multiallelic = 0
    missing_qual = 0
    invalid_qual = 0
    type_counts: Counter[str] = Counter()
    representation_counts: Counter[str] = Counter()
    filter_counts: Counter[str] = Counter()
    genotype_counts: Counter[str] = Counter()
    copy_number_counts: Counter[str] = Counter()
    cnv_genotype_states: Counter[str] = Counter()
    length_histogram = HistogramAccumulator(LENGTH_BINS)
    qual_histogram = HistogramAccumulator(
        _numeric_boundaries((0, 10, 20, 30, 50, 100, 200, 500, 1_000))
    )
    copy_number_quality_histogram = HistogramAccumulator(
        _numeric_boundaries((0, 10, 20, 30, 50, 100, 200, 500, 1_000))
    )
    length_missing = 0
    copy_number_quality_missing = 0
    copy_number_quality_invalid = 0
    simple_events = 0
    support_declared_fields: tuple[str, ...] = ()
    support_records_with_values = 0
    support_records_without_values = 0
    support_count_counts: Counter[str] = Counter()
    support_source_count_states: Counter[str] = Counter()
    support_consistency: Counter[str] = Counter()
    parsed_regions = parse_regions(regions)
    complete = not parsed_regions
    stopped_early = False

    try:
        variant = open_variant(path, threads=threads)
        if parsed_regions and not regions_scan and not has_variant_index(path):
            variant.close()
            raise InputError("Regional operation requires an index or explicit regions_scan")
        samples = tuple(variant.header.samples)
        header_text = str(variant.header)
        header_contract = parse_header_contract(header_text)
        support_declared_fields = tuple(
            field_name for field_name in ("SUPP", "SUPP_VEC") if field_name in variant.header.info
        )
        header = {
            "vcf_version": str(variant.header.version),
            "samples": list(samples),
            "sample_count": len(samples),
            "contig_count": len(variant.header.contigs),
            "info_fields": sorted(variant.header.info),
            "format_fields": sorted(variant.header.formats),
            "filter_fields": sorted(variant.header.filters),
            "text": header_text,
        }
        diagnostics.extend(validate_header_contract(header_contract, adapter_id=adapter_id))
        exact_record_texts = (
            iter(iter_record_texts(path, threads=threads)) if header_contract.is_v45 else None
        )
        reserved_expectations = {
            "GQ": (variant.header.formats, "Integer", None),
            "PS": (variant.header.formats, "Integer", None),
            "AF": (variant.header.info, None, "A"),
        }
        for field_name, (
            collection,
            expected_type,
            expected_number,
        ) in reserved_expectations.items():
            if field_name not in collection:
                continue
            definition = collection[field_name]
            type_invalid = expected_type is not None and definition.type != expected_type
            number_invalid = expected_number is not None and definition.number != expected_number
            if type_invalid or number_invalid:
                diagnostics.append(
                    Diagnostic(
                        "VSS-HEADER-RESERVED-DECLARATION",
                        Severity.ERROR,
                        "vcf_conformance",
                        f"Reserved field {field_name} has a nonstandard declaration",
                        field_name=field_name,
                        specification="VCF field declaration",
                        fixability=Fixability.REQUIRES_ADAPTER,
                        blocks_normalization=True,
                        adapter_id=adapter_id,
                    )
                )
        with variant, EventStore(temp_dir) as events, PhaseEvidenceStore(
            temp_dir, adapter_id=adapter_id
        ) as phases:
            for source_ordinal, record in enumerate(variant, start=1):
                if exact_record_texts is None:
                    record_text = str(record)
                else:
                    try:
                        record_text = next(exact_record_texts)
                    except StopIteration as exc:
                        raise InputError(
                            "VCF record text and parser streams have different cardinality"
                        ) from exc
                if not record_in_regions(record, parsed_regions):
                    continue
                record_count += 1
                if max_records is not None and record_count > max_records:
                    record_count -= 1
                    complete = False
                    stopped_early = True
                    break
                raw_filter, raw_info = _raw_record_fields(record_text)
                alts = tuple(record.alts or ())
                if len(alts) > 1:
                    multiallelic += 1
                if record.qual is None:
                    missing_qual += 1
                else:
                    qual = float(record.qual)
                    if math.isfinite(qual) and qual >= 0:
                        qual_histogram.add(qual)
                    else:
                        invalid_qual += 1
                if header_contract.is_v45:
                    phases.add(record_text, ordinal=source_ordinal)
                diagnostics.extend(
                    validate_record_text(
                        record_text,
                        ordinal=source_ordinal,
                        contract=header_contract,
                        adapter_id=adapter_id,
                    )
                )
                filter_state, filter_keys = _raw_filter_state(record, raw_filter)
                if filter_state == "missing":
                    filter_counts["missing"] += 1
                elif filter_state == "unfiltered":
                    filter_counts["unfiltered"] += 1
                elif filter_state == "PASS":
                    filter_counts["PASS"] += 1
                else:
                    filter_counts["filtered_any"] += 1
                    filter_counts.update(filter_keys)

                raw_values = {
                    item.partition("=")[0]: item.partition("=")[2]
                    for item in raw_info.split(";")
                    if "=" in item
                }
                if support_declared_fields:
                    declared_count = _support_count(
                        record.info.get("SUPP") if "SUPP" in record.info else None
                    )
                    vector = _support_vector(
                        record.info.get("SUPP_VEC") if "SUPP_VEC" in record.info else None
                    )
                    if declared_count is None and vector is None:
                        support_records_without_values += 1
                    else:
                        support_records_with_values += 1
                        vector_count = vector.count("1") if vector is not None else None
                        effective_count = (
                            declared_count if declared_count is not None else vector_count
                        )
                        if effective_count is not None:
                            support_count_counts[str(effective_count)] += 1
                        if vector is not None:
                            support_source_count_states[str(len(vector))] += 1
                        if declared_count is not None and vector_count is not None:
                            support_consistency[
                                "consistent" if declared_count == vector_count else "inconsistent"
                            ] += 1
                        else:
                            support_consistency["uncheckable"] += 1
                for field_name, raw_value in raw_values.items():
                    if header_contract.is_v45:
                        continue
                    if field_name not in variant.header.info:
                        continue
                    number = variant.header.info[field_name].number
                    observed = len(raw_value.split(","))
                    expected = (
                        len(record.alts or ())
                        if number == "A"
                        else len(record.alts or ()) + 1
                        if number == "R"
                        else int(number)
                        if isinstance(number, int)
                        else None
                    )
                    if expected is not None and observed != expected:
                        diagnostics.append(
                            Diagnostic(
                                "VSS-CARDINALITY-INFO",
                                Severity.ERROR,
                                "vcf_conformance",
                                f"INFO field cardinality is {observed}; expected {expected}",
                                source_ordinal,
                                record.contig,
                                record.pos,
                                field_name,
                                "VCF INFO Number declaration",
                                Fixability.REQUIRES_ADAPTER,
                                blocks_normalization=True,
                                adapter_id=adapter_id,
                            )
                        )

                record_has_sv = False
                record_has_bnd = False
                record_has_cnv = False
                for allele_index, alt in enumerate(alts):
                    allele_count += 1
                    variant_type, representation = classify_allele(record, alt, allele_index)
                    type_counts[variant_type] += 1
                    representation_counts[representation] += 1
                    if variant_type != "NON_SV":
                        record_has_sv = True
                    if variant_type == "CNV":
                        record_has_cnv = True
                    if variant_type in {"BND", "SINGLE_BND"}:
                        record_has_bnd = True
                        declared = _first_info(record, "SVTYPE", allele_index)
                        if isinstance(declared, str) and declared.upper() not in {
                            "BND",
                            "TRA",
                        }:
                            diagnostics.append(
                                Diagnostic(
                                    "VSS-BND-ALT-TYPE-CONFLICT",
                                    Severity.ERROR,
                                    "breakend",
                                    "Bracket breakend ALT conflicts with the declared type",
                                    source_ordinal,
                                    record.contig,
                                    record.pos,
                                    "SVTYPE",
                                    "VCF 4.5 breakend alleles",
                                    Fixability.REQUIRES_ADAPTER,
                                    blocks_normalization=True,
                                    adapter_id=adapter_id,
                                )
                            )
                    elif variant_type != "NON_SV":
                        simple_events += 1
                        declared = _first_info(record, "SVTYPE", allele_index)
                        if (
                            isinstance(declared, str)
                            and declared.upper() != variant_type
                            and variant_type != "UNKNOWN"
                        ):
                            diagnostics.append(
                                Diagnostic(
                                    "VSS-ALT-TYPE-CONFLICT",
                                    Severity.ERROR,
                                    "sv_semantics",
                                    "ALT representation conflicts with the declared type",
                                    source_ordinal,
                                    record.contig,
                                    record.pos,
                                    "SVTYPE",
                                    "VCF symbolic allele semantics",
                                    Fixability.REQUIRES_ADAPTER,
                                    blocks_normalization=True,
                                    adapter_id=adapter_id,
                                )
                            )
                    length = allele_length(record, alt, allele_index, variant_type)
                    if length is not None:
                        length_histogram.add(length)
                    elif variant_type not in {"BND", "SINGLE_BND", "TRA", "NON_SV"}:
                        length_missing += 1
                if not record_has_sv:
                    non_sv_records += 1

                mate_ids = _mate_ids(record)
                event_value = record.info.get("EVENT") if "EVENT" in record.info else None
                event_id = str(event_value) if event_value not in {None, "."} else None
                record_id = record.id if record.id not in {None, "."} else None
                events.add(
                    source_ordinal,
                    record_id,
                    event_id,
                    mate_ids,
                    is_bnd=record_has_bnd,
                )

                record_genotype_states: list[str] = []
                for sample in samples:
                    call = record.samples[sample]
                    gt = call.get("GT")
                    if gt is None or not gt or any(value is None for value in gt):
                        genotype_counts["no_call"] += 1
                        record_genotype_states.append("unresolved")
                        if gt and any(value is not None for value in gt):
                            genotype_counts["partially_missing"] += 1
                    elif all(value == 0 for value in gt):
                        genotype_counts["reference"] += 1
                        record_genotype_states.append("reference")
                    elif len(gt) == 2 and gt[0] == gt[1] and gt[0] > 0:
                        genotype_counts["homozygous_alt"] += 1
                        record_genotype_states.append("alternate")
                    elif any(value > 0 for value in gt):
                        genotype_counts["heterozygous_or_other_alt"] += 1
                        record_genotype_states.append("alternate")
                    else:
                        genotype_counts["other"] += 1
                        record_genotype_states.append("unresolved")
                    genotype_counts["phased" if call.phased else "unphased"] += 1
                    if gt:
                        genotype_counts[f"ploidy:{len(gt)}"] += 1
                    copy_number = call.get("CN")
                    if copy_number is None:
                        copy_number_counts["missing"] += 1
                    elif isinstance(copy_number, int) and 0 <= copy_number <= 8:
                        copy_number_counts[str(copy_number)] += 1
                    elif isinstance(copy_number, int) and copy_number >= 9:
                        copy_number_counts["9+"] += 1
                    elif isinstance(copy_number, (int, float)):
                        copy_number_counts["noninteger"] += 1
                    else:
                        copy_number_counts["invalid"] += 1
                    copy_number_quality = call.get("CNQ")
                    if copy_number_quality is None:
                        copy_number_quality_missing += 1
                    elif (
                        isinstance(copy_number_quality, (int, float))
                        and math.isfinite(copy_number_quality)
                        and copy_number_quality >= 0
                    ):
                        copy_number_quality_histogram.add(float(copy_number_quality))
                    else:
                        copy_number_quality_invalid += 1
                if record_has_cnv:
                    if "alternate" in record_genotype_states:
                        cnv_genotype_states["alternate"] += 1
                    elif record_genotype_states and all(
                        state == "reference" for state in record_genotype_states
                    ):
                        cnv_genotype_states["reference_segment"] += 1
                    else:
                        cnv_genotype_states["unresolved"] += 1

            if exact_record_texts is not None and not stopped_early:
                try:
                    next(exact_record_texts)
                except StopIteration:
                    pass
                else:
                    raise InputError(
                        "VCF record text and parser streams have different cardinality"
                    )
            graph = events.summarize()
            if header_contract.is_v45:
                diagnostics.extend(phases.diagnostics())
    except (OSError, ValueError, KeyError) as exc:
        raise InputError(f"VCF/BCF parsing failed: {exc}") from exc

    for _duplicate_id, count in graph["duplicate_ids"]:
        diagnostics.append(
            Diagnostic(
                "VSS-ID-DUPLICATE",
                Severity.ERROR,
                "vcf_conformance",
                f"A record identifier is duplicated {count} times",
                field_name="ID",
                fixability=Fixability.REQUIRES_ADAPTER,
                blocks_normalization=True,
                adapter_id=adapter_id,
            )
        )
    if graph["unresolved_mate_references"]:
        diagnostics.append(
            Diagnostic(
                "VSS-BND-MATE-UNRESOLVED",
                Severity.ERROR,
                "event_graph",
                f"Unresolved MATEID references: {graph['unresolved_mate_references']}",
                field_name="MATEID",
                fixability=Fixability.REQUIRES_SOURCE_EVIDENCE,
                blocks_normalization=True,
                adapter_id=adapter_id,
            )
        )
    if graph["bnd_without_mate"]:
        diagnostics.append(
            Diagnostic(
                "VSS-BND-RELATIONSHIP-UNDECLARED",
                Severity.WARNING,
                "event_graph",
                f"Breakend records without MATEID: {graph['bnd_without_mate']}",
                field_name="MATEID",
                fixability=Fixability.REQUIRES_SOURCE_EVIDENCE,
                adapter_id=adapter_id,
            )
        )

    callset = {
        "vcf_sample_ids": list(samples),
        "single_sample": len(samples) == 1,
        "record_count": record_count,
        "allele_count": allele_count,
    }
    statistics = {
        "histogram_policy": "vss-bins/1",
        "metric_contracts": {
            "alleles": {
                "scope": "alternate_allele",
                "denominator": "all_parsed_alternate_alleles",
                "unit": "alleles",
                "comparability": "canonical-observation/1",
            },
            "breakends": {
                "scope": "breakend_observation",
                "denominator": "all_bracket_and_single_breakend_alleles",
                "unit": "breakends",
                "comparability": "event-resolution/1",
            },
            "copy_number": {
                "scope": "vcf_sample_call",
                "denominator": "all_parsed_sample_calls",
                "unit": "declared_copy_number",
                "comparability": "declared-cn/1",
            },
            "events": {
                "scope": "resolved_event",
                "denominator": "simple_events_and_resolvable_relationship_groups",
                "unit": "events",
                "comparability": "event-resolution/1",
            },
            "filters": {
                "scope": "source_record",
                "denominator": "all_parsed_source_records",
                "unit": "records",
                "comparability": "vcf-filter-state/1",
            },
            "genotypes": {
                "scope": "vcf_sample_call",
                "denominator": "all_parsed_sample_calls",
                "unit": "sample_calls",
                "comparability": "vcf-genotype-state/1",
            },
            "length_bp": {
                "scope": "alternate_allele",
                "denominator": "alleles_with_applicable_length",
                "unit": "base_pairs",
                "comparability": "vss-bins/1",
            },
            "merged_support": {
                "scope": "source_record",
                "denominator": "records_with_declared_merger_support",
                "unit": "records",
                "comparability": "merger-support-provenance/1",
            },
            "qual": {
                "scope": "source_record",
                "denominator": "all_parsed_source_records",
                "unit": "vcf_qual",
                "comparability": "declared-qual/1",
            },
            "source_records": {
                "scope": "source_record",
                "denominator": "all_parsed_source_records",
                "unit": "records",
                "comparability": "canonical-observation/1",
            },
        },
        "source_records": {
            "total": record_count,
            "non_sv_records": non_sv_records,
            "multiallelic_records": multiallelic,
            "missing_qual_records": missing_qual,
        },
        "alleles": {"total": allele_count, "types": dict(sorted(type_counts.items()))},
        "representations": dict(sorted(representation_counts.items())),
        "filters": dict(sorted(filter_counts.items())),
        "genotypes": dict(sorted(genotype_counts.items())),
        "breakends": {
            "total": graph["bnd_total"],
            "reciprocal_pairs": graph["reciprocal_pairs"],
            "without_declared_mate": graph["bnd_without_mate"],
            "unresolved_mate_references": graph["unresolved_mate_references"],
        },
        "events": {"resolved": graph["resolved_events"] + simple_events},
        "length_bp": {
            "policy_id": "vss-bins/1",
            **length_histogram.as_dict(),
            "missing": length_missing,
            "invalid": 0,
            "not_applicable": max(0, allele_count - length_histogram.n - length_missing),
        },
        "qual": {
            **qual_histogram.as_dict(),
            "missing": missing_qual,
            "invalid": invalid_qual,
        },
        "copy_number": dict(sorted(copy_number_counts.items())),
        "copy_number_quality": {
            **copy_number_quality_histogram.as_dict(),
            "missing": copy_number_quality_missing,
            "invalid": copy_number_quality_invalid,
        },
        "merged_support": {
            "status": (
                "present"
                if support_records_with_values
                else "declared_without_values"
                if support_declared_fields
                else "not_declared"
            ),
            "declared_fields": list(support_declared_fields),
            "records_with_support": support_records_with_values,
            "records_without_support": support_records_without_values,
            "supporting_sources": dict(sorted(support_count_counts.items())),
            "source_count_states": dict(sorted(support_source_count_states.items())),
            "vector_count_consistency": dict(sorted(support_consistency.items())),
            "interpretation": "merger_provenance_only",
        },
        "copy_number_interpretation": {
            "baseline_status": "unavailable",
            "reason": "no_explicit_baseline_context",
            "cnv_records_by_genotype_state": dict(sorted(cnv_genotype_states.items())),
            "gain_loss_neutral_inference": "not_performed",
        },
    }
    return ScanResult(header, callset, statistics, tuple(diagnostics), complete)
