"""Stable diagnostic catalog."""

from __future__ import annotations

from typing import Any

from .exceptions import UsageError

CATALOG: dict[str, dict[str, Any]] = {
    "VSS-BND-ALT-TYPE-CONFLICT": {
        "meaning": "A bracket breakend ALT conflicts with the record's declared type.",
        "default_severity": "error",
        "category": "breakend",
        "blocks_normalization": True,
        "fixability": "requires_adapter",
        "specification": "VCF 4.5 breakend alleles",
    },
    "VSS-BND-MATE-UNRESOLVED": {
        "meaning": "MATEID names a record identifier that is absent from the callset.",
        "default_severity": "error",
        "category": "event_graph",
        "blocks_normalization": True,
        "fixability": "requires_source_evidence",
        "specification": "VCF breakend relationship fields",
    },
    "VSS-BND-RELATIONSHIP-UNDECLARED": {
        "meaning": "A breakend record has no explicit mate relationship.",
        "default_severity": "warning",
        "category": "event_graph",
        "blocks_normalization": False,
        "fixability": "requires_source_evidence",
        "specification": "VCF breakend relationship fields",
    },
    "VSS-ID-DUPLICATE": {
        "meaning": "A non-missing record ID occurs more than once.",
        "default_severity": "error",
        "category": "vcf_conformance",
        "blocks_normalization": True,
        "fixability": "requires_adapter",
        "specification": "VCF record identifiers",
    },
    "VSS-ALT-TYPE-CONFLICT": {
        "meaning": "A symbolic or sequence allele conflicts with the declared structural type.",
        "default_severity": "error",
        "category": "sv_semantics",
        "blocks_normalization": True,
        "fixability": "requires_adapter",
        "specification": "VCF symbolic allele semantics",
    },
    "VSS-CARDINALITY-INFO": {
        "meaning": "An INFO value count conflicts with its header Number declaration.",
        "default_severity": "error",
        "category": "vcf_conformance",
        "blocks_normalization": True,
        "fixability": "requires_adapter",
        "specification": "VCF INFO Number declaration",
    },
    "VSS-HEADER-RESERVED-DECLARATION": {
        "meaning": "A reserved field uses a nonstandard Type or Number declaration.",
        "default_severity": "error",
        "category": "vcf_conformance",
        "blocks_normalization": True,
        "fixability": "requires_adapter",
        "specification": "VCF field declaration",
    },
    "VSS-NORMALIZATION-ADAPTER-UNPROVEN": {
        "meaning": "The selected adapter lacks evidence for the requested rewrite profile.",
        "default_severity": "error",
        "category": "normalization_safety",
        "blocks_normalization": True,
        "fixability": "requires_source_evidence",
        "specification": "normalization profile contract",
    },
    "VSS-NORMALIZATION-PROFILE-UNIMPLEMENTED": {
        "meaning": "A representation-changing profile has no implemented transformation.",
        "default_severity": "error",
        "category": "normalization_safety",
        "blocks_normalization": True,
        "fixability": "not_fixable",
        "specification": "normalization profile contract",
    },
}


def _catalog_entry(
    meaning: str,
    *,
    category: str = "vcf_conformance",
    severity: str = "error",
    fixability: str = "requires_adapter",
    specification: str = "VCF 4.5",
) -> dict[str, Any]:
    return {
        "meaning": meaning,
        "default_severity": severity,
        "category": category,
        "blocks_normalization": True,
        "fixability": fixability,
        "specification": specification,
    }


