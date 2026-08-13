#!/usr/bin/env python3
"""Run a repeatable local streaming benchmark without generating or copying inputs."""

from __future__ import annotations

import argparse
import platform
import resource
import time
from pathlib import Path
from typing import Any

from vcf_sv_stats.engine import stats
from vcf_sv_stats.exceptions import UsageError
from vcf_sv_stats.io import assert_distinct_paths
from vcf_sv_stats.models import OperationRequest
from vcf_sv_stats.serialization import payload_sha256, write_json_atomic


def _peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if platform.system() == "Darwin" else value * 1024


def benchmark(paths: tuple[Path, ...], *, repetitions: int) -> dict[str, Any]:
    """Benchmark full statistics scans and return path-safe measurements."""
    if repetitions < 1:
        raise UsageError("repetitions must be positive")
    if not paths:
        raise UsageError("at least one input is required")

    measurements: list[dict[str, Any]] = []
    for path in paths:
        resolved = path.resolve(strict=True)
        if not resolved.is_file():
            raise UsageError(f"benchmark input is not a regular file: {path.name}")
        input_bytes = resolved.stat().st_size
        runs: list[dict[str, Any]] = []
        payload_digests: set[str] = set()
        for repetition in range(1, repetitions + 1):
            before_rss = _peak_rss_bytes()
            started = time.perf_counter_ns()
            result = stats(OperationRequest(resolved))
            elapsed_ns = time.perf_counter_ns() - started
            peak_rss = _peak_rss_bytes()
            digest = payload_sha256(result.summary)
            payload_digests.add(digest)
            records = int(result.summary["statistics"]["source_records"]["total"])
            runs.append(
                {
                    "repetition": repetition,
                    "elapsed_ns": elapsed_ns,
                    "records": records,
                    "records_per_second": (
                        None if elapsed_ns == 0 else records * 1_000_000_000 / elapsed_ns
                    ),
                    "input_bytes_per_second": (
                        None if elapsed_ns == 0 else input_bytes * 1_000_000_000 / elapsed_ns
                    ),
                    "process_peak_rss_bytes": peak_rss,
                    "process_peak_rss_growth_bytes": max(0, peak_rss - before_rss),
                    "payload_sha256": digest,
                }
            )
        measurements.append(
            {
                "input_name": resolved.name,
                "input_bytes": input_bytes,
                "repetitions": runs,
                "deterministic_payload": len(payload_digests) == 1,
            }
        )
    return {
        "schema_name": "vcf-sv-stats.streaming-benchmark",
        "schema_version": "1.0.0",
        "measurement_notes": {
            "clock": "monotonic_wall_clock",
            "memory": "process_peak_rss_including_native_libraries",
            "paths": "basename_only",
        },
        "inputs": measurements,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=2)
    args = parser.parse_args()
    for source in args.input:
        assert_distinct_paths(source.resolve(strict=True), args.output)
    write_json_atomic(
        args.output,
        benchmark(tuple(args.input), repetitions=args.repetitions),
    )


if __name__ == "__main__":
    main()
