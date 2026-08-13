"""Finalized VCF 4.5 header, cardinality, phasing, and SV validation.

The bundled native parser deliberately remains the container/parser boundary.
This module owns the specification layer that native libraries predating all
VCF 4.5 cardinality symbols cannot expose through their typed metadata API.
"""

from __future__ import annotations

import math
import re
import sqlite3
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from itertools import combinations_with_replacement
from pathlib import Path
from typing import Any

from .models import Diagnostic, Fixability, Severity

_DEFINITION_RE = re.compile(r"^##(INFO|FORMAT)=<(.*)>$")
_VERSION_RE = re.compile(r"^VCFv(?P<major>[0-9]+)\.(?P<minor>[0-9]+)$")
_GT_SEPARATOR_RE = re.compile(r"([/|])")


@dataclass(frozen=True, slots=True)
class HeaderField:
    kind: str
    identifier: str
    number: str
    value_type: str


@dataclass(frozen=True, slots=True)
class HeaderContract:
    version: str
    info: dict[str, HeaderField]
    formats: dict[str, HeaderField]

    @property
    def is_v45(self) -> bool:
        return self.version == "VCFv4.5"


@dataclass(frozen=True, slots=True)
class GenotypeLayout:
    alleles: tuple[int | None, ...]
    separators: tuple[str | None, ...]


def parse_genotype_layout(raw: str | None) -> GenotypeLayout:
    """Parse VCF 4.5 GT, including its optional leading phase indicator."""
    if raw is None or raw == "":
        return GenotypeLayout((), ())
    prefix: str | None = raw[0] if raw[0] in "/|" else None
    body = raw[1:] if prefix is not None else raw
    if body == "":
        return GenotypeLayout((), ())
    pieces = _GT_SEPARATOR_RE.split(body)
    if not pieces or any(piece == "" for piece in pieces[::2]):
        return GenotypeLayout((), ())
    if any(separator not in {"/", "|"} for separator in pieces[1::2]):
        return GenotypeLayout((), ())
    alleles: list[int | None] = []
    for value in pieces[::2]:
        if value == ".":
            alleles.append(None)
            continue
        try:
            allele = int(value)
        except ValueError:
            return GenotypeLayout((), ())
        if allele < 0:
            return GenotypeLayout((), ())
        alleles.append(allele)
    separators: list[str | None] = [prefix]
    separators.extend(pieces[1::2])
    if len(separators) != len(alleles):
        return GenotypeLayout((), ())
    return GenotypeLayout(tuple(alleles), tuple(separators))


def _split_structured(value: str) -> tuple[str, ...]:
    parts: list[str] = []
    start = 0
    quoted = False
    escaped = False
    for index, character in enumerate(value):
        if escaped:
            escaped = False
        elif character == "\\" and quoted:
            escaped = True
        elif character == '"':
            quoted = not quoted
        elif character == "," and not quoted:
            parts.append(value[start:index])
            start = index + 1
    parts.append(value[start:])
    return tuple(parts)


def parse_header_contract(header_text: str) -> HeaderContract:
    """Parse the declarations needed for rules native metadata may not expose."""
    version = ""
    info: dict[str, HeaderField] = {}
    formats: dict[str, HeaderField] = {}
    for line in header_text.splitlines():
        if line.startswith("##fileformat="):
            version = line.partition("=")[2].strip()
            continue
        match = _DEFINITION_RE.match(line)
        if match is None:
            continue
        attributes: dict[str, str] = {}
        for item in _split_structured(match.group(2)):
            key, separator, value = item.partition("=")
            if separator:
                attributes[key.strip()] = value.strip().strip('"')
        identifier = attributes.get("ID")
        number = attributes.get("Number")
        value_type = attributes.get("Type")
        if identifier is None or number is None or value_type is None:
            continue
        definition = HeaderField(match.group(1), identifier, number, value_type)
        (info if definition.kind == "INFO" else formats)[identifier] = definition
    return HeaderContract(version, info, formats)


def _diagnostic(
    code: str,
    message: str,
    *,
    field_name: str | None = None,
    record_ordinal: int | None = None,
    chrom: str | None = None,
    pos: int | None = None,
    severity: Severity = Severity.ERROR,
    blocks_normalization: bool = True,
    adapter_id: str | None = None,
) -> Diagnostic:
    return Diagnostic(
        code,
        severity,
        "vcf_conformance",
        message,
        record_ordinal,
        chrom,
        pos,
        field_name,
        "VCF 4.5",
        Fixability.REQUIRES_ADAPTER,
        blocks_normalization=blocks_normalization,
        adapter_id=adapter_id,
    )


