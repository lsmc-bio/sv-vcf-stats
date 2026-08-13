from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from tools.build_test_data import SourceSpec, build
from vcf_sv_stats.fixture_review import (
    PENDING_REDISTRIBUTION_STATUS,
    apply_review,
    load_review,
    manifest_review_digest,
    verify_review,
)

ROOT = Path(__file__).parents[1]


def _manifest() -> dict[str, Any]:
    return json.loads((ROOT / "test_data/manifest.json").read_text(encoding="utf-8"))


def test_committed_review_binds_every_manifest_field_except_disposition() -> None:
    manifest = _manifest()
    review = load_review(ROOT / "test_data/redistribution-review.json")

    assert manifest_review_digest(manifest) == review["manifest_review_digest"]
    assert verify_review(manifest, review) == review["redistribution_status"]

    tampered = copy.deepcopy(manifest)
    tampered["fixtures"][0]["source_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="reviewed digest set"):
        verify_review(tampered, review)


def test_review_can_only_promote_an_exact_pending_manifest() -> None:
    manifest = _manifest()
    review = load_review(ROOT / "test_data/redistribution-review.json")
    for collection in ("fixtures", "derived_parity_artifacts"):
        for entry in manifest[collection]:
            entry["redistribution_status"] = PENDING_REDISTRIBUTION_STATUS

    assert apply_review(manifest, review) == review["redistribution_status"]
    assert verify_review(manifest, review) == review["redistribution_status"]

    changed = copy.deepcopy(manifest)
    changed["derived_parity_artifacts"][0]["fixture_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="reviewed digest set"):
        apply_review(changed, review)


def test_source_specs_do_not_carry_a_default_review_disposition() -> None:
    assert "redistribution_status" not in SourceSpec.__dataclass_fields__
    assert inspect.signature(build).parameters["redistribution_review"].default is None
