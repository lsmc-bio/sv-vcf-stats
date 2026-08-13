"""Digest-bound local source manifests and conservative lineage comparison."""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .adapters import detect_adapter
from .exceptions import InputError, ValidationFailure
from .io import open_variant
from .schemas import validate_artifact
from .serialization import file_sha256
from .vcf45 import parse_header_contract


@dataclass(frozen=True, slots=True)
class SourceManifestEntry:
    producer_label: str
    path: Path
    display_name: str
    sha256: str
    artifact_role: str
    adapter_id: str
    record_namespace: str
    source_id_fields: tuple[str, ...]
    relationship_fields: tuple[str, ...]
    support_ordinal: int | None
    index_path: Path | None = None
    index_sha256: str | None = None


@dataclass(frozen=True, slots=True)
class SourceManifest:
    combined_sha256: str
    sources: tuple[SourceManifestEntry, ...]


@dataclass(frozen=True, slots=True)
class AlleleFact:
    ordinal: int
    allele_ordinal: int
    chrom: str
    pos: int
    ref: str
    alt: str
    record_id: str | None
    mate_ids: tuple[str, ...]
    event_ids: tuple[str, ...]
    info_values: dict[str, tuple[str, ...]]

    @property
    def allele_key(self) -> tuple[str, int, str, str]:
        return (self.chrom, self.pos, self.ref, self.alt)


def _local_path(value: str, *, base_dir: Path) -> Path:
    parsed = urlparse(value)
    if parsed.scheme:
        raise InputError("Source manifests accept local paths only")
    candidate = Path(value)
    resolved = (
        (base_dir / candidate).resolve(strict=True)
        if not candidate.is_absolute()
        else candidate.resolve(strict=True)
    )
    if not resolved.is_file():
        raise InputError(f"Source-manifest member is not a regular file: {resolved.name}")
    return resolved


def _same_file(left: Path, right: Path) -> bool:
    try:
        return os.path.samefile(left, right)
    except OSError as exc:
        raise InputError(f"Unable to compare source-manifest file identities: {exc}") from exc


def load_source_manifest(
    manifest_path: str | Path,
    *,
    combined_path: str | Path,
) -> SourceManifest:
    manifest_file = Path(manifest_path).resolve(strict=True)
    if not manifest_file.is_file():
        raise InputError("Source manifest must be a regular local file")
    try:
        value = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InputError(f"Unable to read source manifest: {exc}") from exc
    validate_artifact("source-manifest", value)

    combined = Path(combined_path).resolve(strict=True)
    observed_combined_sha = file_sha256(combined)
    if value["combined_sha256"] != observed_combined_sha:
        raise ValidationFailure("Source manifest combined-artifact digest does not match")

    entries: list[SourceManifestEntry] = []
    labels: set[str] = set()
    namespaces: set[str] = set()
    identities: list[Path] = [combined, manifest_file]
    support_ordinals: list[int | None] = []
    for raw in value["sources"]:
        label = str(raw["producer_label"])
        namespace = str(raw["record_namespace"])
        if label in labels:
            raise ValidationFailure("Source-manifest producer labels must be unique")
        if namespace in namespaces:
            raise ValidationFailure("Source-manifest record namespaces must be unique")
        labels.add(label)
        namespaces.add(namespace)
        source_path = _local_path(str(raw["path"]), base_dir=manifest_file.parent)
        if any(_same_file(source_path, prior) for prior in identities):
            raise ValidationFailure("Source-manifest members must not alias another input")
        identities.append(source_path)
        observed_sha = file_sha256(source_path)
        if observed_sha != raw["sha256"]:
            raise ValidationFailure(f"Source digest does not match for label {label}")

        index_path: Path | None = None
        index_sha: str | None = None
        if "index" in raw:
            index_path = _local_path(str(raw["index"]["path"]), base_dir=manifest_file.parent)
            if any(_same_file(index_path, prior) for prior in identities):
                raise ValidationFailure("Source-manifest index must not alias another input")
            identities.append(index_path)
            index_sha = file_sha256(index_path)
            if index_sha != raw["index"]["sha256"]:
                raise ValidationFailure(f"Source index digest does not match for label {label}")

        with open_variant(source_path) as variant:
            header_text = str(variant.header)
        adapter_id = str(raw["adapter_id"])
        if adapter_id != "generic":
            detection = detect_adapter(header_text)
            if detection.selected.adapter_id != adapter_id:
                raise ValidationFailure(f"Source adapter does not match for label {label}")
        provenance = raw["merger_provenance"]
        support_ordinal = provenance.get("support_ordinal")
        support_ordinals.append(None if support_ordinal is None else int(support_ordinal))
        entries.append(
            SourceManifestEntry(
                producer_label=label,
                path=source_path,
                display_name=str(raw["display_name"]),
                sha256=observed_sha,
                artifact_role=str(raw["artifact_role"]),
                adapter_id=adapter_id,
                record_namespace=namespace,
                source_id_fields=tuple(str(item) for item in provenance["source_id_fields"]),
                relationship_fields=tuple(str(item) for item in provenance["relationship_fields"]),
                support_ordinal=None if support_ordinal is None else int(support_ordinal),
                index_path=index_path,
                index_sha256=index_sha,
            )
        )
    if any(item is not None for item in support_ordinals):
        expected = list(range(len(entries)))
        if support_ordinals != expected:
            raise ValidationFailure(
                "Source-manifest support ordinals must be complete and match source order"
            )
    return SourceManifest(observed_combined_sha, tuple(entries))