def validate_header_contract(
    contract: HeaderContract,
    *,
    adapter_id: str | None,
) -> tuple[Diagnostic, ...]:
    diagnostics: list[Diagnostic] = []
    version_match = _VERSION_RE.match(contract.version)
    if version_match is None:
        diagnostics.append(
            _diagnostic(
                "VSS-VCF-VERSION-UNSUPPORTED-FINAL-OR-DRAFT",
                "The declared VCF version is not a supported finalized version",
                field_name="fileformat",
                adapter_id=adapter_id,
            )
        )
        return tuple(diagnostics)
    version = (int(version_match.group("major")), int(version_match.group("minor")))
    if version[0] != 4 or version[1] > 5:
        diagnostics.append(
            _diagnostic(
                "VSS-VCF-VERSION-UNSUPPORTED-FINAL-OR-DRAFT",
                "The declared VCF version is newer than the supported finalized VCF 4.5 contract",
                field_name="fileformat",
                adapter_id=adapter_id,
            )
        )
        return tuple(diagnostics)
    if not contract.is_v45:
        return ()

    expectations: dict[tuple[str, str], tuple[str, str]] = {
        ("INFO", "END"): ("1", "Integer"),
        ("INFO", "SVTYPE"): ("1", "String"),
        ("INFO", "SVLEN"): ("A", "Integer"),
        ("INFO", "MATEID"): ("A", "String"),
        ("INFO", "PARID"): ("A", "String"),
        ("INFO", "EVENT"): ("A", "String"),
        ("INFO", "EVENTTYPE"): ("A", "String"),
        ("INFO", "SVCLAIM"): ("A", "String"),
        ("FORMAT", "LEN"): ("1", "Integer"),
        ("FORMAT", "LAA"): (".", "Integer"),
        ("FORMAT", "LAD"): ("LR", "Integer"),
        ("FORMAT", "LADF"): ("LR", "Integer"),
        ("FORMAT", "LADR"): ("LR", "Integer"),
        ("FORMAT", "LEC"): ("LA", "Integer"),
        ("FORMAT", "LGL"): ("LG", "Float"),
        ("FORMAT", "LGP"): ("LG", "Float"),
        ("FORMAT", "LPL"): ("LG", "Integer"),
        ("FORMAT", "LPP"): ("LG", "Integer"),
        ("FORMAT", "PSL"): ("P", "String"),
        ("FORMAT", "PSO"): ("P", "Integer"),
        ("FORMAT", "PSQ"): ("P", "Integer"),
    }
    for (kind, identifier), (number, value_type) in expectations.items():
        collection = contract.info if kind == "INFO" else contract.formats
        definition = collection.get(identifier)
        if definition is None:
            continue
        if definition.number != number or definition.value_type != value_type:
            diagnostics.append(
                _diagnostic(
                    "VSS-HEADER-RESERVED-DECLARATION",
                    f"Reserved {kind} field {identifier} must declare "
                    f"Number={number}, Type={value_type}",
                    field_name=identifier,
                    adapter_id=adapter_id,
                )
            )
    return tuple(diagnostics)


def _values(raw: str | None) -> tuple[str, ...] | None:
    if raw is None or raw in {"", "."}:
        return None
    return tuple(raw.split(","))


def _symbolic_base(alt: str) -> str | None:
    if not (alt.startswith("<") and alt.endswith(">")):
        return None
    return alt[1:-1].split(":", 1)[0]


def _is_breakpoint(alt: str) -> bool:
    return "[" in alt or "]" in alt or alt.startswith(".") or alt.endswith(".")


def _selected_values(
    values: tuple[str, ...],
    indexes: tuple[int, ...],
    *,
    include_reference: bool,
) -> tuple[str, ...]:
    offset = 1 if include_reference else 0
    selected = ([values[0]] if include_reference else []) + [
        values[index - 1 + offset] for index in indexes
    ]
    return tuple(selected)


_LOCAL_EQUIVALENTS = {
    "LAD": ("AD", "LR"),
    "LADF": ("ADF", "LR"),
    "LADR": ("ADR", "LR"),
    "LEC": ("EC", "LA"),
    "LGL": ("GL", "LG"),
    "LGP": ("GP", "LG"),
    "LPL": ("PL", "LG"),
    "LPP": ("PP", "LG"),
}


