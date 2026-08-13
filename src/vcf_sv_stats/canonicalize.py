"""Lossless, two-pass canonical splitting for finalized VCF 4.5 records.

The transformation operates on textual records so that VCF 4.5 cardinality
symbols remain available even when the Python binding's typed metadata API
predates them.  HTSlib remains responsible for container encoding and indexes.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from itertools import combinations_with_replacement
from pathlib import Path

from .exceptions import OutputError, ValidationFailure
from .io import iter_record_texts, open_variant
from .vcf45 import (
    HeaderContract,
    parse_genotype,
    parse_genotype_layout,
    parse_header_contract,
)

_CANONICAL_PREFIX = "VCFSVSTATS1_"


@dataclass(frozen=True, slots=True)
class CanonicalWriteResult:
    input_records: int
    input_alleles: int
    output_records: int
    event_identifiers: int
    leading_phase_indicator: bool


class SplitPlan:
    """Disk-backed record, allele, relationship, and event rewrite plan."""

    def __init__(self, database: Path):
        self._database = database
        self._connection = sqlite3.connect(database)
        self._connection.executescript(
            """
            PRAGMA journal_mode=OFF;
            PRAGMA synchronous=FULL;
            CREATE TABLE source_records (
                source_ordinal INTEGER PRIMARY KEY,
                source_id TEXT UNIQUE,
                allele_count INTEGER NOT NULL
            );
            CREATE TABLE outputs (
                source_ordinal INTEGER NOT NULL,
                allele_ordinal INTEGER NOT NULL,
                output_id TEXT NOT NULL UNIQUE,
                PRIMARY KEY (source_ordinal, allele_ordinal)
            );
            CREATE TABLE relationships (
                source_ordinal INTEGER NOT NULL,
                allele_ordinal INTEGER NOT NULL,
                field_name TEXT NOT NULL,
                target_source_id TEXT NOT NULL
            );
            CREATE INDEX relationship_target
                ON relationships(target_source_id, field_name);
            CREATE TABLE events (
                source_event_id TEXT PRIMARY KEY,
                output_event_id TEXT NOT NULL UNIQUE
            );
            """
        )

    def close(self) -> None:
        self._connection.close()

    def add_record(
        self,
        source_ordinal: int,
        source_id: str | None,
        allele_count: int,
        info: dict[str, str | None],
        contract: HeaderContract,
    ) -> None:
        if source_id is not None and source_id.startswith(_CANONICAL_PREFIX):
            raise ValidationFailure("Input record ID collides with the canonical output namespace")
        try:
            self._connection.execute(
                "INSERT INTO source_records VALUES (?, ?, ?)",
                (source_ordinal, source_id, allele_count),
            )
        except sqlite3.IntegrityError as exc:
            raise ValidationFailure(
                "Canonical splitting requires unique non-missing record IDs"
            ) from exc
        for allele_ordinal in range(1, allele_count + 1):
            output_id = f"{_CANONICAL_PREFIX}R{source_ordinal:09d}A{allele_ordinal:04d}"
            self._connection.execute(
                "INSERT INTO outputs VALUES (?, ?, ?)",
                (source_ordinal, allele_ordinal, output_id),
            )
            for field_name in ("MATEID", "PARID"):
                raw = info.get(field_name)
                if raw in {None, ".", ""}:
                    continue
                assert raw is not None
                definition = contract.info.get(field_name)
                values = raw.split(",")
                selected = (
                    values[allele_ordinal - 1]
                    if definition is not None
                    and definition.number == "A"
                    and len(values) == allele_count
                    else values[0]
                    if len(values) == 1
                    else None
                )
                if selected is None:
                    raise ValidationFailure(
                        f"Canonical relationship mapping is ambiguous for {field_name}"
                    )
                if selected != ".":
                    self._connection.execute(
                        "INSERT INTO relationships VALUES (?, ?, ?, ?)",
                        (source_ordinal, allele_ordinal, field_name, selected),
                    )
            raw_event = info.get("EVENT")
            if raw_event not in {None, ".", ""}:
                assert raw_event is not None
                values = raw_event.split(",")
                definition = contract.info.get("EVENT")
                selected_event = (
                    values[allele_ordinal - 1]
                    if definition is not None
                    and definition.number == "A"
                    and len(values) == allele_count
                    else values[0]
                    if len(values) == 1
                    else None
                )
                if selected_event is None:
                    raise ValidationFailure("Canonical EVENT mapping is ambiguous")
                if selected_event != ".":
                    self._connection.execute(
                        "INSERT OR IGNORE INTO events VALUES (?, ?)",
                        (
                            selected_event,
                            f"{_CANONICAL_PREFIX}E{source_ordinal:09d}A{allele_ordinal:04d}",
                        ),
                    )

    def commit(self) -> None:
        self._connection.commit()

    def output_id(self, source_ordinal: int, allele_ordinal: int) -> str:
        row = self._connection.execute(
            "SELECT output_id FROM outputs WHERE source_ordinal=? AND allele_ordinal=?",
            (source_ordinal, allele_ordinal),
        ).fetchone()
        if row is None:
            raise OutputError("Canonical split plan is internally inconsistent")
        return str(row[0])

    def rewrite_relationship(
        self,
        target_source_id: str,
        *,
        current_source_id: str | None,
        field_name: str,
    ) -> str:
        rows = self._connection.execute(
            """
            SELECT outputs.source_ordinal, outputs.allele_ordinal, outputs.output_id
              FROM source_records
              JOIN outputs USING (source_ordinal)
             WHERE source_records.source_id=?
             ORDER BY outputs.allele_ordinal
            """,
            (target_source_id,),
        ).fetchall()
        if not rows:
            raise ValidationFailure(f"Canonical {field_name} target is absent from the split plan")
        if len(rows) == 1:
            return str(rows[0][2])
        if current_source_id is None:
            raise ValidationFailure(f"Canonical {field_name} target is ambiguous")
        reciprocal = self._connection.execute(
            """
            SELECT outputs.output_id
              FROM relationships
              JOIN outputs USING (source_ordinal, allele_ordinal)
             WHERE relationships.target_source_id=?
               AND relationships.field_name=?
               AND relationships.source_ordinal=?
             ORDER BY relationships.allele_ordinal
            """,
            (current_source_id, field_name, int(rows[0][0])),
        ).fetchall()
        if len(reciprocal) != 1:
            raise ValidationFailure(f"Canonical {field_name} target is ambiguous")
        return str(reciprocal[0][0])

    def rewrite_event(self, source_event_id: str) -> str:
        row = self._connection.execute(
            "SELECT output_event_id FROM events WHERE source_event_id=?",
            (source_event_id,),
        ).fetchone()
        if row is None:
            raise OutputError("Canonical event plan is internally inconsistent")
        return str(row[0])

    def event_count(self) -> int:
        row = self._connection.execute("SELECT count(*) FROM events").fetchone()
        return int(row[0])


def _parse_info(raw: str) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    if raw == ".":
        return result
    for item in raw.split(";"):
        key, separator, value = item.partition("=")
        result[key] = value if separator else None
    return result


def _render_info(values: dict[str, str | None]) -> str:
    if not values:
        return "."
    return ";".join(key if value is None else f"{key}={value}" for key, value in values.items())


def _genotypes(allele_count: int, ploidy: int) -> tuple[tuple[int, ...], ...]:
    values = combinations_with_replacement(range(allele_count), ploidy)
    return tuple(sorted(values, key=lambda item: tuple(reversed(item))))


def _project_genotypes(
    raw: str,
    *,
    source_allele_count: int,
    selected_source_allele: int | None,
    ploidy: int,
) -> str:
    if raw in {"", "."}:
        return raw
    values = raw.split(",")
    source = _genotypes(source_allele_count, ploidy)
    if len(values) != len(source):
        raise ValidationFailure("Canonical Number=G/LG value has invalid cardinality")
    retained = (0,) if selected_source_allele is None else (0, selected_source_allele)
    indexes = {genotype: index for index, genotype in enumerate(source)}
    output: list[str] = []
    for local_genotype in _genotypes(len(retained), ploidy):
        source_genotype = tuple(retained[index] for index in local_genotype)
        output.append(values[indexes[source_genotype]])
    return ",".join(output)


def _split_vector(
    raw: str,
    *,
    number: str,
    alternate_index: int,
    alternate_count: int,
    ploidy: int,
) -> str:
    if raw in {"", "."}:
        return raw
    values = raw.split(",")
    if number == "A":
        if len(values) != alternate_count:
            raise ValidationFailure("Canonical Number=A value has invalid cardinality")
        return values[alternate_index]
    if number == "R":
        if len(values) != alternate_count + 1:
            raise ValidationFailure("Canonical Number=R value has invalid cardinality")
        return ",".join((values[0], values[alternate_index + 1]))
    if number == "G":
        return _project_genotypes(
            raw,
            source_allele_count=alternate_count + 1,
            selected_source_allele=alternate_index + 1,
            ploidy=ploidy,
        )
    if number == "P":
        if len(values) != ploidy:
            raise ValidationFailure("Canonical Number=P value has invalid cardinality")
        return raw
    if number in {"LA", "LR", "LG"}:
        raise ValidationFailure("INFO local-allele cardinality cannot be remapped without a sample")
    return raw


def _rewrite_gt(raw: str, selected_allele: int) -> str:
    if raw in {"", "."}:
        return raw
    genotype = parse_genotype_layout(raw)
    if not genotype.alleles:
        raise ValidationFailure("Canonical genotype contains an invalid allele layout")
    rendered = []
    for allele, separator in zip(
        genotype.alleles, genotype.separators, strict=True
    ):
        rendered.append(separator or "")
        rendered.append("." if allele is None else "1" if allele == selected_allele else "0")
    return "".join(rendered)


def _local_values(
    raw: str,
    *,
    number: str,
    source_laa: tuple[int, ...],
    selected_allele: int,
    ploidy: int,
) -> str:
    if raw in {"", "."}:
        return raw
    values = raw.split(",")
    local_position = (
        source_laa.index(selected_allele) + 1 if selected_allele in source_laa else None
    )
    if number == "LA":
        if len(values) != len(source_laa):
            raise ValidationFailure("Canonical Number=LA value has invalid cardinality")
        return "." if local_position is None else values[local_position - 1]
    if number == "LR":
        if len(values) != len(source_laa) + 1:
            raise ValidationFailure("Canonical Number=LR value has invalid cardinality")
        return (
            values[0]
            if local_position is None
            else ",".join((values[0], values[local_position]))
        )
    if number == "LG":
        return _project_genotypes(
            raw,
            source_allele_count=len(source_laa) + 1,
            selected_source_allele=local_position,
            ploidy=ploidy,
        )
    raise OutputError("Unknown local cardinality in canonical split")


def _sample_ploidies(columns: list[str]) -> tuple[int, ...]:
    if len(columns) < 10 or columns[8] in {"", "."}:
        return ()
    keys = columns[8].split(":")
    if "GT" not in keys:
        return ()
    gt_index = keys.index("GT")
    result: list[int] = []
    for sample in columns[9:]:
        values = sample.split(":")
        gt = values[gt_index] if gt_index < len(values) else "."
        parsed = parse_genotype(gt)
        if parsed:
            result.append(len(parsed))
    return tuple(result)


def _rewrite_samples(
    columns: list[str],
    *,
    contract: HeaderContract,
    alternate_index: int,
    alternate_count: int,
) -> None:
    if len(columns) < 10 or columns[8] in {"", "."}:
        return
    keys = columns[8].split(":")
    selected_allele = alternate_index + 1
    for column_index in range(9, len(columns)):
        original = columns[column_index].split(":")
        original.extend("." for _ in range(len(keys) - len(original)))
        by_key = dict(zip(keys, original, strict=True))
        gt = by_key.get("GT", ".")
        ploidy = len(parse_genotype(gt))
        if ploidy < 1:
            ploidy = 2
        raw_laa = by_key.get("LAA", ".")
        try:
            source_laa = (
                ()
                if raw_laa in {"", "."}
                else tuple(int(value) for value in raw_laa.split(","))
            )
        except ValueError as exc:
            raise ValidationFailure("Canonical LAA contains a non-integer allele") from exc
        rewritten: list[str] = []
        for key in keys:
            raw = by_key[key]
            if key == "GT":
                value = _rewrite_gt(raw, selected_allele)
            elif key == "LAA":
                value = "1" if selected_allele in source_laa else "."
            else:
                definition = contract.formats.get(key)
                if definition is None:
                    value = raw
                elif definition.number in {"LA", "LR", "LG"}:
                    value = _local_values(
                        raw,
                        number=definition.number,
                        source_laa=source_laa,
                        selected_allele=selected_allele,
                        ploidy=ploidy,
                    )
                else:
                    value = _split_vector(
                        raw,
                        number=definition.number,
                        alternate_index=alternate_index,
                        alternate_count=alternate_count,
                        ploidy=ploidy,
                    )
            rewritten.append(value)
        columns[column_index] = ":".join(rewritten)


def _rewrite_info(
    columns: list[str],
    *,
    contract: HeaderContract,
    plan: SplitPlan,
    source_ordinal: int,
    source_id: str | None,
    alternate_index: int,
    alternate_count: int,
    ploidy: int,
) -> None:
    values = _parse_info(columns[7])
    for key, raw in tuple(values.items()):
        if raw is None:
            continue
        definition = contract.info.get(key)
        if definition is not None:
            raw = _split_vector(
                raw,
                number=definition.number,
                alternate_index=alternate_index,
                alternate_count=alternate_count,
                ploidy=ploidy,
            )
        if key in {"MATEID", "PARID"} and raw not in {"", "."}:
            raw = plan.rewrite_relationship(
                raw,
                current_source_id=source_id,
                field_name=key,
            )
        elif key == "EVENT" and raw not in {"", "."}:
            raw = plan.rewrite_event(raw)
        elif key == "SVLEN" and raw not in {"", "."}:
            try:
                raw = str(abs(int(raw)))
            except ValueError as exc:
                raise ValidationFailure("Canonical SVLEN is not an integer") from exc
        values[key] = raw

    alt = columns[4]
    symbolic = alt.startswith("<") and alt.endswith(">")
    symbolic_type = alt[1:-1].split(":", 1)[0] if symbolic else None
    breakend = "[" in alt or "]" in alt or alt.startswith(".") or alt.endswith(".")
    if "SVTYPE" in values:
        if breakend:
            values["SVTYPE"] = "BND"
        elif symbolic_type not in {None, "*", "NON_REF"}:
            values["SVTYPE"] = symbolic_type
    if symbolic_type in {"DEL", "DUP"} and values.get("SVCLAIM") in {None, ".", ""}:
        raise ValidationFailure(
            "Canonical VCF 4.5 DEL/DUP rewriting requires an explicit source SVCLAIM"
        )

    if "END" in values:
        end = int(columns[1]) + len(columns[3]) - 1
        raw_svlen = values.get("SVLEN")
        if symbolic_type not in {None, "*", "NON_REF", "BND", "TRA"} and raw_svlen not in {
            None,
            ".",
            "",
        }:
            assert raw_svlen is not None
            end = max(end, int(columns[1]) + abs(int(raw_svlen)))
        if symbolic_type in {"*", "NON_REF"} and len(columns) > 9 and columns[8] != ".":
            keys = columns[8].split(":")
            if "LEN" in keys:
                length_index = keys.index("LEN")
                for sample in columns[9:]:
                    sample_values = sample.split(":")
                    raw_length = (
                        sample_values[length_index] if length_index < len(sample_values) else "."
                    )
                    if raw_length not in {"", "."}:
                        end = max(end, int(columns[1]) + int(raw_length) - 1)
        values["END"] = str(end)
    columns[7] = _render_info(values)


def _header_with_provenance(header_text: str, request_sha256: str) -> str:
    if any(line.startswith(f"##{_CANONICAL_PREFIX}") for line in header_text.splitlines()):
        raise ValidationFailure("Input header already uses the canonical provenance namespace")
    lines = header_text.rstrip("\n").splitlines()
    if not lines or lines[0] != "##fileformat=VCFv4.5":
        raise ValidationFailure("Canonical splitting requires finalized VCF 4.5 input")
    chrom_index = next((index for index, line in enumerate(lines) if line.startswith("#CHROM")), -1)
    if chrom_index < 0:
        raise ValidationFailure("VCF header is missing the column declaration")
    lines[chrom_index:chrom_index] = [
        f"##{_CANONICAL_PREFIX}REQUEST_SHA256={request_sha256}",
        f"##{_CANONICAL_PREFIX}PROFILE=canonical",
    ]
    return "\n".join(lines) + "\n"


def write_canonical_vcf(
    source: Path,
    destination: Path,
    mappings_path: Path,
    *,
    request_sha256: str,
    source_sha256: str,
    temp_dir: Path,
) -> CanonicalWriteResult:
    """Write a plain canonical VCF and streaming mapping JSONL."""
    database = temp_dir / "canonical-plan.sqlite3"
    plan = SplitPlan(database)
    input_records = 0
    input_alleles = 0
    leading_phase_indicator = False
    try:
        with open_variant(source) as variant:
            header_text = str(variant.header)
        contract = parse_header_contract(header_text)
        if not contract.is_v45:
            raise ValidationFailure("Canonical splitting requires finalized VCF 4.5 input")
        for source_ordinal, record_text in enumerate(iter_record_texts(source), start=1):
            input_records += 1
            columns = record_text.split("\t")
            if len(columns) > 9 and columns[8] not in {"", "."}:
                keys = columns[8].split(":")
                if "GT" in keys:
                    gt_index = keys.index("GT")
                    leading_phase_indicator = leading_phase_indicator or any(
                        gt_index < len(sample.split(":"))
                        and sample.split(":")[gt_index].startswith(("|", "/"))
                        for sample in columns[9:]
                    )
            alternate_count = len(columns[4].split(","))
            input_alleles += alternate_count
            source_id = None if columns[2] in {"", "."} else columns[2]
            plan.add_record(
                source_ordinal,
                source_id,
                alternate_count,
                _parse_info(columns[7]),
                contract,
            )
        plan.commit()

        with (
            destination.open("x", encoding="utf-8", newline="\n") as output,
            mappings_path.open("x", encoding="utf-8", newline="\n") as mappings,
        ):
            output.write(_header_with_provenance(header_text, request_sha256))
            output_ordinal = 0
            for source_ordinal, record_text in enumerate(iter_record_texts(source), start=1):
                original = record_text.split("\t")
                alts = original[4].split(",")
                source_id = None if original[2] in {"", "."} else original[2]
                ploidies = _sample_ploidies(original)
                ploidy = ploidies[0] if ploidies else 2
                if len(set(ploidies)) > 1 and any(
                    field.number in {"G", "P"} for field in contract.info.values()
                ):
                    raise ValidationFailure(
                        "INFO Number=G/P cannot be remapped across differing sample ploidies"
                    )
                for alternate_index, alt in enumerate(alts):
                    output_ordinal += 1
                    columns = list(original)
                    columns[2] = plan.output_id(source_ordinal, alternate_index + 1)
                    columns[4] = alt
                    _rewrite_samples(
                        columns,
                        contract=contract,
                        alternate_index=alternate_index,
                        alternate_count=len(alts),
                    )
                    _rewrite_info(
                        columns,
                        contract=contract,
                        plan=plan,
                        source_ordinal=source_ordinal,
                        source_id=source_id,
                        alternate_index=alternate_index,
                        alternate_count=len(alts),
                        ploidy=ploidy,
                    )
                    output.write("\t".join(columns) + "\n")
                    mapping = {
                        "source_record_key": (
                            f"source:{source_sha256[:16]}:{source_ordinal}:{alternate_index + 1}"
                        ),
                        "source_ordinal": source_ordinal,
                        "source_id": source_id,
                        "source_allele_ordinal": alternate_index + 1,
                        "output_id": columns[2],
                        "output_ordinal": output_ordinal,
                        "transform_codes": [
                            "split_multiallelic" if len(alts) > 1 else "canonical_identity",
                            "rewrite_record_id",
                            "remap_declared_cardinality",
                            "remap_relationship_identifiers",
                        ],
                    }
                    mappings.write(json.dumps(mapping, sort_keys=True) + "\n")
            output.flush()
            os.fsync(output.fileno())
            mappings.flush()
            os.fsync(mappings.fileno())
        return CanonicalWriteResult(
            input_records=input_records,
            input_alleles=input_alleles,
            output_records=input_alleles,
            event_identifiers=plan.event_count(),
            leading_phase_indicator=leading_phase_indicator,
        )
    finally:
        plan.close()


__all__ = ["CanonicalWriteResult", "write_canonical_vcf"]
