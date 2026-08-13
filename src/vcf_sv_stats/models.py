"""Immutable public models for the versioned API."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


class Fixability(StrEnum):
    SAFE_AUTOMATIC = "safe_automatic"
    REQUIRES_REFERENCE = "requires_reference"
    REQUIRES_ADAPTER = "requires_adapter"
    REQUIRES_SOURCE_EVIDENCE = "requires_source_evidence"
    REQUIRES_LOSS_AUTHORIZATION = "requires_loss_authorization"
    NOT_FIXABLE = "not_fixable"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class ExternalIdentifier:
    namespace: str
    value: str


@dataclass(frozen=True, slots=True)
class AnalysisUnit:
    analysis_unit_id: str
    display_id: str | None = None
    algorithm_id: str | None = None
    mapped_vcf_sample_ids: tuple[str, ...] = ()
    external_identifiers: tuple[ExternalIdentifier, ...] = ()


@dataclass(frozen=True, slots=True)
class OperationRequest:
    input_path: str | Path
    adapter_id: str | None = None
    accept_untested_producer_version: bool = False
    identity_context: str | Path | None = None
    reference: str | Path | None = None
    mode: Literal["compatible", "standard", "strict", "pedantic"] = "standard"
    threads: int = 1
    temp_dir: str | Path | None = None
    regions: tuple[str, ...] = ()
    regions_scan: bool = False
    max_input_bytes: int | None = None
    max_uncompressed_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class CanonicalObservation:
    source_record_ordinal: int
    allele_ordinal: int
    chrom: str
    pos: int
    record_id: str | None
    original_svtype: str | None
    normalized_type: str
    representation: str
    length_bp: int | None
    filter_state: str
    mate_ids: tuple[str, ...] = ()
    event_id: str | None = None


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    severity: Severity
    category: str
    message: str
    record_ordinal: int | None = None
    chrom: str | None = None
    pos: int | None = None
    field_name: str | None = None
    specification: str | None = None
    fixability: Fixability = Fixability.NOT_APPLICABLE
    blocks_statistics: bool = False
    blocks_normalization: bool = False
    adapter_id: str | None = None
    producer_version: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AdapterEvidence:
    key: str
    value: str
    weight: float


@dataclass(frozen=True, slots=True)
class AdapterCandidate:
    adapter_id: str
    producer: str
    version: str | None
    status: str
    score: float
    evidence: tuple[AdapterEvidence, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DetectionResult:
    selected: AdapterCandidate
    candidates: tuple[AdapterCandidate, ...]
    ambiguous: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class InspectionResult:
    input: dict[str, Any]
    header: dict[str, Any]
    detection: DetectionResult
    callset: dict[str, Any]
    diagnostics: tuple[Diagnostic, ...] = ()
    complete: bool = True

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["detection"] = self.detection.as_dict()
        value["diagnostics"] = [item.as_dict() for item in self.diagnostics]
        return value


@dataclass(frozen=True, slots=True)
class ValidationResult:
    valid: bool
    states: dict[str, str]
    diagnostics: tuple[Diagnostic, ...]
    input: dict[str, Any]
    detection: DetectionResult

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "states": self.states,
            "diagnostics": [item.as_dict() for item in self.diagnostics],
            "input": self.input,
            "detection": self.detection.as_dict(),
        }


@dataclass(frozen=True, slots=True)
class StatisticsResult:
    summary: dict[str, Any]
    diagnostics: tuple[Diagnostic, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {"summary": self.summary, "diagnostics": [d.as_dict() for d in self.diagnostics]}


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    output_path: Path
    index_path: Path
    manifest_path: Path
    receipt_path: Path
    output_sha256: str
    index_sha256: str
    manifest_sha256: str
    diagnostics: tuple[Diagnostic, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "output_path": str(self.output_path),
            "index_path": str(self.index_path),
            "manifest_path": str(self.manifest_path),
            "receipt_path": str(self.receipt_path),
            "output_sha256": self.output_sha256,
            "index_sha256": self.index_sha256,
            "manifest_sha256": self.manifest_sha256,
            "diagnostics": [d.as_dict() for d in self.diagnostics],
        }


@dataclass(frozen=True, slots=True)
class DiscrepancyResult:
    diagnostics: tuple[Diagnostic, ...]
    counts: dict[str, int]
    complete: bool
    report_path: Path | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "diagnostics": [d.as_dict() for d in self.diagnostics],
            "counts": self.counts,
            "complete": self.complete,
            "report_path": None if self.report_path is None else str(self.report_path),
        }


@dataclass(frozen=True, slots=True)
class RunResult:
    output_dir: Path
    artifacts: tuple[Path, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {"output_dir": str(self.output_dir), "artifacts": [str(p) for p in self.artifacts]}
