"""Exact-digest binding for fixture redistribution dispositions."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, cast

from .serialization import payload_sha256

PENDING_REDISTRIBUTION_STATUS = "pending-redistribution-review"
REVIEW_SCHEMA_NAME = "vcf-sv-stats.fixture-redistribution-review"
REVIEW_SCHEMA_VERSION = "1.0.0"
SHA256 = re.compile(r"[0-9a-f]{64}")


def manifest_review_digest(manifest: dict[str, Any]) -> str:
    """Digest every manifest field except the disposition written by the review."""
    projection = copy.deepcopy(manifest)
    for collection in ("fixtures", "derived_parity_artifacts"):
        entries = projection.get(collection)
        if not isinstance(entries, list):
            raise ValueError(f"Fixture manifest {collection} must be an array")
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError(f"Fixture manifest {collection} entry must be an object")
            entry.pop("redistribution_status", None)
    return payload_sha256(projection)


def load_review(path: Path) -> dict[str, str]:
    value = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    required = {
        "schema_name": REVIEW_SCHEMA_NAME,
        "schema_version": REVIEW_SCHEMA_VERSION,
        "subject": "HG002",
    }
    if any(value.get(key) != expected for key, expected in required.items()):
        raise ValueError("Fixture redistribution review identity is invalid")
    review_id = value.get("review_id")
    status = value.get("redistribution_status")
    digest = value.get("manifest_review_digest")
    if not isinstance(review_id, str) or not review_id:
        raise ValueError("Fixture redistribution review ID is invalid")
    if not isinstance(status, str) or not status.startswith("reviewed-"):
        raise ValueError("Fixture redistribution review status is not terminal")
    if not isinstance(digest, str) or SHA256.fullmatch(digest) is None:
        raise ValueError("Fixture redistribution review digest is invalid")
    return {
        "review_id": review_id,
        "redistribution_status": status,
        "manifest_review_digest": digest,
    }


def apply_review(manifest: dict[str, Any], review: dict[str, str]) -> str:
    observed = manifest_review_digest(manifest)
    if observed != review["manifest_review_digest"]:
        raise ValueError("Fixture manifest does not match the reviewed digest set")
    status = review["redistribution_status"]
    for collection in ("fixtures", "derived_parity_artifacts"):
        for entry in manifest[collection]:
            entry["redistribution_status"] = status
    return status


def verify_review(manifest: dict[str, Any], review: dict[str, str]) -> str:
    observed = manifest_review_digest(manifest)
    if observed != review["manifest_review_digest"]:
        raise ValueError("Fixture manifest does not match the reviewed digest set")
    status = review["redistribution_status"]
    entries = [*manifest["fixtures"], *manifest["derived_parity_artifacts"]]
    if not entries or {entry.get("redistribution_status") for entry in entries} != {status}:
        raise ValueError("Fixture redistribution dispositions do not match the review")
    return status
