#!/usr/bin/env python3
"""Build deterministic, sanitized, single-subject VCF fixtures.

The source directory and output directory are both mandatory. The builder stages the
complete corpus beside the requested output, validates it, and publishes it only after
all checks pass. Source VCFs and intermediate plain-text files are never copied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pysam
import pysam.bcftools

from vcf_sv_stats.engine import stats
from vcf_sv_stats.fixture_review import PENDING_REDISTRIBUTION_STATUS, apply_review, load_review
from vcf_sv_stats.models import OperationRequest
from vcf_sv_stats.serialization import file_sha256, json_bytes

SUBJECT = "HG002"
SANITIZATION_VERSION = "fixture-sanitizer/1"
MAX_CLOSURE_RECORDS = 128
MAX_CORPUS_RECORDS = 2_500
MAX_COMPRESSED_BYTES = 10 * 1024 * 1024
SUBJECT_TOKEN = re.compile(r"(?i)\b(?:HG\d{3}|NA\d{5}|GM\d{5})\b")
UNSAFE_VALUE = re.compile(
    r"(?i)(?:^|[/\\])(?:users|home|mnt|scratch|projects)(?:[/\\])|"
    r"(?:analysis[-_ ]?unit)|(?:s3|https?|ssh)://|[\w.+-]+@[\w.-]+"
)
PUBLIC_INFO_FIELDS = frozenset(
    """AF ALLVARS_EXT AVG_END AVG_LEN AVG_START BND BND_DEPTH BND_PAIR_COUNT CALLERS
    CHR2 CHR2_POS CIEND CIEND95 CIGAR CIPOS CIPOS95 CN CNT CONTIGA CONTIGB COVERAGE
    CT CTG DOWNSTREAM_PAIR_COUNT END ENDVARIANCE EXPSEQ EndDistance GC GRP GTMatch HOMLEN
    HOMSEQ IDLIST IDLIST_EXT IMPRECISE INTRASAMPLE_IDLIST KIND LCR LEFT_SVINSSEQ LFA LFB
    LPREC LR_SUPPORT LTE MAPQ MATEID MATE_BND_DEPTH ML_PROB MatchId Multi NEXP NGRP OL
    PAIR_COUNT PE PHASE PRECISE PRIMARY_SUPPORT PROBS PctRecOverlap PctSeqSimilarity
    PctSizeSimilarity REF_READS REGIONA REGIONB REMAP REP REPSC RIGHT_SVINSSEQ RM_clsfam
    RM_repeat RM_score RPOLY RT SC SOURCES SOURCE_IDS SR SRC_SVTYPE SR_SUPPORT STARTVARIANCE
    STDEV_LEN STDEV_POS STRAND STRANDS STRIDE SU SUPP SUPPORT SUPPORT_LONG SUPPORT_SA
    SUPP_EXT SUPP_READS SUPP_VEC SUPP_VEC_EXT SVLEN SVMETHOD SVTYPE SizeDiff StartDistance
    TRF TRFcopies TRFdiff TRFend TRFentropy TRFovl TRFperiod TRFrepeat TRFscore TRFsim
    TRFstart TruScore UPSTREAM_PAIR_COUNT VAF VARCALLS WR""".split()  # noqa: SIM905
)
PUBLIC_FORMAT_FIELDS = frozenset(
    """AD AF BCC BE BND CMP CN CO COV DP DP0S DPS DR DV ENDD FAS FCC FT GCS GQ GT HP
    ICN ISIZES JIT LN LNK LQ MAPQP MAPQS MAS MCOV MQS MS NDC NEIGH NEIGH10 NG NMB NMP
    NMS NMU NP NSA NXA OB0S OBS OCN PE PL POSD PR PROB PS PSET RAS RB RED RMS RR RV SBT
    SC SCS SCW SQC SQR SR STL SU TECH TY VAF WR hVAF""".split()  # noqa: SIM905
)


@dataclass(frozen=True, slots=True)
class SourceSpec:
    relative_path: str
    fixture_name: str
    source_signature: str


SOURCES: tuple[SourceSpec, ...] = (
    SourceSpec("vcfs/dysgu.native.vcf.gz", "dysgu.native", "DYSGU_1.8.0"),
    SourceSpec("vcfs/dysgu.normalized.vcf.gz", "dysgu.normalized", "DYSGU_1.8.0"),
    SourceSpec("vcfs/jasmine.merged.vcf.gz", "jasmine.merged", "Jasmine_1.1.5"),
    SourceSpec("vcfs/manta.native.vcf.gz", "manta.native", "Manta_1.6.0"),
    SourceSpec("vcfs/manta.normalized.vcf.gz", "manta.normalized", "Manta_1.6.0"),
    SourceSpec("vcfs/octopusv.merged.vcf.gz", "octopusv.merged", "OctopuSV_0.4.1"),
    SourceSpec(
        "vcfs/sentieon.cnvscope.vcf.gz",
        "sentieon.cnvscope",
        "Sentieon_CNVscope_202503.03",
    ),
    SourceSpec(
        "vcfs/sentieon.longreadsv.native.vcf.gz",
        "sentieon.longreadsv.native",
        "Sentieon_LongReadSV_202503.03",
    ),
    SourceSpec(
        "vcfs/sentieon.longreadsv.normalized.vcf.gz",
        "sentieon.longreadsv.normalized",
        "Sentieon_LongReadSV_202503.03",
    ),
    SourceSpec("vcfs/sniffles2.native.vcf.gz", "sniffles2.native", "Sniffles2_2.8.0"),
    SourceSpec(
        "vcfs/sniffles2.normalized.vcf.gz",
        "sniffles2.normalized",
        "Sniffles2_2.8.0",
    ),
    SourceSpec("vcfs/survivor.merged.vcf.gz", "survivor.merged", "SURVIVOR_1.0.6"),
    SourceSpec("vcfs/tiddit.native.vcf.gz", "tiddit.native", "TIDDIT-3.9.7"),
    SourceSpec("vcfs/tiddit.normalized.vcf.gz", "tiddit.normalized", "TIDDIT-3.9.7"),
    SourceSpec(
        "vcfs/tiddit.reference-repaired.vcf.gz",
        "tiddit.reference-repaired",
        "TIDDIT-3.9.7",
    ),
    SourceSpec("vcfs/trussv.merged.vcf.gz", "trussv.merged", "TrusSV_0.3.1"),
    SourceSpec(
        "vcfs/truari/query.del-ins-ge50.in-truth-bed.vcf.gz",
        "truvari.query",
        "Truari_fixture",
    ),
    SourceSpec(
        "vcfs/truari/truvari/fn.vcf.gz",
        "truvari.fn",
        "Truari_fixture",
    ),
    SourceSpec(
        "vcfs/truari/truvari/fp.vcf.gz",
        "truvari.fp",
        "Truari_fixture",
    ),
    SourceSpec(
        "vcfs/truari/truvari/tp-base.vcf.gz",
        "truvari.tp-base",
        "Truari_fixture",
    ),
    SourceSpec(
        "vcfs/truari/truvari/tp-comp.vcf.gz",
        "truvari.tp-comp",
        "Truari_fixture",
    ),
)


@dataclass(frozen=True, slots=True)
class RecordFacts:
    ordinal: int
    record_id: str | None
    relationships: tuple[str, ...]
    features: frozenset[str]


def _sha_token(namespace: str, value: str, length: int = 16) -> str:
    digest = hashlib.sha256(f"{namespace}\0{value}".encode()).hexdigest()
    return digest[:length]


def _target_count(source_records: int) -> int:
    return min(100, max(12, math.ceil(0.005 * source_records)))


def _single_subject_sample(path: Path) -> str:
    with pysam.VariantFile(str(path)) as variant:
        samples = tuple(variant.header.samples)
    if len(samples) != 1 or SUBJECT not in samples[0].upper():
        raise ValueError(f"Source is not a single-subject {SUBJECT} callset: {path.name}")
    return samples[0]


def _relationship_values(record: Any) -> tuple[str, ...]:
    values: list[str] = []
    if record.id not in {None, "."}:
        values.append(f"id:{record.id}")
    for key in ("MATEID", "PARID"):
        if key not in record.info:
            continue
        raw = record.info[key]
        items = raw if isinstance(raw, tuple) else (raw,)
        values.extend(f"id:{item}" for item in items if item not in {None, "."})
    if "EVENT" in record.info and record.info["EVENT"] not in {None, "."}:
        values.append(f"event:{record.info['EVENT']}")
    return tuple(sorted(set(values)))


def _record_features(record: Any, duplicate_ids: set[str]) -> frozenset[str]:
    alts = tuple(str(alt) for alt in (record.alts or ()))
    features: set[str] = set()
    if len(alts) > 1:
        features.add("multiallelic")
    for alt in alts:
        if alt.startswith("<") and alt.endswith(">"):
            features.add("representation:symbolic")
        elif "[" in alt or "]" in alt:
            features.add("representation:breakend")
        else:
            features.add("representation:sequence-resolved")
    svtype = record.info.get("SVTYPE") if "SVTYPE" in record.info else None
    if isinstance(svtype, tuple):
        svtype = svtype[0] if svtype else None
    if svtype:
        features.add(f"svtype:{str(svtype).upper()}")
    filters = tuple(str(value) for value in record.filter)
    if not filters:
        features.add("filter:missing")
    elif filters == ("PASS",):
        features.add("filter:pass")
    else:
        features.add("filter:filtered")
    if record.id in {None, "."}:
        features.add("id:missing")
    elif record.id in duplicate_ids:
        features.add("id:duplicate")
    if any("[" in alt or "]" in alt for alt in alts):
        features.add("bnd:with-mate" if "MATEID" in record.info else "bnd:orphan-or-single")
    if any(key in record.info for key in ("SUPP_VEC", "SUPP", "SOURCES", "CALLERS")):
        features.add("merged:support-vector")
    for sample in record.samples.values():
        gt = sample.get("GT")
        if gt is None or any(value is None for value in gt):
            features.add("genotype:no-call")
        elif all(value == 0 for value in gt):
            features.add("genotype:reference")
        elif len(gt) == 2 and gt[0] == gt[1] and gt[0] > 0:
            features.add("genotype:homozygous-alt")
        elif any(value > 0 for value in gt):
            features.add("genotype:heterozygous-or-other-alt")
        if "CN" in sample:
            value = sample.get("CN")
            if value is None:
                cn_state = "missing"
            elif value == 0:
                cn_state = "zero"
            elif value == 1:
                cn_state = "one"
            elif value == 2:
                cn_state = "two"
            elif isinstance(value, (int, float)) and value > 2:
                cn_state = "gain"
            else:
                cn_state = "other"
            features.add(f"copy-number:{cn_state}")
    for key, definition in record.header.info.items():
        if key not in record.info or definition.number not in {"A", "R"}:
            continue
        raw = record.info[key]
        observed = len(raw) if isinstance(raw, tuple) else 1
        expected = len(alts) + (1 if definition.number == "R" else 0)
        if observed != expected:
            features.add("cardinality:deviation")
    return frozenset(features)


def _inventory(path: Path) -> tuple[list[RecordFacts], dict[str, list[int]], Counter[str]]:
    id_counts: Counter[str] = Counter()
    with pysam.VariantFile(str(path)) as variant:
        for record in variant:
            if record.id not in {None, "."}:
                id_counts[str(record.id)] += 1
    duplicate_ids = {record_id for record_id, count in id_counts.items() if count > 1}
    facts: list[RecordFacts] = []
    groups: dict[str, list[int]] = defaultdict(list)
    with pysam.VariantFile(str(path)) as variant:
        for ordinal, record in enumerate(variant, start=1):
            relationships = _relationship_values(record)
            facts.append(
                RecordFacts(
                    ordinal,
                    None if record.id in {None, "."} else str(record.id),
                    relationships,
                    _record_features(record, duplicate_ids),
                )
            )
            for relationship in relationships:
                groups[relationship].append(ordinal)
    return facts, groups, id_counts


def _relationship_components(
    facts: list[RecordFacts], groups: dict[str, list[int]]
) -> dict[int, frozenset[int]]:
    parent = list(range(len(facts) + 1))

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for ordinals in groups.values():
        if not ordinals:
            continue
        first = ordinals[0]
        for ordinal in ordinals[1:]:
            union(first, ordinal)
    members: dict[int, set[int]] = defaultdict(set)
    for fact in facts:
        members[find(fact.ordinal)].add(fact.ordinal)
    frozen = {root: frozenset(values) for root, values in members.items()}
    return {fact.ordinal: frozen[find(fact.ordinal)] for fact in facts}


def _candidate_closure(
    selected: set[int],
    ordinal: int,
    components: dict[int, frozenset[int]],
) -> set[int] | None:
    component = components[ordinal]
    if len(component) > MAX_CLOSURE_RECORDS:
        return None
    candidate = set(selected)
    candidate.update(component)
    return candidate if len(candidate) <= MAX_CLOSURE_RECORDS else None


def _select(
    facts: list[RecordFacts], groups: dict[str, list[int]]
) -> tuple[set[int], list[str], list[str]]:
    target = min(_target_count(len(facts)), MAX_CLOSURE_RECORDS)
    universe = set().union(*(fact.features for fact in facts)) if facts else set()
    uncovered = set(universe)
    selected: set[int] = set()
    components = _relationship_components(facts, groups)
    eligible = [fact for fact in facts if len(components[fact.ordinal]) <= MAX_CLOSURE_RECORDS]
    while uncovered:
        candidates = []
        for fact in eligible:
            closure = _candidate_closure(selected, fact.ordinal, components)
            gain = len(fact.features & uncovered)
            if closure is not None and gain:
                candidates.append((gain, -len(closure), -fact.ordinal, fact, closure))
        if not candidates:
            break
        _gain, _size, _ordinal, best, selected = max(candidates, key=lambda item: item[:3])
        uncovered -= best.features
    if facts and len(selected) < target:
        for index in range(target):
            ordinal = facts[min(len(facts) - 1, (index * len(facts)) // target)].ordinal
            closure = _candidate_closure(selected, ordinal, components)
            if closure is not None:
                selected = closure
            if len(selected) >= target:
                break
    if len(selected) < target:
        for fact in facts:
            closure = _candidate_closure(selected, fact.ordinal, components)
            if closure is not None:
                selected = closure
            if len(selected) >= target:
                break
    if not selected and facts:
        selected.add(1)
    features = sorted(set().union(*(facts[index - 1].features for index in selected)))
    return selected, features, sorted(universe - set(features))


def _neutral_id_map(fixture_name: str, facts: list[RecordFacts]) -> dict[str, str]:
    counts = Counter(fact.record_id for fact in facts if fact.record_id is not None)
    mapping: dict[str, str] = {}
    for fact in facts:
        if fact.record_id is None or fact.record_id in mapping:
            continue
        prefix = "dup" if counts[fact.record_id] > 1 else "vss"
        mapping[fact.record_id] = f"{prefix}-{_sha_token(fixture_name, fact.record_id)}"
    return mapping


def _neutral_reference_value(fixture_name: str, key: str, value: str) -> str:
    if value in {"", "."}:
        return value
    return f"ref-{_sha_token(f'{fixture_name}:{key}', value)}"


def _sanitize_info(
    value: str,
    fixture_name: str,
    id_map: dict[str, str],
) -> tuple[str, set[str]]:
    if value in {"", "."}:
        return value, set()
    fields: list[str] = []
    keys: set[str] = set()
    for item in value.split(";"):
        key, separator, raw = item.partition("=")
        if key not in PUBLIC_INFO_FIELDS:
            continue
        keys.add(key)
        if not separator:
            fields.append(key)
            continue
        if key in {"MATEID", "PARID"}:
            raw = ",".join(
                id_map.get(part, _neutral_reference_value(fixture_name, key, part))
                for part in raw.split(",")
            )
        elif key == "EVENT" or "ID" in key.upper() or key in {"RNAMES", "RTID"}:
            raw = ",".join(
                _neutral_reference_value(fixture_name, key, part) for part in raw.split(",")
            )
        elif UNSAFE_VALUE.search(raw):
            raw = _neutral_reference_value(fixture_name, key, raw)
        fields.append(f"{key}={raw}")
    return ";".join(fields) if fields else ".", keys


def _sanitize_format(format_value: str, sample_value: str) -> tuple[str, str, set[str]]:
    if format_value in {"", "."}:
        return ".", ".", set()
    keys = format_value.split(":")
    values = sample_value.split(":")
    kept: list[tuple[str, str]] = []
    for index, key in enumerate(keys):
        if key not in PUBLIC_FORMAT_FIELDS:
            continue
        raw = values[index] if index < len(values) else "."
        if UNSAFE_VALUE.search(raw):
            raw = "."
        kept.append((key, raw))
    if not kept:
        return ".", ".", set()
    return (
        ":".join(key for key, _ in kept),
        ":".join(raw for _, raw in kept),
        {key for key, _ in kept},
    )


def _meta_number(value: Any) -> str:
    return str(value if value is not None else ".")


def _escape_meta(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _build_header(
    source_header: Any,
    source_signature: str,
    contigs: set[str],
    alts: set[str],
    filters: set[str],
    infos: set[str],
    formats: set[str],
) -> list[str]:
    lines = [
        "##fileformat=VCFv4.3",
        f"##source={source_signature}",
        "##reference=GRCh38",
        f"##fixture_subject={SUBJECT}",
        f"##fixture_sanitization={SANITIZATION_VERSION}",
    ]
    for contig in source_header.contigs:
        if contig not in contigs:
            continue
        length = source_header.contigs[contig].length
        suffix = "" if length is None else f",length={length}"
        lines.append(f"##contig=<ID={contig}{suffix}>")
    for alt in sorted(alts):
        lines.append(f'##ALT=<ID={alt},Description="Retained symbolic allele {alt}">')
    for value in sorted(filters - {"PASS"}):
        lines.append(f'##FILTER=<ID={value},Description="Retained public filter {value}">')
    for key in sorted(infos):
        if key not in source_header.info:
            continue
        definition = source_header.info[key]
        lines.append(
            f"##INFO=<ID={key},Number={_meta_number(definition.number)},"
            f'Type={definition.type},Description="Retained public INFO field {_escape_meta(key)}">'
        )
    for key in sorted(formats):
        if key not in source_header.formats:
            continue
        definition = source_header.formats[key]
        lines.append(
            f"##FORMAT=<ID={key},Number={_meta_number(definition.number)},"
            f"Type={definition.type},"
            f'Description="Retained public FORMAT field {_escape_meta(key)}">'
        )
    lines.append("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tHG002")
    return lines


def _sanitize_records(
    source: Path,
    fixture_name: str,
    source_signature: str,
    selected: set[int],
    facts: list[RecordFacts],
) -> tuple[list[str], list[str]]:
    id_map = _neutral_id_map(fixture_name, facts)
    rows: list[str] = []
    used_contigs: set[str] = set()
    used_alts: set[str] = set()
    used_filters: set[str] = set()
    used_infos: set[str] = set()
    used_formats: set[str] = set()
    with pysam.VariantFile(str(source)) as variant:
        source_header = variant.header.copy()
        for ordinal, record in enumerate(variant, start=1):
            if ordinal not in selected:
                continue
            columns = str(record).rstrip("\n").split("\t")
            if len(columns) != 10:
                raise ValueError(f"Expected one sample column in {source.name}")
            used_contigs.add(columns[0])
            columns[2] = "." if columns[2] == "." else id_map[str(record.id)]
            for alt in columns[4].split(","):
                if alt.startswith("<") and alt.endswith(">"):
                    used_alts.add(alt[1:-1])
            used_filters.update(value for value in columns[6].split(";") if value != ".")
            columns[7], info_keys = _sanitize_info(columns[7], fixture_name, id_map)
            columns[8], columns[9], format_keys = _sanitize_format(columns[8], columns[9])
            used_infos.update(info_keys)
            used_formats.update(format_keys)
            rows.append("\t".join(columns))
    header = _build_header(
        source_header,
        source_signature,
        used_contigs,
        used_alts,
        used_filters,
        used_infos,
        used_formats,
    )
    return header, rows


def _write_fixture(plain: Path, compressed: Path, header: list[str], rows: list[str]) -> Path:
    plain.write_text("\n".join((*header, *rows, "")), encoding="utf-8")
    pysam.tabix_compress(str(plain), str(compressed), force=True)
    indexed = pysam.tabix_index(str(compressed), preset="vcf", force=True)
    if Path(indexed) != compressed:
        raise ValueError("Indexer changed the fixture data path")
    index = Path(str(compressed) + ".tbi")
    with pysam.VariantFile(str(compressed)) as variant:
        if tuple(variant.header.samples) != (SUBJECT,):
            raise ValueError(f"Fixture sample is not exactly {SUBJECT}: {compressed.name}")
        observed = sum(1 for _ in variant)
    if observed != len(rows) or not index.is_file():
        raise ValueError(f"Fixture or index validation failed: {compressed.name}")
    return index


def _expected_output(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    result = stats(OperationRequest(path))
    value = {
        "fixture": path.name,
        "detection": result.summary["callset"]["producer"],
        "callset": {
            key: result.summary["callset"][key]
            for key in ("vcf_sample_ids", "single_sample", "record_count", "allele_count")
        },
        "statistics": result.summary["statistics"],
        "diagnostic_codes": sorted(item.code for item in result.diagnostics),
    }
    return value, [item.as_dict() for item in result.diagnostics]


def _build_bcf(source: Path, destination: Path) -> Path:
    with (
        pysam.VariantFile(str(source)) as input_variant,
        pysam.VariantFile(str(destination), "wb", header=input_variant.header) as output_variant,
    ):
        for record in input_variant:
            output_variant.write(record)
    pysam.bcftools.index("--csi", "--force", str(destination), catch_stdout=False)
    index = Path(str(destination) + ".csi")
    with pysam.VariantFile(str(destination)) as variant:
        if tuple(variant.header.samples) != (SUBJECT,):
            raise ValueError("Derived BCF sample validation failed")
        sum(1 for _ in variant)
    return index


def _verify_subject_tokens(root: Path) -> None:
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix in {".tbi", ".csi", ".bcf"}:
            continue
        if path.suffix == ".gz":
            with pysam.BGZFile(str(path), "rb") as handle:
                text = handle.read().decode("utf-8")
        else:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
        unexpected = {token.upper() for token in SUBJECT_TOKEN.findall(text)} - {SUBJECT}
        if unexpected:
            raise ValueError(f"Unexpected subject token in {path.name}")


def _plain_query_source(source_dir: Path) -> Path:
    return source_dir / "vcfs/truari/query.del-ins-ge50.in-truth-bed.vcf"


def build(
    source_dir: Path,
    output_dir: Path,
    redistribution_review: Path | None = None,
) -> None:
    if not source_dir.is_dir():
        raise ValueError(f"Source directory does not exist: {source_dir}")
    if output_dir.exists():
        raise ValueError(f"Output directory already exists: {output_dir}")
    for spec in SOURCES:
        if not (source_dir / spec.relative_path).is_file():
            raise ValueError(f"Required source VCF is missing: {spec.relative_path}")

    stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.stage.", dir=output_dir.parent))
    try:
        vcf_dir = stage / "vcf"
        expected_dir = stage / "expected"
        vcf_dir.mkdir()
        expected_dir.mkdir()
        manifest_entries: list[dict[str, Any]] = []
        corpus_records = 0
        source_identity_evidence: list[dict[str, Any]] = []

        all_identity_paths = [source_dir / spec.relative_path for spec in SOURCES]
        all_identity_paths.append(_plain_query_source(source_dir))
        for path in all_identity_paths:
            sample = _single_subject_sample(path)
            source_identity_evidence.append(
                {
                    "source_path": str(path.relative_to(source_dir)),
                    "source_sha256": file_sha256(path),
                    "sample_count": 1,
                    "subject_evidence": (
                        "sample_is_hg002" if sample == SUBJECT else "single_hg002_derived_alias"
                    ),
                }
            )

        for spec in SOURCES:
            source = source_dir / spec.relative_path
            facts, groups, _id_counts = _inventory(source)
            selected, features, excluded_features = _select(facts, groups)
            header, rows = _sanitize_records(
                source,
                spec.fixture_name,
                spec.source_signature,
                selected,
                facts,
            )
            plain = stage / f".{spec.fixture_name}.intermediate.vcf"
            compressed = vcf_dir / f"{spec.fixture_name}.hg002.subset.vcf.gz"
            index = _write_fixture(plain, compressed, header, rows)
            if spec.fixture_name == "truvari.query":
                shutil.copyfile(plain, vcf_dir / "truvari.query.hg002.subset.vcf")
            plain.unlink()
            expected, diagnostics = _expected_output(compressed)
            expected_path = expected_dir / f"{spec.fixture_name}.expected.json"
            expected_path.write_bytes(json_bytes(expected))
            diagnostics_path = expected_dir / f"{spec.fixture_name}.diagnostics.jsonl"
            diagnostics_path.write_text(
                "".join(json.dumps(item, sort_keys=True) + "\n" for item in diagnostics),
                encoding="utf-8",
            )
            corpus_records += len(rows)
            manifest_entries.append(
                {
                    "fixture_id": spec.fixture_name,
                    "source_basename": source.name,
                    "source_sha256": file_sha256(source),
                    "source_record_count": len(facts),
                    "fixture_record_count": len(rows),
                    "subject": SUBJECT,
                    "selected_behavior_classes": features,
                    "oversized_relationship_exclusions": excluded_features,
                    "sanitization_version": SANITIZATION_VERSION,
                    "fixture_path": str(compressed.relative_to(stage)),
                    "fixture_sha256": file_sha256(compressed),
                    "index_sha256": file_sha256(index),
                    "redistribution_status": PENDING_REDISTRIBUTION_STATUS,
                }
            )

        parity_source = vcf_dir / "manta.native.hg002.subset.vcf.gz"
        bcf = vcf_dir / "manta.native.hg002.subset.bcf"
        bcf_index = _build_bcf(parity_source, bcf)
        parity_record_count = next(
            entry["fixture_record_count"]
            for entry in manifest_entries
            if entry["fixture_id"] == "manta.native"
        )
        query_plain = vcf_dir / "truvari.query.hg002.subset.vcf"
        query_record_count = next(
            entry["fixture_record_count"]
            for entry in manifest_entries
            if entry["fixture_id"] == "truvari.query"
        )
        manifest = {
            "schema_name": "vcf-sv-stats.fixture-manifest",
            "schema_version": "1.0.0",
            "subject": SUBJECT,
            "sanitization_version": SANITIZATION_VERSION,
            "selection_policy": {
                "target": "min(100,max(12,ceil(0.005*source_records)))",
                "relationship_closure_limit": MAX_CLOSURE_RECORDS,
                "method": "deterministic behavior set-cover plus coordinate-order quantiles",
            },
            "source_identity_evidence": source_identity_evidence,
            "fixtures": manifest_entries,
            "derived_parity_artifacts": [
                {
                    "fixture_path": str(bcf.relative_to(stage)),
                    "fixture_sha256": file_sha256(bcf),
                    "index_sha256": file_sha256(bcf_index),
                    "fixture_record_count": parity_record_count,
                    "derived_from": parity_source.name,
                    "subject": SUBJECT,
                    "redistribution_status": PENDING_REDISTRIBUTION_STATUS,
                },
                {
                    "fixture_path": str(query_plain.relative_to(stage)),
                    "fixture_sha256": file_sha256(query_plain),
                    "fixture_record_count": query_record_count,
                    "derived_from": "truvari.query.hg002.subset.vcf.gz",
                    "subject": SUBJECT,
                    "redistribution_status": PENDING_REDISTRIBUTION_STATUS,
                },
            ],
            "totals": {
                "source_derived_records": corpus_records,
                "compressed_vcf_bytes": sum(
                    path.stat().st_size for path in vcf_dir.glob("*.vcf.gz")
                ),
            },
        }
        if redistribution_review is not None:
            apply_review(manifest, load_review(redistribution_review))
            shutil.copyfile(redistribution_review, stage / "redistribution-review.json")
        (stage / "manifest.json").write_bytes(json_bytes(manifest))
        (stage / "NOTICE.md").write_text(
            "# Fixture notice\n\n"
            "These deterministic, heavily subsampled fixtures contain public HG002 "
            "Genome in a Bottle data on GRCh38 coordinates. The source data are made "
            "available by the National Institute of Standards and Technology Genome "
            "in a Bottle program. Caller signatures identify Manta 1.6.0, TIDDIT 3.9.7, "
            "dysgu 1.8.0, Sniffles2 2.8.0, Sentieon 202503.03, Jasmine 1.1.5, "
            "SURVIVOR 1.0.6, OctopuSV 0.4.1, and TrusSV 0.3.1 outputs. No original "
            "source VCF is redistributed.\n\n"
            "Each manifest entry records the fixture-level redistribution decision. The\n"
            "fixtures contain factual public-subject observations and factual\n"
            "producer/version attribution, not caller source code or binaries. Caller\n"
            "software remains subject to its own license. The fixture corpus was\n"
            "eligible for a reviewed disposition only when its exact manifest digest\n"
            "matches an explicitly supplied redistribution-review policy; publication\n"
            "remains a separately approved gate.\n",
            encoding="utf-8",
        )
        if corpus_records > MAX_CORPUS_RECORDS:
            raise ValueError(f"Fixture corpus exceeds {MAX_CORPUS_RECORDS} records")
        if manifest["totals"]["compressed_vcf_bytes"] > MAX_COMPRESSED_BYTES:
            raise ValueError(f"Fixture corpus exceeds {MAX_COMPRESSED_BYTES} compressed bytes")
        _verify_subject_tokens(stage)
        os.replace(stage, output_dir)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--redistribution-review", type=Path)
    args = parser.parse_args()
    review = (
        args.redistribution_review.resolve(strict=True)
        if args.redistribution_review is not None
        else None
    )
    build(
        args.source_dir.resolve(strict=True),
        args.output_dir.resolve(strict=False),
        review,
    )


if __name__ == "__main__":
    main()
