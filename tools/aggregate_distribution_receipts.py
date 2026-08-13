#!/usr/bin/env python3
"""Aggregate the exact supported-target installed-distribution receipts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from vcf_sv_stats.exceptions import UsageError
from vcf_sv_stats.schemas import validate_artifact
from vcf_sv_stats.serialization import file_sha256, payload_sha256, write_json_atomic


def aggregate(input_dir: Path, targets_path: Path) -> dict[str, Any]:
    """Validate the full OS, architecture, Python, wheel, and sdist cross-product."""
    target_spec = cast(dict[str, Any], json.loads(targets_path.read_text(encoding="utf-8")))
    expected = []
    for target in target_spec["targets"]:
        for python_version in target_spec["python_versions"]:
            for channel in target_spec["installation_channels"]:
                expected.append((target, str(python_version), str(channel)))
    expected_names = {
        f"{target['id']}.py{python_version}.{channel}.json"
        for target, python_version, channel in expected
    }
    observed_names = {item.name for item in input_dir.glob("*.json")}
    if observed_names != expected_names:
        raise UsageError("distribution receipts do not match the supported target matrix")

    cases = []
    semantic_digests = set()
    tool_versions = set()
    for target, python_version, channel in expected:
        name = f"{target['id']}.py{python_version}.{channel}.json"
        path = input_dir / name
        value = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
        validate_artifact("install-verification", value)
        unsigned = dict(value)
        observed_digest = unsigned.pop("receipt_sha256")
        if observed_digest != payload_sha256(unsigned):
            raise UsageError("installed-distribution receipt digest does not match")
        environment = value["environment"]
        if (
            environment["operating_system"] != target["operating_system"]
            or environment["machine"] != target["machine"]
            or not str(environment["python_version"]).startswith(f"{python_version}.")
        ):
            raise UsageError("installed-distribution receipt target does not match")
        semantic_digests.add(str(value["semantic_sha256"]))
        tool_versions.add(str(environment["tool_version"]))
        cases.append(
            {
                "target": target["id"],
                "runner": target["runner"],
                "python": python_version,
                "channel": channel,
                "receipt_name": name,
                "receipt_sha256": file_sha256(path),
                "passed": value["passed"],
            }
        )
    if len(semantic_digests) != 1 or len(tool_versions) != 1:
        raise UsageError("distribution semantics or candidate version differs across targets")
    value = {
        "schema_name": "vcf-sv-stats.distribution-qualification",
        "schema_version": "1.0.0",
        "target_spec_sha256": file_sha256(targets_path),
        "tool_version": next(iter(tool_versions)),
        "semantic_sha256": next(iter(semantic_digests)),
        "case_count": len(cases),
        "cases": cases,
        "wheel_sdist_parity": True,
        "all_supported_targets_passed": all(item["passed"] for item in cases),
    }
    value["receipt_sha256"] = payload_sha256(value)
    validate_artifact("distribution-qualification", value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument(
        "--targets", type=Path, default=Path("packaging/supported-targets.json")
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_json_atomic(
        args.output,
        aggregate(args.input_dir.resolve(strict=True), args.targets.resolve(strict=True)),
    )


if __name__ == "__main__":
    main()
