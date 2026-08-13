"""Built-in, versioned producer adapters and evidence-based detection."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from .exceptions import UsageError, ValidationFailure
from .models import AdapterCandidate, AdapterEvidence, DetectionResult


@dataclass(frozen=True, slots=True)
class AdapterDescriptor:
    adapter_id: str
    producer: str
    versions: tuple[str, ...]
    status: str
    producer_kind: str
    signatures: tuple[tuple[str, float], ...]
    rewrite_supported: bool = True
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "adapter_id": self.adapter_id,
            "producer": self.producer,
            "versions": list(self.versions),
            "status": self.status,
            "producer_kind": self.producer_kind,
            "rewrite_supported": self.rewrite_supported,
            "notes": self.notes,
        }


GENERIC_ADAPTER = AdapterDescriptor(
    adapter_id="urn:vcf-sv-stats:adapter:generic:1",
    producer="unknown",
    versions=(),
    status="supported",
    producer_kind="unknown",
    signatures=(),
    rewrite_supported=True,
    notes="Standards adapter for valid unknown or ambiguous producers.",
)


ADAPTERS: tuple[AdapterDescriptor, ...] = (
    AdapterDescriptor(
        "urn:vcf-sv-stats:adapter:manta:1",
        "Manta",
        ("1.6.0",),
        "supported",
        "caller",
        (("generatesvcandidates 1.6.0", 0.9), ("source=manta", 0.8)),
        notes="MATEID and EVENT relationships are preserved and resolved as explicit graph facts.",
    ),
    AdapterDescriptor(
        "urn:vcf-sv-stats:adapter:tiddit:1",
        "TIDDIT",
        ("3.9.7",),
        "supported",
        "caller",
        (("source=tiddit-3.9.7", 0.95), ("source=tiddit", 0.8)),
        notes=(
            "Duplicate IDs and breakends without declared mates remain diagnostics; "
            "reference repair requires a verified explicit reference."
        ),
    ),
    AdapterDescriptor(
        "urn:vcf-sv-stats:adapter:dysgu:1",
        "dysgu",
        ("1.8.0",),
        "supported",
        "caller",
        (("source=dysgu_1.8.0", 0.95), ("source=dysgu", 0.8)),
        notes=(
            "Translocation, anchor, and exclusion annotations are interpreted only in this adapter."
        ),
    ),
    AdapterDescriptor(
        "urn:vcf-sv-stats:adapter:sniffles2:1",
        "Sniffles2",
        ("2.8.0",),
        "supported",
        "caller",
        (("source=sniffles2_2.8.0", 0.95), ("source=sniffles2", 0.8)),
        notes="Unpaired breakends remain unresolved observations; no mate is inferred.",
    ),
    AdapterDescriptor(
        "urn:vcf-sv-stats:adapter:sentieon-longreadsv:1",
        "Sentieon LongReadSV",
        ("202503.03",),
        "supported",
        "caller",
        (("source=sentieon_longreadsv_202503.03", 0.98), ("longreadsv", 0.55)),
        notes="Multiallelic and phase-set declaration deviations remain explicit diagnostics.",
    ),
    AdapterDescriptor(
        "urn:vcf-sv-stats:adapter:sentieon-cnvscope:1",
        "Sentieon CNVscope",
        ("202503.03",),
        "supported",
        "caller",
        (("source=sentieon_cnvscope_202503.03", 0.98), ("cnvscope", 0.55)),
        notes="Reference-genotype segments are distinguished from alternate CNV calls.",
    ),
    AdapterDescriptor(
        "urn:vcf-sv-stats:adapter:jasmine:1",
        "Jasmine",
        ("1.1.5",),
        "supported",
        "merger",
        (("source=jasmine_1.1.5", 0.98),),
        notes="Source-support annotations remain merger provenance and do not imply consensus.",
    ),
    AdapterDescriptor(
        "urn:vcf-sv-stats:adapter:survivor:1",
        "SURVIVOR",
        ("1.0.6",),
        "supported",
        "merger",
        (("source=survivor_1.0.6", 0.98), ("source=survivor", 0.8)),
        notes="Bracket, type, and source-support conventions remain merger-scoped.",
    ),
    AdapterDescriptor(
        "urn:vcf-sv-stats:adapter:octopusv:1",
        "OctopuSV",
        ("0.4.1",),
        "provisional",
        "merger",
        (("source=octopusv_0.4.1", 0.98),),
        rewrite_supported=False,
        notes="Public version identity remains provisional; caller-specific rewrites are disabled.",
    ),
    AdapterDescriptor(
        "urn:vcf-sv-stats:adapter:trussv:1",
        "TrusSV",
        ("0.3.1",),
        "provisional",
        "merger",
        (("source=trussv_0.3.1", 0.98), ("trussv", 0.55)),
        rewrite_supported=False,
        notes=(
            "Public upstream identity remains provisional; caller-specific rewrites are disabled."
        ),
    ),
    AdapterDescriptor(
        "urn:vcf-sv-stats:adapter:severus:1",
        "Severus",
        (),
        "unsupported",
        "caller",
        (("source=severus", 0.8),),
        rewrite_supported=False,
        notes="No native versioned fixture is available.",
    ),
    AdapterDescriptor(
        "urn:vcf-sv-stats:adapter:sentieon-shortread-sv:1",
        "Sentieon short-read SV",
        (),
        "unsupported",
        "caller",
        (("source=sentieon_shortread_sv", 0.9),),
        rewrite_supported=False,
        notes="No distinct native short-read SV fixture is available.",
    ),
)

_BY_ID = {item.adapter_id: item for item in (GENERIC_ADAPTER, *ADAPTERS)}


def list_adapters(*, status: str | None = None) -> tuple[AdapterDescriptor, ...]:
    values = (GENERIC_ADAPTER, *ADAPTERS)
    if status is None:
        return values
    allowed = {"supported", "provisional", "unsupported"}
    if status not in allowed:
        raise UsageError(f"Unknown adapter status: {status}")
    return tuple(value for value in values if value.status == status)


def get_adapter(adapter_id: str) -> AdapterDescriptor:
    try:
        return _BY_ID[adapter_id]
    except KeyError as exc:
        raise UsageError(f"Unknown adapter: {adapter_id}") from exc


def _candidate(descriptor: AdapterDescriptor, header_lower: str) -> AdapterCandidate | None:
    evidence: list[AdapterEvidence] = []
    score = 0.0
    for signature, weight in descriptor.signatures:
        if signature in header_lower:
            evidence.append(AdapterEvidence("header_signature", signature, weight))
            score += weight
    if not evidence:
        return None
    version: str | None = None
    for expected in descriptor.versions:
        if re.search(rf"(?<![0-9]){re.escape(expected.lower())}(?![0-9])", header_lower):
            version = expected
            score += 0.05
            evidence.append(AdapterEvidence("producer_version", expected, 0.05))
            break
    return AdapterCandidate(
        adapter_id=descriptor.adapter_id,
        producer=descriptor.producer,
        version=version,
        status=descriptor.status,
        score=min(score, 1.0),
        evidence=tuple(evidence),
    )


def detect_adapter(
    header_text: str,
    *,
    requested_adapter_id: str | None = None,
    accept_untested_version: bool = False,
) -> DetectionResult:
    header_lower = header_text.casefold()
    ranked = sorted(
        filter(None, (_candidate(item, header_lower) for item in ADAPTERS)),
        key=lambda item: (-item.score, item.adapter_id),
    )
    candidates = tuple(ranked)

    if requested_adapter_id is not None:
        descriptor = get_adapter(requested_adapter_id)
        if descriptor is GENERIC_ADAPTER:
            selected = AdapterCandidate(
                GENERIC_ADAPTER.adapter_id, "unknown", None, "supported", 1.0, ()
            )
            return DetectionResult(selected, candidates, False)
        match = next((item for item in candidates if item.adapter_id == requested_adapter_id), None)
        if match is None:
            raise ValidationFailure(
                f"Requested adapter does not match producer evidence: {requested_adapter_id}"
            )
        if descriptor.status == "unsupported":
            raise ValidationFailure(f"Requested adapter is unsupported: {requested_adapter_id}")
        if match.version is None and descriptor.versions and not accept_untested_version:
            raise ValidationFailure(
                f"Producer version is outside the tested range for {requested_adapter_id}"
            )
        if match.version is None and descriptor.versions:
            match = AdapterCandidate(
                match.adapter_id,
                match.producer,
                match.version,
                "provisional",
                match.score,
                match.evidence,
            )
        return DetectionResult(match, candidates, False)

    ambiguous = len(candidates) > 1 and candidates[0].score - candidates[1].score < 0.15
    if not candidates or candidates[0].score < 0.5 or ambiguous:
        selected = AdapterCandidate(
            GENERIC_ADAPTER.adapter_id,
            "unknown",
            None,
            "supported",
            1.0,
            (),
        )
        return DetectionResult(selected, candidates, ambiguous)
    top = candidates[0]
    descriptor = get_adapter(top.adapter_id)
    if descriptor.status == "unsupported" or (
        top.version is None and descriptor.versions and not accept_untested_version
    ):
        selected = AdapterCandidate(
            GENERIC_ADAPTER.adapter_id,
            "unknown",
            None,
            "supported",
            1.0,
            (),
        )
        return DetectionResult(selected, candidates, False)
    if top.version is None and descriptor.versions:
        top = AdapterCandidate(
            top.adapter_id,
            top.producer,
            top.version,
            "provisional",
            top.score,
            top.evidence,
        )
    return DetectionResult(top, candidates, False)


def registry_as_dict(
    descriptors: Iterable[AdapterDescriptor] | None = None,
) -> list[dict[str, object]]:
    return [item.as_dict() for item in descriptors or list_adapters()]