def _local_equivalent_matches(
    sample: dict[str, str],
    *,
    local_name: str,
    local_number: str,
    local_alleles: tuple[int, ...],
    alternate_count: int,
    ploidy: int,
) -> bool:
    standard_name = _LOCAL_EQUIVALENTS[local_name][0]
    local_values = _values(sample.get(local_name))
    standard_values = _values(sample.get(standard_name))
    if local_values is None or standard_values is None:
        return True
    if local_number == "LA":
        if len(standard_values) != alternate_count:
            return False
        selected = _selected_values(standard_values, local_alleles, include_reference=False)
    elif local_number == "LR":
        if len(standard_values) != alternate_count + 1:
            return False
        selected = _selected_values(standard_values, local_alleles, include_reference=True)
    else:
        standard_genotypes = tuple(
            sorted(
                combinations_with_replacement(range(alternate_count + 1), ploidy),
                key=lambda item: tuple(reversed(item)),
            )
        )
        local_genotypes = tuple(
            sorted(
                combinations_with_replacement(range(len(local_alleles) + 1), ploidy),
                key=lambda item: tuple(reversed(item)),
            )
        )
        if len(standard_values) != len(standard_genotypes):
            return False
        indexes = {genotype: index for index, genotype in enumerate(standard_genotypes)}
        translated = tuple(
            tuple(0 if value == 0 else local_alleles[value - 1] for value in genotype)
            for genotype in local_genotypes
        )
        selected = tuple(standard_values[indexes[genotype]] for genotype in translated)
    return len(local_values) == len(selected) and all(
        left == right or left == "." or right == "."
        for left, right in zip(local_values, selected, strict=True)
    )


