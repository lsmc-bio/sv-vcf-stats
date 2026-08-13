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


def explain(code: str) -> dict[str, Any]:
    try:
        return {"code": code, **CATALOG[code]}
    except KeyError as exc:
        raise UsageError(f"Unknown diagnostic code: {code}") from exc
