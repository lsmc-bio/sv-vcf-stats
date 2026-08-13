#!/usr/bin/env python3
"""Verify fixture integrity, indexes, subject identity, and manifest bindings."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, cast

import pysam

from vcf_sv_stats.fixture_review import PENDING_REDISTRIBUTION_STATUS, load_review, verify_review
from vcf_sv_stats.serialization import file_sha256

SUBJECT = "HG002"
SUBJECT_TOKEN = re.compile(r"(?i)\b(?:HG\d{3}|NA\d{5}|GM\d{5})\b")
MAX_CLOSURE_RECORDS = 128
MAX_CORPUS_RECORDS = 2_500
MAX_COMPRESSED_BYTES = 10 * 1024 * 1024


def _unexpected_subjects(text: str) -> set[str]:
    return {token.upper() for token in SUBJECT_TOKEN.findall(text)} - {SUBJECT}


def _inspect_variant(path: Path) -> int:
    unexpected: set[str] = set()
    with pysam.VariantFile(str(path)) as variant:
        if tuple(variant.header.samples) != (SUBJECT,):
            raise ValueError(f"Fixture does not have exactly one HG002 sample: {path.name}")
        unexpected.update(_unexpected_subjects(str(variant.header)))
        observed = 0
        for record in variant:
            observed += 1
            unexpected.update(_unexpected_subjects(str(record)))
    if unexpected:
        raise ValueError(f"Unexpected subject token: {path.name}")
    return observed


def verify(root: Path, *, require_review: bool = True) -> dict[str, int]:
    manifest = cast(
        dict[str, Any], json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    )
    if manifest.get("subject") != SUBJECT:
        raise ValueError("Fixture manifest subject is not HG002")
    review_path = root / "redistribution-review.json"
    if review_path.is_file():
        redistribution_status = verify_review(manifest, load_review(review_path))
    elif require_review:
        raise ValueError("Fixture redistribution review policy is missing")
    else:
        redistribution_status = PENDING_REDISTRIBUTION_STATUS
    source_evidence = manifest.get("source_identity_evidence")
    if not isinstance(source_evidence, list) or len(source_evidence) != 22:
        raise ValueError("Fixture manifest must contain all 22 source identity inspections")
    evidence_digests: set[str] = set()
    for evidence in source_evidence:
        if evidence.get("sample_count") != 1 or evidence.get("subject_evidence") not in {
            "sample_is_hg002",
            "single_hg002_derived_alias",
        }:
            raise ValueError("Source identity evidence is not single-subject HG002")
        source_digest = evidence.get("source_sha256")
        if not isinstance(source_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", source_digest):
            raise ValueError("Source identity evidence has an invalid digest")
        evidence_digests.add(source_digest)
    checked = 0
    records = 0
    compressed_bytes = 0
    expected_variant_paths: set[Path] = set()
    source_fixture_counts: dict[str, int] = {}
    for entry in manifest["fixtures"]:
        if entry.get("subject") != SUBJECT:
            raise ValueError(f"Fixture manifest subject mismatch: {entry['fixture_id']}")
        if entry.get("source_sha256") not in evidence_digests:
            raise ValueError(f"Fixture source lacks HG002 identity evidence: {entry['fixture_id']}")
        if entry.get("redistribution_status") != redistribution_status:
            raise ValueError(f"Fixture redistribution review is incomplete: {entry['fixture_id']}")
        if entry.get("oversized_relationship_exclusions"):
            fixture_id = entry["fixture_id"]
            raise ValueError(f"Fixture has an oversized relationship exclusion: {fixture_id}")
        path = root / entry["fixture_path"]
        expected_variant_paths.add(path)
        if file_sha256(path) != entry["fixture_sha256"]:
            raise ValueError(f"Fixture digest mismatch: {path.name}")
        index = Path(str(path) + ".tbi")
        if not index.is_file() or file_sha256(index) != entry["index_sha256"]:
            raise ValueError(f"Fixture index mismatch: {path.name}")
        observed = _inspect_variant(path)
        if observed != entry["fixture_record_count"]:
            raise ValueError(f"Fixture record-count mismatch: {path.name}")
        source_records = int(entry["source_record_count"])
        target = min(100, max(12, (source_records + 199) // 200))
        if observed < target or observed > MAX_CLOSURE_RECORDS:
            raise ValueError(f"Fixture violates its deterministic record budget: {path.name}")
        checked += 1
        records += observed
        compressed_bytes += path.stat().st_size
        source_fixture_counts[path.name] = observed
    for derived in manifest.get("derived_parity_artifacts", []):
        if derived.get("subject") != SUBJECT:
            raise ValueError(f"Derived fixture subject mismatch: {derived['fixture_path']}")
        if derived.get("redistribution_status") != redistribution_status:
            fixture_path = derived["fixture_path"]
            raise ValueError(f"Derived fixture redistribution review is incomplete: {fixture_path}")
        path = root / derived["fixture_path"]
        expected_variant_paths.add(path)
        if file_sha256(path) != derived.get("fixture_sha256"):
            raise ValueError(f"Derived fixture digest mismatch: {path.name}")
        observed = _inspect_variant(path)
        if observed != derived.get("fixture_record_count"):
            raise ValueError(f"Derived fixture record-count mismatch: {path.name}")
        if observed != source_fixture_counts.get(derived["derived_from"]):
            raise ValueError(f"Derived fixture is not record-parallel: {path.name}")
        if "index_sha256" in derived:
            index = Path(str(path) + ".csi")
            if not index.is_file() or file_sha256(index) != derived["index_sha256"]:
                raise ValueError(f"Derived fixture index mismatch: {path.name}")
    actual_variant_paths = {
        path
        for path in (root / "vcf").iterdir()
        if path.is_file() and (path.name.endswith(".vcf.gz") or path.suffix in {".vcf", ".bcf"})
    }
    if actual_variant_paths != expected_variant_paths:
        raise ValueError("Fixture manifest and variant files do not match exactly")
    totals = manifest.get("totals", {})
    if records != totals.get("source_derived_records") or records > MAX_CORPUS_RECORDS:
        raise ValueError("Fixture corpus record total is invalid")
    if (
        compressed_bytes != totals.get("compressed_vcf_bytes")
        or compressed_bytes > MAX_COMPRESSED_BYTES
    ):
        raise ValueError("Fixture compressed-byte total is invalid")
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix in {".tbi", ".csi", ".bcf", ".gz"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if _unexpected_subjects(text):
            raise ValueError(f"Unexpected subject token: {path.name}")
    return {"fixtures": checked, "records": records}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-data-dir", type=Path, required=True)
    parser.add_argument("--allow-pending-redistribution-review", action="store_true")
    args = parser.parse_args()
    result = verify(
        args.test_data_dir.resolve(strict=True),
        require_review=not args.allow_pending_redistribution_review,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