class PhaseEvidenceStore:
    """Disk-backed VCF 4.5 phase-set checks that require callset context."""

    def __init__(
        self,
        temp_dir: str | Path | None = None,
        *,
        adapter_id: str | None,
    ) -> None:
        with tempfile.NamedTemporaryFile(
            prefix="vcf-sv-stats.phase.", suffix=".sqlite3", dir=temp_dir, delete=False
        ) as handle:
            self.path = Path(handle.name)
        self.adapter_id = adapter_id
        self.connection = sqlite3.connect(self.path)
        self.connection.executescript(
            """
            PRAGMA journal_mode=OFF;
            PRAGMA synchronous=OFF;
            CREATE TABLE phases (
                sample_ordinal INTEGER NOT NULL,
                phase_set TEXT NOT NULL,
                source_ordinal INTEGER NOT NULL,
                allele_position INTEGER NOT NULL,
                pso TEXT,
                requires_pso INTEGER NOT NULL,
                chrom TEXT,
                pos INTEGER
            );
            CREATE INDEX phases_name ON phases(sample_ordinal, phase_set);
            CREATE TABLE breakpoints (
                source_ordinal INTEGER NOT NULL,
                sample_ordinal INTEGER NOT NULL,
                record_id TEXT,
                mate_id TEXT NOT NULL,
                psl TEXT NOT NULL,
                pso TEXT NOT NULL,
                chrom TEXT,
                pos INTEGER
            );
            CREATE INDEX breakpoints_id ON breakpoints(record_id, sample_ordinal);
            """
        )

    def add(self, record_text: str, *, ordinal: int) -> None:
        columns = record_text.rstrip("\n").split("\t")
        if len(columns) < 10 or columns[8] in {"", "."}:
            return
        format_keys = tuple(columns[8].split(":"))
        if "PSL" not in format_keys:
            return
        alts = tuple(columns[4].split(",")) if columns[4] not in {"", "."} else ()
        requires_pso = any(
            (_symbolic_base(alt) not in {None, "*", "NON_REF"}) or _is_breakpoint(alt)
            for alt in alts
        )
        breakpoint = any(_is_breakpoint(alt) for alt in alts)
        info = _parse_info(columns[7])
        mate_ids = tuple(
            item
            for field_name in ("MATEID", "PARID")
            for item in (info.get(field_name) or "").split(",")
            if item not in {"", "."}
        )
        context = _record_context(columns, ordinal)
        for sample_ordinal, sample_text in enumerate(columns[9:], start=1):
            sample_columns = sample_text.split(":")
            sample = {
                key: sample_columns[index] if index < len(sample_columns) else "."
                for index, key in enumerate(format_keys)
            }
            psl = _values(sample.get("PSL"))
            if psl is None:
                continue
            pso = _values(sample.get("PSO"))
            for allele_position, phase_set in enumerate(psl, start=1):
                if phase_set == ".":
                    continue
                ordinal_value = (
                    None
                    if pso is None or allele_position > len(pso)
                    else pso[allele_position - 1]
                )
                self.connection.execute(
                    "INSERT INTO phases VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        sample_ordinal,
                        phase_set,
                        ordinal,
                        allele_position,
                        ordinal_value,
                        int(requires_pso),
                        context["chrom"],
                        context["pos"],
                    ),
                )
            if breakpoint and mate_ids:
                rendered_psl = ",".join(psl)
                rendered_pso = "." if pso is None else ",".join(pso)
                for mate_id in mate_ids:
                    self.connection.execute(
                        "INSERT INTO breakpoints VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            ordinal,
                            sample_ordinal,
                            None if columns[2] in {"", "."} else columns[2],
                            mate_id,
                            rendered_psl,
                            rendered_pso,
                            context["chrom"],
                            context["pos"],
                        ),
                    )

    def diagnostics(self) -> tuple[Diagnostic, ...]:
        self.connection.commit()
        diagnostics: list[Diagnostic] = []
        missing_rows = self.connection.execute(
            """
            SELECT DISTINCT p.source_ordinal, p.chrom, p.pos
              FROM phases p
             WHERE (p.pso IS NULL OR p.pso = '.')
               AND EXISTS (
                   SELECT 1 FROM phases required
                    WHERE required.sample_ordinal = p.sample_ordinal
                      AND required.phase_set = p.phase_set
                      AND required.requires_pso = 1
               )
             ORDER BY p.source_ordinal
            """
        ).fetchall()
        for source_ordinal, chrom, pos in missing_rows:
            diagnostics.append(
                _diagnostic(
                    "VSS-PHASE-PSO-REQUIRED",
                    "PSO is required to preserve traversal for an SV-associated phase set",
                    field_name="PSO",
                    record_ordinal=int(source_ordinal),
                    chrom=None if chrom is None else str(chrom),
                    pos=None if pos is None else int(pos),
                    severity=Severity.WARNING,
                    blocks_normalization=True,
                    adapter_id=self.adapter_id,
                )
            )
        mismatch_rows = self.connection.execute(
            """
            SELECT DISTINCT a.source_ordinal, a.chrom, a.pos
              FROM breakpoints a
              JOIN breakpoints b
                ON b.record_id = a.mate_id
               AND b.sample_ordinal = a.sample_ordinal
               AND a.source_ordinal < b.source_ordinal
             WHERE a.psl != b.psl OR a.pso != b.pso
             ORDER BY a.source_ordinal
            """
        ).fetchall()
        for source_ordinal, chrom, pos in mismatch_rows:
            diagnostics.append(
                _diagnostic(
                    "VSS-PHASE-BREAKPOINT-MISMATCH",
                    "Reciprocal breakpoint records must have identical PSL and PSO values",
                    field_name="PSL",
                    record_ordinal=int(source_ordinal),
                    chrom=None if chrom is None else str(chrom),
                    pos=None if pos is None else int(pos),
                    adapter_id=self.adapter_id,
                )
            )
        return tuple(diagnostics)

    def close(self) -> None:
        self.connection.close()
        self.path.unlink(missing_ok=True)

    def __enter__(self) -> PhaseEvidenceStore:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def parse_genotype(raw: str | None) -> tuple[int | None, ...]:
    return parse_genotype_layout(raw).alleles


def genotype_cardinality(allele_count: int, ploidy: int) -> int:
    if allele_count < 1 or ploidy < 1:
        return 0
    return math.comb(allele_count + ploidy - 1, ploidy)


def expected_cardinality(
    number: str,
    *,
    alternate_count: int,
    ploidy: int,
    local_alternate_count: int,
) -> int | None:
    if number == ".":
        return None
    if number == "A":
        return alternate_count
    if number == "R":
        return alternate_count + 1
    if number == "G":
        return genotype_cardinality(alternate_count + 1, ploidy)
    if number == "P":
        return ploidy
    if number == "LA":
        return local_alternate_count
    if number == "LR":
        return local_alternate_count + 1
    if number == "LG":
        return genotype_cardinality(local_alternate_count + 1, ploidy)
    try:
        return int(number)
    except ValueError:
        return None


