"""Stable pre-1.0 API surface for inspection, validation, and reporting."""

from __future__ import annotations

from vcf_sv_stats.adapters import detect_adapter, get_adapter, list_adapters
from vcf_sv_stats.canonical import iter_canonical
from vcf_sv_stats.engine import discrepancies, inspect, stats, validate
from vcf_sv_stats.models import (
    AdapterCandidate,
    AnalysisUnit,
    CanonicalObservation,
    DetectionResult,
    Diagnostic,
    DiscrepancyResult,
    ExternalIdentifier,
    InspectionResult,
    NormalizationResult,
    OperationRequest,
    RunResult,
    StatisticsResult,
    ValidationResult,
)
from vcf_sv_stats.normalize import normalize, run_bundle

__all__ = [
    "AdapterCandidate",
    "AnalysisUnit",
    "CanonicalObservation",
    "DetectionResult",
    "Diagnostic",
    "DiscrepancyResult",
    "ExternalIdentifier",
    "InspectionResult",
    "NormalizationResult",
    "OperationRequest",
    "RunResult",
    "StatisticsResult",
    "ValidationResult",
    "detect_adapter",
    "discrepancies",
    "get_adapter",
    "inspect",
    "iter_canonical",
    "list_adapters",
    "normalize",
    "run_bundle",
    "stats",
    "validate",
]