CATALOG.update(
    {
        "VSS-CARDINALITY-FORMAT": _catalog_entry(
            "A FORMAT value count conflicts with its header Number declaration."
        ),
        "VSS-LOCAL-ALLELE-EQUIVALENCE": _catalog_entry(
            "Local and full-allele FORMAT fields encode conflicting non-missing values."
        ),
        "VSS-LOCAL-ALLELE-GT-CONFLICT": _catalog_entry(
            "A called alternate allele is absent from LAA while local fields are used."
        ),
        "VSS-LOCAL-ALLELE-INVALID": _catalog_entry(
            "LAA does not contain distinct, in-range, one-based ALT indexes."
        ),
        "VSS-LOCAL-ALLELE-LAA-REQUIRED": _catalog_entry(
            "A non-missing local-allele field is present without LAA."
        ),
        "VSS-LOCAL-ALLELE-ORDER": _catalog_entry(
            "LAA does not precede every other local-allele FORMAT field."
        ),
        "VSS-NORMALIZATION-CANONICAL-INPUT-VERSION": _catalog_entry(
            "Canonical normalization requires finalized VCF 4.5 input.",
            category="normalization_safety",
            fixability="requires_source_evidence",
            specification="normalization profile contract",
        ),
        "VSS-NORMALIZATION-SOURCE-COMPARISON-UNSAFE": _catalog_entry(
            "Merged-source evidence is incomplete or ambiguous for canonical rewriting.",
            category="normalization_safety",
            fixability="requires_source_evidence",
            specification="source-manifest comparison contract",
        ),
        "VSS-NORMALIZATION-SOURCE-MANIFEST-REQUIRED": _catalog_entry(
            "A merger-produced callset lacks the source manifest required for rewriting.",
            category="normalization_safety",
            fixability="requires_source_evidence",
            specification="source-manifest comparison contract",
        ),
        "VSS-PHASE-BREAKPOINT-MISMATCH": _catalog_entry(
            "Reciprocal breakpoint records disagree in PSL or PSO."
        ),
        "VSS-PHASE-PS-PSL-CONFLICT": _catalog_entry(
            "One sample genotype defines both mutually exclusive PS and PSL values."
        ),
        "VSS-PHASE-PSL-UNPHASED": _catalog_entry(
            "PSL is non-missing for an allele without a preceding phase separator."
        ),
        "VSS-PHASE-PSO-REQUIRED": _catalog_entry(
            "An SV-associated phase set lacks the traversal ordinal required in PSO.",
            severity="warning",
        ),
        "VSS-PHASE-PSO-WITHOUT-PSL": _catalog_entry(
            "PSO is non-missing where the corresponding PSL value is missing."
        ),
        "VSS-PHASE-PSQ-WITHOUT-PSL": _catalog_entry(
            "PSQ is non-missing where the corresponding PSL value is missing."
        ),
        "VSS-SOURCE-COMPARISON": _catalog_entry(
            "A source observation has an explicit merged-lineage comparison outcome.",
            category="source_lineage",
            severity="info",
            fixability="requires_source_evidence",
            specification="source-manifest comparison contract",
        ),
        "VSS-V45-END-COMPUTED-MISMATCH": _catalog_entry(
            "Deprecated END differs from the maximum end computed from REF, SVLEN, and LEN."
        ),
        "VSS-V45-EVENTTYPE-WITHOUT-EVENT": _catalog_entry(
            "A non-missing EVENTTYPE lacks an allele-specific EVENT identifier."
        ),
        "VSS-V45-LEN-WITHOUT-REFERENCE-BLOCK": _catalog_entry(
            "FORMAT LEN appears on a record without <*> or <NON_REF>."
        ),
        "VSS-V45-REFERENCE-BLOCK-LAA": _catalog_entry(
            "A reference-block start uses LAA without the unspecified ALT allele."
        ),
        "VSS-V45-REFERENCE-BLOCK-LEN": _catalog_entry(
            "A non-missing FORMAT LEN value is not a positive block length."
        ),
        "VSS-V45-SVCLAIM-INVALID": _catalog_entry(
            "SVCLAIM is incompatible with the corresponding ALT allele."
        ),
        "VSS-V45-SVCLAIM-REQUIRED": _catalog_entry(
            "A symbolic DEL or DUP allele lacks its required SVCLAIM."
        ),
        "VSS-V45-SVLEN-LEGACY-SIGN": _catalog_entry(
            "A legacy negative SVLEN is interpreted by absolute value.", severity="warning"
        ),
        "VSS-V45-SVLEN-NOT-APPLICABLE": _catalog_entry(
            "SVLEN is non-missing for an ALT allele where VCF 4.5 requires missing."
        ),
        "VSS-V45-SVLEN-REQUIRED": _catalog_entry(
            "A symbolic structural ALT lacks SVLEN and a usable legacy END fallback."
        ),
        "VSS-V45-SVTYPE-CONFLICT": _catalog_entry(
            "Deprecated SVTYPE does not agree exactly with every ALT allele."
        ),
        "VSS-V45-SYMBOLIC-ALT-CASE": _catalog_entry(
            "A reserved symbolic ALT identifier uses incorrect letter case."
        ),
        "VSS-V45-SYMBOLIC-BND-DISALLOWED": _catalog_entry(
            "A symbolic BND or TRA ALT is used instead of VCF 4.5 breakpoint notation."
        ),
        "VSS-VCF-VERSION-UNSUPPORTED-FINAL-OR-DRAFT": _catalog_entry(
            "The fileformat declaration is draft, malformed, or newer than finalized VCF 4.5."
        ),
    }
)


def explain(code: str) -> dict[str, Any]:
    try:
        return {"code": code, **CATALOG[code]}
    except KeyError as exc:
        raise UsageError(f"Unknown diagnostic code: {code}") from exc