def _info_values(raw: str) -> dict[str, tuple[str, ...]]:
    values: dict[str, tuple[str, ...]] = {}
    if raw == ".":
        return values
    for item in raw.split(";"):
        key, separator, value = item.partition("=")
        if separator:
            values[key] = tuple(value.split(","))
    return values


def _facts(path: Path) -> tuple[AlleleFact, ...]:
    facts: list[AlleleFact] = []
    with open_variant(path) as variant:
        contract = parse_header_contract(str(variant.header))
        for ordinal, record in enumerate(variant, start=1):
            columns = str(record).rstrip("\n").split("\t")
            info = _info_values(columns[7])
            for allele_ordinal, alt in enumerate(record.alts or (), start=1):
                allele_info: dict[str, tuple[str, ...]] = {}
                for field_name, values in info.items():
                    definition = contract.info.get(field_name)
                    if (
                        definition is not None
                        and definition.number == "A"
                        and len(values) == len(record.alts or ())
                    ):
                        allele_info[field_name] = (values[allele_ordinal - 1],)
                    else:
                        allele_info[field_name] = values
                mate_ids = tuple(
                    item for item in allele_info.get("MATEID", ()) if item != "."
                )
                event_ids = tuple(
                    item for item in allele_info.get("EVENT", ()) if item != "."
                )
                facts.append(
                    AlleleFact(
                        ordinal=ordinal,
                        allele_ordinal=allele_ordinal,
                        chrom=str(record.contig),
                        pos=int(record.pos),
                        ref=str(record.ref),
                        alt=str(alt),
                        record_id=None if record.id in {None, "."} else str(record.id),
                        mate_ids=mate_ids,
                        event_ids=event_ids,
                        info_values=allele_info,
                    )
                )
    return tuple(facts)


def _opaque_key(digest: str, namespace: str, ordinal: int, allele_ordinal: int) -> str:
    return f"{namespace}:{digest[:16]}:{ordinal}:{allele_ordinal}"


