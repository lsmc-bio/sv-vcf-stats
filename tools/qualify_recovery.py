#!/usr/bin/env python3
"""Qualify atomic stats publication under signals, a resource limit, and a crash."""

from __future__ import annotations

import argparse
import os
import platform
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from vcf_sv_stats.exceptions import UsageError
from vcf_sv_stats.io import assert_distinct_paths
from vcf_sv_stats.schemas import validate_artifact
from vcf_sv_stats.serialization import file_sha256, payload_sha256, write_json_atomic

try:
    import resource
except ImportError:  # pragma: no cover - this qualification is POSIX-only
    resource = None  # type: ignore[assignment]


SCENARIOS = ("sigint", "sigterm", "file_size_limit", "sigkill")


def _file_size_limit() -> None:
    if resource is None:  # pragma: no cover - guarded by qualify()
        return
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    resource.setrlimit(resource.RLIMIT_FSIZE, (512, 512))


def _wait_until_interruptible(process: subprocess.Popen[bytes], seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise UsageError("qualification input completed before interruption")
        time.sleep(min(0.01, max(0.0, deadline - time.monotonic())))
    if process.poll() is not None:
        raise UsageError("qualification input completed before interruption")


def _run_scenario(input_path: Path, scenario: str, *, settle_seconds: float) -> dict[str, Any]:
    if scenario not in SCENARIOS:
        raise UsageError(f"unknown recovery scenario: {scenario}")
    with tempfile.TemporaryDirectory(prefix=f"vss-recovery-{scenario}-") as directory_name:
        directory = Path(directory_name)
        temporary = directory / "temporary"
        temporary.mkdir()
        output = directory / "summary.json"
        command = [
            sys.executable,
            "-m",
            "vcf_sv_stats",
            "stats",
            str(input_path),
            "--temp-dir",
            str(temporary),
            "--output",
            str(output),
        ]
        preexec_fn = _file_size_limit if scenario == "file_size_limit" else None
        started_ns = time.perf_counter_ns()
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=preexec_fn,
        )
        if scenario != "file_size_limit":
            _wait_until_interruptible(process, settle_seconds)
            requested_signal = {
                "sigint": signal.SIGINT,
                "sigterm": signal.SIGTERM,
                "sigkill": signal.SIGKILL,
            }[scenario]
            process.send_signal(requested_signal)
        try:
            returncode = process.wait(timeout=120)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.wait()
            raise UsageError(f"recovery scenario did not terminate: {scenario}") from exc

        publication_entries = sorted(
            path.name for path in directory.iterdir() if path.name != temporary.name
        )
        transient_entries = sorted(
            path.name for path in directory.glob(f".{output.name}.*")
        )
        passed = returncode != 0 and not output.exists() and not transient_entries
        if not passed:
            raise UsageError(f"recovery scenario left a complete-looking artifact: {scenario}")
        return {
            "scenario": scenario,
            "elapsed_ns": time.perf_counter_ns() - started_ns,
            "returncode": returncode,
            "output_absent": not output.exists(),
            "publication_directory_entries": publication_entries,
            "transient_output_entries": transient_entries,
            "passed": passed,
        }


def qualify(
    input_path: Path,
    *,
    settle_seconds: float = 0.25,
    source_commit: str,
) -> dict[str, Any]:
    """Run the POSIX recovery matrix and return a digest-bound receipt."""
    if os.name != "posix" or resource is None:
        raise UsageError("signal and resource recovery qualification requires POSIX")
    if settle_seconds <= 0:
        raise UsageError("settle_seconds must be positive")
    if re.fullmatch(r"[0-9a-f]{40}", source_commit) is None:
        raise UsageError("source_commit must be a full lowercase Git commit digest")
    resolved = input_path.resolve(strict=True)
    if not resolved.is_file():
        raise UsageError("qualification input must be a regular file")
    scenarios = [
        _run_scenario(resolved, scenario, settle_seconds=settle_seconds)
        for scenario in SCENARIOS
    ]
    value: dict[str, Any] = {
        "schema_name": "vcf-sv-stats.recovery-qualification",
        "schema_version": "1.0.0",
        "environment": {
            "operating_system": platform.system(),
            "operating_system_release": platform.release(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
            "source_commit": source_commit,
        },
        "input": {
            "name": resolved.name,
            "bytes": resolved.stat().st_size,
            "sha256": file_sha256(resolved),
        },
        "policy": {
            "publication": "atomic_final_path",
            "resource_limit": "output_file_size_512_bytes",
            "paths": "basename_only",
        },
        "scenarios": scenarios,
    }
    value["receipt_sha256"] = payload_sha256(value)
    validate_artifact("recovery-qualification", value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--settle-seconds", type=float, default=0.25)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    assert_distinct_paths(args.input.resolve(strict=True), args.output)
    write_json_atomic(
        args.output,
        qualify(
            args.input,
            settle_seconds=args.settle_seconds,
            source_commit=args.source_commit,
        ),
    )


if __name__ == "__main__":
    main()
