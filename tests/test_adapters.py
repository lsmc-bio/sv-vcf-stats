from __future__ import annotations

import pytest

from vcf_sv_stats.adapters import detect_adapter, get_adapter, list_adapters
from vcf_sv_stats.exceptions import ValidationFailure


def test_registry_statuses_and_rewrite_policy() -> None:
    supported = {item.producer for item in list_adapters(status="supported")}
    provisional = {item.producer for item in list_adapters(status="provisional")}
    unsupported = {item.producer for item in list_adapters(status="unsupported")}

    assert {"Manta", "TIDDIT", "dysgu", "Sniffles2", "Jasmine", "SURVIVOR"} <= supported
    assert provisional == {"OctopuSV", "TrusSV"}
    assert unsupported == {"Severus", "Sentieon short-read SV"}
    assert not get_adapter("urn:vcf-sv-stats:adapter:octopusv:1").rewrite_supported


def test_versioned_detection_and_generic_fallback() -> None:
    detected = detect_adapter("##source=Manta_1.6.0\n##cmd=GenerateSVCandidates 1.6.0")
    assert detected.selected.adapter_id == "urn:vcf-sv-stats:adapter:manta:1"
    assert detected.selected.version == "1.6.0"

    generic = detect_adapter("##source=unrecognized-public-caller")
    assert generic.selected.adapter_id == "urn:vcf-sv-stats:adapter:generic:1"


def test_explicit_adapter_requires_matching_evidence() -> None:
    with pytest.raises(ValidationFailure, match="does not match"):
        detect_adapter(
            "##source=Manta_1.6.0",
            requested_adapter_id="urn:vcf-sv-stats:adapter:tiddit:1",
        )


def test_ambiguous_and_untested_detection_are_safe() -> None:
    ambiguous = detect_adapter("##source=manta\n##source=tiddit")
    assert ambiguous.ambiguous
    assert ambiguous.selected.producer == "unknown"
    assert len(ambiguous.candidates) == 2

    untested = detect_adapter("##source=manta", accept_untested_version=True)
    assert untested.selected.producer == "Manta"
    assert untested.selected.version is None
    assert untested.selected.status == "provisional"