def compare_sources(
    combined_path: str | Path,
    manifest_path: str | Path,
) -> tuple[tuple[dict[str, Any], ...], dict[str, Any]]:
    """Compare declared sources without inferring merger topology or safe repair."""
    combined = Path(combined_path).resolve(strict=True)
    manifest = load_source_manifest(manifest_path, combined_path=combined)
    combined_facts = _facts(combined)
    by_allele: dict[tuple[str, int, str, str], list[AlleleFact]] = defaultdict(list)
    for fact in combined_facts:
        by_allele[fact.allele_key].append(fact)

    entry_facts = tuple((entry, _facts(entry.path)) for entry in manifest.sources)
    source_by_id: dict[tuple[int, str], list[AlleleFact]] = defaultdict(list)
    source_by_event: dict[tuple[int, str], list[AlleleFact]] = defaultdict(list)
    for entry_index, (_entry, facts) in enumerate(entry_facts):
        for fact in facts:
            if fact.record_id is not None:
                source_by_id[(entry_index, fact.record_id)].append(fact)
            for event_id in fact.event_ids:
                source_by_event[(entry_index, event_id)].append(fact)

    def fact_key(fact: AlleleFact) -> tuple[int, int]:
        return (fact.ordinal, fact.allele_ordinal)

    def source_identity(entry_index: int, fact: AlleleFact) -> tuple[int, int, int]:
        return (entry_index, fact.ordinal, fact.allele_ordinal)

    def declared_tokens(
        fact: AlleleFact,
        field_names: tuple[str, ...],
    ) -> set[str]:
        return {
            token
            for field_name in field_names
            for token in fact.info_values.get(field_name, ())
            if token not in {"", "."}
        }

    candidate_map: dict[tuple[int, int, int], tuple[AlleleFact, ...]] = {}
    match_basis_map: dict[tuple[int, int, int], tuple[str, ...]] = {}
    for entry_index, (entry, facts) in enumerate(entry_facts):
        for source in facts:
            exact = {fact_key(item): item for item in by_allele.get(source.allele_key, ())}
            by_id: dict[tuple[int, int], AlleleFact] = {}
            if source.record_id is not None:
                for item in combined_facts:
                    if source.record_id == item.record_id or source.record_id in declared_tokens(
                        item, entry.source_id_fields
                    ):
                        by_id[fact_key(item)] = item
            basis = []
            if exact:
                basis.append("allele")
            if by_id:
                basis.append("declared_source_id")
            if exact and by_id:
                intersection = set(exact) & set(by_id)
                candidate_values = (
                    {key: exact[key] for key in intersection}
                    if intersection
                    else {**exact, **by_id}
                )
                if not intersection:
                    basis.append("conflicting_evidence")
            else:
                candidate_values = exact or by_id
            identity = source_identity(entry_index, source)
            candidate_map[identity] = tuple(
                candidate_values[key] for key in sorted(candidate_values)
            )
            match_basis_map[identity] = tuple(basis)

    selected_map = {
        identity: candidates[0] if len(candidates) == 1 else None
        for identity, candidates in candidate_map.items()
    }

    def mate_preserved(
        entry_index: int,
        entry: SourceManifestEntry,
        selected: AlleleFact,
        mate_id: str,
    ) -> bool:
        target_sources = source_by_id.get((entry_index, mate_id), ())
        target_candidates = {
            fact_key(candidate): candidate
            for target in target_sources
            if (
                candidate := selected_map.get(source_identity(entry_index, target))
            )
            is not None
        }
        if not target_sources or len(target_candidates) != 1:
            return False
        target = next(iter(target_candidates.values()))
        if target.record_id is None:
            return False
        relationship_fields = tuple(
            field_name
            for field_name in entry.relationship_fields
            if field_name in {"MATEID", "PARID"}
        )
        return target.record_id in declared_tokens(selected, relationship_fields)

    def event_preserved(
        entry_index: int,
        entry: SourceManifestEntry,
        selected: AlleleFact,
        event_id: str,
    ) -> bool:
        if "EVENT" not in entry.relationship_fields:
            return False
        members = source_by_event.get((entry_index, event_id), ())
        selected_members = [
            selected_map.get(source_identity(entry_index, member)) for member in members
        ]
        if not members or any(item is None for item in selected_members):
            return False
        event_sets = [
            declared_tokens(item, ("EVENT",))
            for item in selected_members
            if item is not None
        ]
        if not event_sets:
            return False
        shared = set.intersection(*event_sets)
        return bool(shared & declared_tokens(selected, ("EVENT",)))

    comparisons: list[dict[str, Any]] = []
    for entry_index, (entry, facts) in enumerate(entry_facts):
        for source in facts:
            identity = source_identity(entry_index, source)
            source_candidates = candidate_map[identity]
            source_relationships = tuple(
                token for token in (*source.mate_ids, *source.event_ids) if token not in {"", "."}
            )
            selected = selected_map[identity]
            if len(source_candidates) == 1:
                assert selected is not None
                allele_preserved = selected.allele_key == source.allele_key
                endpoint_preserved = (selected.chrom, selected.pos) == (
                    source.chrom,
                    source.pos,
                )
                identifier_preserved = (
                    source.record_id is None
                    or source.record_id == selected.record_id
                    or source.record_id in declared_tokens(selected, entry.source_id_fields)
                )
                relationships_preserved = all(
                    mate_preserved(entry_index, entry, selected, mate_id)
                    for mate_id in source.mate_ids
                ) and all(
                    event_preserved(entry_index, entry, selected, event_id)
                    for event_id in source.event_ids
                )
                vector = next(iter(selected.info_values.get("SUPP_VEC", ())), None)
                if entry.support_ordinal is None or vector is None or vector == ".":
                    support_order_preserved = True
                    support_order_state = "not_observed"
                else:
                    support_order_preserved = (
                        len(vector) == len(manifest.sources)
                        and set(vector) <= {"0", "1"}
                        and vector[entry.support_ordinal] == "1"
                    )
                    support_order_state = (
                        "preserved" if support_order_preserved else "not_preserved"
                    )
                status = (
                    "preserved"
                    if allele_preserved
                    and endpoint_preserved
                    and identifier_preserved
                    and relationships_preserved
                    and support_order_preserved
                    else "not_preserved"
                )
            elif len(source_candidates) > 1:
                allele_preserved = False
                endpoint_preserved = False
                identifier_preserved = False
                relationships_preserved = False
                support_order_preserved = False
                support_order_state = "ambiguous"
                status = "ambiguous"
            else:
                allele_preserved = False
                endpoint_preserved = False
                identifier_preserved = False
                relationships_preserved = False
                support_order_preserved = False
                support_order_state = "not_found"
                status = "not_found"
            source_key = _opaque_key(
                entry.sha256,
                entry.record_namespace,
                source.ordinal,
                source.allele_ordinal,
            )
            combined_key = (
                None
                if selected is None
                else _opaque_key(
                    manifest.combined_sha256,
                    "combined",
                    selected.ordinal,
                    selected.allele_ordinal,
                )
            )
            comparisons.append(
                {
                    "source_label": entry.producer_label,
                    "source_sha256": entry.sha256,
                    "source_record_key": source_key,
                    "source_record_ordinal": source.ordinal,
                    "source_allele_ordinal": source.allele_ordinal,
                    "combined_record_key": combined_key,
                    "status": status,
                    "dimensions": {
                        "allele": allele_preserved,
                        "endpoint": endpoint_preserved,
                        "record_id": identifier_preserved,
                        "relationships": relationships_preserved,
                        "support_order": support_order_preserved,
                    },
                    "evidence": {
                        "candidate_count": len(source_candidates),
                        "match_basis": list(match_basis_map[identity]),
                        "support_order": support_order_state,
                    },
                    "source_relationship_available": bool(source_relationships),
                    "merged_relationship_preserved": relationships_preserved,
                    "safe_reinsertion": False,
                }
            )
    status_counts = Counter(item["status"] for item in comparisons)
    evidence = {
        "manifest_schema": "urn:vcf-sv-stats:schema:source-manifest:1.0.0",
        "combined_sha256": manifest.combined_sha256,
        "source_count": len(manifest.sources),
        "comparison_count": len(comparisons),
        "status_counts": dict(sorted(status_counts.items())),
        "source_order": [entry.producer_label for entry in manifest.sources],
        "normalization_authority": "comparison_only",
        "safe_reinsertion_proposed": False,
    }
    return tuple(comparisons), evidence


__all__ = [
    "SourceManifest",
    "SourceManifestEntry",
    "compare_sources",
    "load_source_manifest",
]