def _parse_info(raw: str) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    if raw == ".":
        return result
    for item in raw.split(";"):
        key, separator, value = item.partition("=")
        result[key] = value if separator else None
    return result


def _record_context(columns: list[str], ordinal: int) -> dict[str, Any]:
    try:
        pos = int(columns[1])
    except (IndexError, ValueError):
        pos = None
    return {
        "record_ordinal": ordinal,
        "chrom": columns[0] if columns else None,
        "pos": pos,
    }


def _append_cardinality_diagnostic(
    diagnostics: list[Diagnostic],
    *,
    kind: str,
    field_name: str,
    observed: int,
    expected: int,
    context: dict[str, Any],
    adapter_id: str | None,
) -> None:
    diagnostics.append(
        _diagnostic(
            f"VSS-CARDINALITY-{kind}",
            f"{kind} field cardinality is {observed}; expected {expected}",
            field_name=field_name,
            adapter_id=adapter_id,
            **context,
        )
    )


def validate_record_text(
    record_text: str,
    *,
    ordinal: int,
    contract: HeaderContract,
    adapter_id: str | None,
) -> tuple[Diagnostic, ...]:
    """Validate record constructs whose exact rules depend on VCF 4.5."""
    if not contract.is_v45:
        return ()
    columns = record_text.rstrip("\n").split("\t")
    if len(columns) < 8:
        return ()
    context = _record_context(columns, ordinal)
    diagnostics: list[Diagnostic] = []
    alts = tuple(columns[4].split(",")) if columns[4] not in {"", "."} else ()
    alternate_count = len(alts)
    info = _parse_info(columns[7])
    format_keys = tuple(columns[8].split(":")) if len(columns) > 8 and columns[8] != "." else ()
    sample_values: list[dict[str, str]] = []
    sample_ploidies: list[int] = []
    for sample_text in columns[9:]:
        sample_columns = sample_text.split(":")
        sample = {
            key: sample_columns[index] if index < len(sample_columns) else "."
            for index, key in enumerate(format_keys)
        }
        sample_values.append(sample)
        genotype = parse_genotype_layout(sample.get("GT"))
        if genotype.alleles:
            sample_ploidies.append(len(genotype.alleles))
    info_ploidy = sample_ploidies[0] if sample_ploidies and len(set(sample_ploidies)) == 1 else 2

    for field_name, raw in info.items():
        definition = contract.info.get(field_name)
        info_values = _values(raw)
        if definition is None or info_values is None:
            continue
        expected = expected_cardinality(
            definition.number,
            alternate_count=alternate_count,
            ploidy=info_ploidy,
            local_alternate_count=0,
        )
        if expected is not None and len(info_values) != expected:
            _append_cardinality_diagnostic(
                diagnostics,
                kind="INFO",
                field_name=field_name,
                observed=len(info_values),
                expected=expected,
                context=context,
                adapter_id=adapter_id,
            )

    local_numbers = {"LA", "LR", "LG"}
    for sample in sample_values:
        genotype = parse_genotype_layout(sample.get("GT"))
        gt = genotype.alleles
        ploidy = len(gt) or 2
        laa_values = _values(sample.get("LAA"))
        local_alleles: tuple[int, ...] = ()
        if laa_values is not None:
            try:
                local_alleles = tuple(int(value) for value in laa_values)
            except ValueError:
                diagnostics.append(
                    _diagnostic(
                        "VSS-LOCAL-ALLELE-INVALID",
                        "FORMAT LAA must contain distinct 1-based ALT indexes",
                        field_name="LAA",
                        adapter_id=adapter_id,
                        **context,
                    )
                )
            if (
                len(set(local_alleles)) != len(local_alleles)
                or any(value < 1 or value > alternate_count for value in local_alleles)
            ):
                diagnostics.append(
                    _diagnostic(
                        "VSS-LOCAL-ALLELE-INVALID",
                        "FORMAT LAA must contain distinct 1-based ALT indexes",
                        field_name="LAA",
                        adapter_id=adapter_id,
                        **context,
                    )
                )
        used_local_fields = [
            field_name
            for field_name in format_keys
            if contract.formats.get(field_name) is not None
            and contract.formats[field_name].number in local_numbers
            and _values(sample.get(field_name)) is not None
        ]
        if used_local_fields and "LAA" not in format_keys:
            diagnostics.append(
                _diagnostic(
                    "VSS-LOCAL-ALLELE-LAA-REQUIRED",
                    "FORMAT LAA is required when a local-allele field has a value",
                    field_name=used_local_fields[0],
                    adapter_id=adapter_id,
                    **context,
                )
            )
        if used_local_fields and "LAA" in format_keys:
            laa_index = format_keys.index("LAA")
            if any(format_keys.index(field_name) < laa_index for field_name in used_local_fields):
                diagnostics.append(
                    _diagnostic(
                        "VSS-LOCAL-ALLELE-ORDER",
                        "FORMAT LAA must precede every local-allele field other than GT",
                        field_name="LAA",
                        adapter_id=adapter_id,
                        **context,
                    )
                )
        if used_local_fields and any(
            allele not in {None, 0} and allele not in local_alleles for allele in gt
        ):
            diagnostics.append(
                _diagnostic(
                    "VSS-LOCAL-ALLELE-GT-CONFLICT",
                    "Every called ALT allele must be present in LAA when local fields are used",
                    field_name="LAA",
                    adapter_id=adapter_id,
                    **context,
                )
            )
        if _values(sample.get("PS")) is not None and _values(sample.get("PSL")) is not None:
            diagnostics.append(
                _diagnostic(
                    "VSS-PHASE-PS-PSL-CONFLICT",
                    "A sample genotype cannot define both PS and PSL",
                    field_name="PSL",
                    adapter_id=adapter_id,
                    **context,
                )
            )
        psl_values = _values(sample.get("PSL"))
        pso_values = _values(sample.get("PSO"))
        psq_values = _values(sample.get("PSQ"))
        if psl_values is not None and len(psl_values) == len(genotype.separators):
            for index, (phase_set, separator) in enumerate(
                zip(psl_values, genotype.separators, strict=True)
            ):
                if separator != "|" and phase_set != ".":
                    diagnostics.append(
                        _diagnostic(
                            "VSS-PHASE-PSL-UNPHASED",
                            "An allele without a preceding phase separator must have missing PSL",
                            field_name="PSL",
                            adapter_id=adapter_id,
                            **context,
                        )
                    )
                if phase_set == ".":
                    if (
                        pso_values is not None
                        and index < len(pso_values)
                        and pso_values[index] != "."
                    ):
                        diagnostics.append(
                            _diagnostic(
                                "VSS-PHASE-PSO-WITHOUT-PSL",
                                "PSO must be missing when the corresponding PSL is missing",
                                field_name="PSO",
                                adapter_id=adapter_id,
                                **context,
                            )
                        )
                    if (
                        psq_values is not None
                        and index < len(psq_values)
                        and psq_values[index] != "."
                    ):
                        diagnostics.append(
                            _diagnostic(
                                "VSS-PHASE-PSQ-WITHOUT-PSL",
                                "PSQ must be missing when the corresponding PSL is missing",
                                field_name="PSQ",
                                adapter_id=adapter_id,
                                **context,
                            )
                        )
        for field_name in format_keys:
            definition = contract.formats.get(field_name)
            field_values = _values(sample.get(field_name))
            if definition is None or field_values is None:
                continue
            expected = expected_cardinality(
                definition.number,
                alternate_count=alternate_count,
                ploidy=ploidy,
                local_alternate_count=len(local_alleles),
            )
            if expected is not None and len(field_values) != expected:
                _append_cardinality_diagnostic(
                    diagnostics,
                    kind="FORMAT",
                    field_name=field_name,
                    observed=len(field_values),
                    expected=expected,
                    context=context,
                    adapter_id=adapter_id,
                )
        for local_name, (standard_name, local_number) in _LOCAL_EQUIVALENTS.items():
            if local_name not in format_keys or standard_name not in format_keys:
                continue
            if not _local_equivalent_matches(
                sample,
                local_name=local_name,
                local_number=local_number,
                local_alleles=local_alleles,
                alternate_count=alternate_count,
                ploidy=ploidy,
            ):
                diagnostics.append(
                    _diagnostic(
                        "VSS-LOCAL-ALLELE-EQUIVALENCE",
                        "Local and full-allele FORMAT fields encode conflicting values",
                        field_name=local_name,
                        adapter_id=adapter_id,
                        **context,
                    )
                )

    svlen_values = _values(info.get("SVLEN"))
    svclaim_values = _values(info.get("SVCLAIM"))
    event_values = _values(info.get("EVENT"))
    event_type_values = _values(info.get("EVENTTYPE"))
    end_values = _values(info.get("END"))
    computed_ends: list[int] = [int(columns[1]) + max(1, len(columns[3])) - 1]
    observed_end: int | None = None
    if end_values is not None and len(end_values) == 1 and end_values[0] != ".":
        with suppress(ValueError):
            observed_end = int(end_values[0])
    for allele_index, alt in enumerate(alts):
        symbolic = alt.startswith("<") and alt.endswith(">")
        symbolic_type = _symbolic_base(alt)
        is_breakend = _is_breakpoint(alt)
        is_reference_block = symbolic_type in {"*", "NON_REF"}
        if symbolic_type in {"BND", "TRA"}:
            diagnostics.append(
                _diagnostic(
                    "VSS-V45-SYMBOLIC-BND-DISALLOWED",
                    "VCF 4.5 requires breakpoint notation instead of symbolic BND or TRA ALT",
                    field_name="ALT",
                    adapter_id=adapter_id,
                    **context,
                )
            )
        if symbolic_type is not None and symbolic_type.upper() in {
            "DEL",
            "DUP",
            "INS",
            "INV",
            "CNV",
            "BND",
            "TRA",
            "NON_REF",
        } and symbolic_type != symbolic_type.upper():
            diagnostics.append(
                _diagnostic(
                    "VSS-V45-SYMBOLIC-ALT-CASE",
                    "Reserved symbolic ALT identifiers are case-sensitive",
                    field_name="ALT",
                    adapter_id=adapter_id,
                    **context,
                )
            )
        allele_type = symbolic_type
        if is_breakend:
            allele_type = "BND"
        elif not symbolic:
            length_delta = len(alt) - len(columns[3])
            if abs(length_delta) >= 50:
                allele_type = "INS" if length_delta > 0 else "DEL"
        raw_length = (
            svlen_values[allele_index]
            if svlen_values is not None and allele_index < len(svlen_values)
            else None
        )
        length: int | None = None
        if raw_length not in {None, "."}:
            assert raw_length is not None
            with suppress(ValueError):
                length = int(raw_length)
        if length is not None and (
            is_breakend or is_reference_block or not symbolic
        ):
            diagnostics.append(
                _diagnostic(
                    "VSS-V45-SVLEN-NOT-APPLICABLE",
                    "SVLEN must be missing for non-symbolic, breakpoint, and "
                    "reference-block ALT alleles",
                    field_name="SVLEN",
                    adapter_id=adapter_id,
                    **context,
                )
            )
        if symbolic and not is_reference_block and symbolic_type not in {"BND", "TRA"}:
            if length is None:
                if observed_end is None:
                    diagnostics.append(
                        _diagnostic(
                            "VSS-V45-SVLEN-REQUIRED",
                            "Every symbolic structural ALT requires SVLEN or a legacy END fallback",
                            field_name="SVLEN",
                            adapter_id=adapter_id,
                            **context,
                        )
                    )
                else:
                    computed_ends.append(observed_end)
            else:
                if length < 0:
                    diagnostics.append(
                        _diagnostic(
                            "VSS-V45-SVLEN-LEGACY-SIGN",
                            "Negative SVLEN is a legacy convention interpreted by absolute value",
                            field_name="SVLEN",
                            severity=Severity.WARNING,
                            blocks_normalization=False,
                            adapter_id=adapter_id,
                            **context,
                        )
                    )
                # POS is the base immediately preceding a symbolic SV.  A
                # length of N therefore ends at POS + N (unlike REF or LEN,
                # whose first covered base is POS itself).
                computed_ends.append(int(columns[1]) + abs(length))
        claim = (
            svclaim_values[allele_index]
            if svclaim_values is not None and allele_index < len(svclaim_values)
            else None
        )
        allowed_claims = (
            {"D", "J", "DJ"}
            if allele_type in {"DEL", "DUP"}
            else {"D", "."}
            if allele_type == "CNV"
            else {"J", "DJ", "."}
            if allele_type in {"INV", "INS"}
            else {"J", "."}
            if is_breakend
            else {"."}
        )
        if symbolic_type in {"DEL", "DUP"} and claim is None:
            diagnostics.append(
                _diagnostic(
                    "VSS-V45-SVCLAIM-REQUIRED",
                    "DEL and DUP symbolic alleles require an allele-specific SVCLAIM",
                    field_name="SVCLAIM",
                    adapter_id=adapter_id,
                    **context,
                )
            )
        elif claim is not None and claim not in allowed_claims:
            diagnostics.append(
                _diagnostic(
                    "VSS-V45-SVCLAIM-INVALID",
                    "SVCLAIM is incompatible with the ALT allele semantics",
                    field_name="SVCLAIM",
                    adapter_id=adapter_id,
                    **context,
                )
            )

    if event_type_values is not None:
        for index, event_type in enumerate(event_type_values):
            event = (
                None
                if event_values is None or index >= len(event_values)
                else event_values[index]
            )
            if event_type != "." and event in {None, "."}:
                diagnostics.append(
                    _diagnostic(
                        "VSS-V45-EVENTTYPE-WITHOUT-EVENT",
                        "EVENTTYPE requires an allele-specific EVENT identifier",
                        field_name="EVENTTYPE",
                        adapter_id=adapter_id,
                        **context,
                    )
                )
    declared_type = _values(info.get("SVTYPE"))
    if declared_type is not None:
        inferred_types: set[str] = set()
        for alt in alts:
            if "[" in alt or "]" in alt or alt.startswith(".") or alt.endswith("."):
                inferred_types.add("BND")
            elif alt.startswith("<") and alt.endswith(">"):
                symbolic_name = alt[1:-1].split(":", 1)[0]
                if symbolic_name not in {"*", "NON_REF"}:
                    inferred_types.add(symbolic_name)
        if inferred_types and (
            len(inferred_types) != 1 or declared_type[0] not in inferred_types
        ):
            diagnostics.append(
                _diagnostic(
                    "VSS-V45-SVTYPE-CONFLICT",
                    "Deprecated SVTYPE does not unambiguously agree with every ALT allele",
                    field_name="SVTYPE",
                    adapter_id=adapter_id,
                    **context,
                )
            )

    reference_indexes = tuple(
        index for index, alt in enumerate(alts, start=1) if alt in {"<*>", "<NON_REF>"}
    )
    reference_block = bool(reference_indexes)
    if not reference_block:
        for sample in sample_values:
            if _values(sample.get("LEN")) is not None:
                diagnostics.append(
                    _diagnostic(
                        "VSS-V45-LEN-WITHOUT-REFERENCE-BLOCK",
                        "FORMAT LEN is defined only for <*> or <NON_REF> reference blocks",
                        field_name="LEN",
                        adapter_id=adapter_id,
                        **context,
                    )
                )
    if reference_block:
        for sample in sample_values:
            raw_length = sample.get("LEN")
            if raw_length not in {None, "."}:
                assert raw_length is not None
                try:
                    length = int(raw_length)
                except ValueError:
                    length = 0
                if length < 1:
                    diagnostics.append(
                        _diagnostic(
                            "VSS-V45-REFERENCE-BLOCK-LEN",
                            "FORMAT LEN must be a positive reference-block length",
                            field_name="LEN",
                            adapter_id=adapter_id,
                            **context,
                        )
                    )
                else:
                    computed_ends.append(int(columns[1]) + length - 1)
            laa = _values(sample.get("LAA"))
            defines_block = raw_length not in {None, "."} or observed_end is not None
            if (
                defines_block
                and "LAA" in format_keys
                and (
                    laa is None
                    or not any(
                        value.isdigit() and int(value) in reference_indexes for value in laa
                    )
                )
            ):
                diagnostics.append(
                    _diagnostic(
                        "VSS-V45-REFERENCE-BLOCK-LAA",
                        "A reference-block start with LAA must include the unspecified allele",
                        field_name="LAA",
                        adapter_id=adapter_id,
                        **context,
                    )
                )
    if observed_end is not None:
        expected_end = max(computed_ends)
        if observed_end != expected_end:
            diagnostics.append(
                _diagnostic(
                    "VSS-V45-END-COMPUTED-MISMATCH",
                    f"Deprecated END is {observed_end}; computed value is {expected_end}",
                    field_name="END",
                    adapter_id=adapter_id,
                    **context,
                )
            )
    return tuple(diagnostics)
