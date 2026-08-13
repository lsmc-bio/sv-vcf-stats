#!/usr/bin/env python3
"""Regenerate deterministic application goldens from the committed fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from tools.build_test_data import (
    _auxiliary_artifacts,
    _fixture_notice,
    _write_source_comparison_artifacts,
)
from vcf_sv_stats.engine import stats
from vcf_sv_stats.models import OperationRequest
from vcf_sv_stats.serialization import json_bytes, write_bytes_atomic


def _expected_output(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    result = stats(OperationRequest(path))
    value = {
        "fixture": path.name,
        "detection": result.summary["callset"]["producer"],
        "callset": {
            key: result.summary["callset"][key]
            for key in ("vcf_sample_ids", "single_sample", "record_count", "allele_count")
        },
        "statistics": result.summary["statistics"],
        "diagnostic_codes": sorted(item.code for item in result.diagnostics),
    }
    return value, [item.as_dict() for item in result.diagnostics]


def regenerate(test_data_dir: Path) -> None:
    manifest = cast(
        dict[str, Any],
        json.loads((test_data_dir / "manifest.json").read_text(encoding="utf-8")),
    )
    expected_dir = test_data_dir / "expected"
    if not expected_dir.is_dir():
        raise ValueError("Expected-output directory does not exist")
    for entry in manifest["fixtures"]:
        fixture_id = str(entry["fixture_id"])
        fixture = test_data_dir / str(entry["fixture_path"])
        expected, diagnostics = _expected_output(fixture)
        write_bytes_atomic(
            expected_dir / f"{fixture_id}.expected.json",
            json_bytes(expected),
            force=True,
        )
        diagnostic_content = "".join(
            json.dumps(item, sort_keys=True) + "\n" for item in diagnostics
        ).encode()
        write_bytes_atomic(
            expected_dir / f"{fixture_id}.diagnostics.jsonl",
            diagnostic_content,
            force=True,
        )
    _write_source_comparison_artifacts(test_data_dir, expected_dir)
    (test_data_dir / "NOTICE.md").write_text(_fixture_notice(), encoding="utf-8")
    manifest["auxiliary_artifacts"] = _auxiliary_artifacts(test_data_dir)
    write_bytes_atomic(
        test_data_dir / "manifest.json",
        json_bytes(manifest),
        force=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-data-dir", type=Path, required=True)
    args = parser.parse_args()
    regenerate(args.test_data_dir.resolve(strict=True))


if __name__ == "__main__":
    main()
