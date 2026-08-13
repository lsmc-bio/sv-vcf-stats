#!/usr/bin/env python3
"""Run isolated, path-safe streaming and minimal-reader benchmarks."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

import pysam

from vcf_sv_stats import __version__
from vcf_sv_stats.engine import stats
from vcf_sv_stats.exceptions import UsageError
from vcf_sv_stats.io import assert_distinct_paths
from vcf_sv_stats.models import OperationRequest
from vcf_sv_stats.schemas import validate_artifact
from vcf_sv_stats.serialization import json_bytes, payload_sha256, write_json_atomic

try:
    import resource
except ImportError:  # pragma: no cover - exercised by the Windows distribution matrix
    resource = None  # type: ignore[assignment]


def _peak_rss_bytes() -> int | None:
    if resource is None:
        return None
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if platform.system() == "Darwin" else value * 1024


def _cpu_times_ns() -> tuple[int, int]:
    if resource is None:
        return time.process_time_ns(), 0
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return int(usage.ru_utime * 1_000_000_000), int(usage.ru_stime * 1_000_000_000)


def _tree_bytes(root: Path) -> int:
    total = 0
    for path in root.rglob("*"):
        try:
            if path.is_file():
                total += path.stat().st_size
        except FileNotFoundError:
            continue
    return total


class TemporarySpaceMonitor:
    def __init__(self, root: Path, *, interval_seconds: float = 0.01):
        self.root = root
        self.interval_seconds = interval_seconds
        self.peak_bytes = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="vss-temp-monitor", daemon=True)

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self.peak_bytes = max(self.peak_bytes, _tree_bytes(self.root))

    def __enter__(self) -> TemporarySpaceMonitor:
        self._thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.peak_bytes = max(self.peak_bytes, _tree_bytes(self.root))
        self._stop.set()
        self._thread.join()


def _minimal_pysam_scan(path: Path) -> tuple[int, int, int, int, int, int]:
    records = 0
    alleles = 0
    sample_calls = 0
    called_genotype_alleles = 0
    with pysam.VariantFile(str(path)) as variant:
        samples = len(variant.header.samples)
        contigs = len(variant.header.contigs)
        for record in variant:
            records += 1
            alleles += len(record.alts or ())
            for call in record.samples.values():
                sample_calls += 1
                genotype = call.get("GT")
                if genotype:
                    called_genotype_alleles += sum(allele is not None for allele in genotype)
                call.get("CN")
                call.get("CNQ")
    return records, alleles, samples, contigs, sample_calls, called_genotype_alleles


def worker(path: Path, *, mode: str, threads: int) -> dict[str, Any]:
    """Run one measurement in a fresh process."""
    if mode not in {"stats", "pysam"}:
        raise UsageError(f"unknown benchmark mode: {mode}")
    if threads < 1:
        raise UsageError("threads must be positive")
    resolved = path.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="vss-benchmark-worker-") as temporary_name:
        temporary = Path(temporary_name)
        before_user_ns, before_system_ns = _cpu_times_ns()
        started_ns = time.perf_counter_ns()
        with TemporarySpaceMonitor(temporary) as monitor:
            if mode == "stats":
                result = stats(OperationRequest(resolved, temp_dir=temporary, threads=threads))
                summary = result.summary
                records = int(summary["statistics"]["source_records"]["total"])
                alleles = int(summary["statistics"]["alleles"]["total"])
                samples = len(summary["callset"]["vcf_sample_ids"])
                with pysam.VariantFile(str(resolved)) as variant:
                    contigs = len(variant.header.contigs)
                digest = payload_sha256(summary)
                output_bytes = len(json_bytes(summary))
            else:
                (
                    records,
                    alleles,
                    samples,
                    contigs,
                    sample_calls,
                    called_genotype_alleles,
                ) = _minimal_pysam_scan(resolved)
                baseline = {
                    "records": records,
                    "alleles": alleles,
                    "samples": samples,
                    "contigs": contigs,
                    "sample_calls": sample_calls,
                    "called_genotype_alleles": called_genotype_alleles,
                }
                digest = payload_sha256(baseline)
                output_bytes = len(json_bytes(baseline))
        elapsed_ns = time.perf_counter_ns() - started_ns
        after_user_ns, after_system_ns = _cpu_times_ns()
        return {
            "mode": mode,
            "threads": threads,
            "elapsed_ns": elapsed_ns,
            "user_cpu_ns": max(0, after_user_ns - before_user_ns),
            "system_cpu_ns": max(0, after_system_ns - before_system_ns),
            "records": records,
            "alleles": alleles,
            "samples": samples,
            "contigs": contigs,
            "records_per_second": records * 1_000_000_000 / elapsed_ns,
            "input_bytes_per_second": resolved.stat().st_size * 1_000_000_000 / elapsed_ns,
            "process_peak_rss_bytes": _peak_rss_bytes(),
            "temporary_peak_bytes": monitor.peak_bytes,
            "temporary_final_bytes": _tree_bytes(temporary),
            "output_json_bytes": output_bytes,
            "payload_sha256": digest,
        }


def _run_worker(path: Path, *, mode: str, threads: int) -> dict[str, Any]:
    process = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker",
            "--worker-input",
            str(path),
            "--worker-mode",
            mode,
            "--worker-threads",
            str(threads),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        raise UsageError(f"benchmark worker failed for {path.name} in {mode} mode")
    try:
        value = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise UsageError(f"benchmark worker returned invalid JSON for {path.name}") from exc
    if not isinstance(value, dict):
        raise UsageError(f"benchmark worker returned an invalid result for {path.name}")
    return value


def _command_value(command: list[str]) -> str:
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    return result.stdout.strip() or "unavailable"


def _cpu_model() -> str:
    if platform.system() == "Darwin":
        return _command_value(["sysctl", "-n", "machdep.cpu.brand_string"])
    if platform.system() == "Linux":
        try:
            for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
                if line.lower().startswith("model name"):
                    return line.partition(":")[2].strip()
        except OSError:
            pass
    return platform.processor() or "unavailable"


def _total_memory_bytes() -> int | None:
    if platform.system() == "Darwin":
        value = _command_value(["sysctl", "-n", "hw.memsize"])
        return int(value) if value.isdigit() else None
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
    except (AttributeError, OSError, ValueError):
        return None
    return int(pages) * int(page_size)


def _filesystem_type(path: Path) -> str:
    if platform.system() == "Darwin":
        device_output = _command_value(["df", "-P", str(path)])
        lines = device_output.splitlines()
        device = lines[-1].split()[0] if len(lines) >= 2 and lines[-1].split() else ""
        mount_output = _command_value(["mount"])
        for line in mount_output.splitlines():
            if device and line.startswith(f"{device} on ") and "(" in line:
                return line.rpartition("(")[2].partition(",")[0].rstrip(")")
        return "unavailable"
    return _command_value(["stat", "-f", "-c", "%T", str(path)])


def _environment(path: Path, *, source_commit: str) -> dict[str, Any]:
    return {
        "operating_system": platform.system(),
        "operating_system_release": platform.release(),
        "machine": platform.machine(),
        "cpu_model": _cpu_model(),
        "logical_cpu_count": os.cpu_count(),
        "total_memory_bytes": _total_memory_bytes(),
        "filesystem_type": _filesystem_type(path.parent),
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "tool_version": __version__,
        "pysam_version": pysam.__version__,
        "htslib_version": getattr(pysam, "__samtools_version__", "unavailable"),
        "temp_monitor_interval_ms": 10,
        "source_commit": source_commit,
    }


def _assert_path_safe(value: Any) -> None:
    if isinstance(value, dict):
        for nested in value.values():
            _assert_path_safe(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_path_safe(nested)
    elif isinstance(value, str) and value.startswith(("/", "\\")):
        raise UsageError("benchmark receipt contains a filesystem path")


def benchmark(
    paths: tuple[Path, ...],
    *,
    repetitions: int,
    threads: tuple[int, ...] = (1,),
    include_baseline: bool = True,
    source_commit: str = "0" * 40,
) -> dict[str, Any]:
    """Benchmark full statistics scans in isolated child processes."""
    if repetitions < 1:
        raise UsageError("repetitions must be positive")
    if not paths:
        raise UsageError("at least one input is required")
    if not threads or any(value < 1 for value in threads):
        raise UsageError("thread counts must be positive")
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise UsageError("source_commit must be a full lowercase Git commit digest")

    environment = _environment(paths[0].resolve(strict=True), source_commit=source_commit)
    measurements: list[dict[str, Any]] = []
    for path in paths:
        resolved = path.resolve(strict=True)
        if not resolved.is_file():
            raise UsageError(f"benchmark input is not a regular file: {path.name}")
        input_runs: list[dict[str, Any]] = []
        for thread_count in threads:
            for repetition in range(1, repetitions + 1):
                run = _run_worker(resolved, mode="stats", threads=thread_count)
                run.update(
                    {
                        "repetition": repetition,
                        "cache_state": (
                            "cold_process_uncontrolled_os_cache"
                            if repetition == 1 and not input_runs
                            else "warm_process_uncontrolled_os_cache"
                        ),
                    }
                )
                input_runs.append(run)
        if include_baseline:
            baseline = _run_worker(resolved, mode="pysam", threads=1)
            baseline.update({"repetition": 1, "cache_state": "warm_process_uncontrolled_os_cache"})
            input_runs.append(baseline)
        stats_digests = {str(run["payload_sha256"]) for run in input_runs if run["mode"] == "stats"}
        measurements.append(
            {
                "input_name": resolved.name,
                "input_bytes": resolved.stat().st_size,
                "container": (
                    "vcf.gz"
                    if resolved.name.endswith(".vcf.gz")
                    else "bcf"
                    if resolved.suffix == ".bcf"
                    else "vcf"
                ),
                "measurements": input_runs,
                "deterministic_stats_payload": len(stats_digests) == 1,
            }
        )

    value: dict[str, Any] = {
        "schema_name": "vcf-sv-stats.streaming-benchmark",
        "schema_version": "1.0.0",
        "environment": environment,
        "measurement_policy": {
            "clock": "monotonic_wall_clock",
            "memory": "fresh_process_peak_rss_including_native_libraries",
            "temporary_space": "10ms_recursive_size_sampling",
            "cache": "first-process-cold-label_without_os_cache_eviction_then_warm",
            "baseline": f"minimal_sequential_pysam_{pysam.__version__}_record_scan",
            "paths": "basename_only",
        },
        "inputs": measurements,
    }
    value["receipt_sha256"] = payload_sha256(value)
    _assert_path_safe(value)
    validate_artifact("streaming-benchmark", value)
    return value


def refresh_baselines(value: dict[str, Any], paths: tuple[Path, ...]) -> dict[str, Any]:
    """Replace minimal-reader measurements without rerunning full statistics scans."""
    validate_artifact("streaming-benchmark", value)
    unsigned = dict(value)
    observed_digest = unsigned.pop("receipt_sha256")
    if observed_digest != payload_sha256(unsigned):
        raise UsageError("benchmark receipt digest does not match")
    by_name = {path.name: path.resolve(strict=True) for path in paths}
    if len(by_name) != len(paths):
        raise UsageError("benchmark baseline input basenames must be unique")
    expected_names = {str(item["input_name"]) for item in value["inputs"]}
    if set(by_name) != expected_names:
        raise UsageError("benchmark baseline inputs do not match the receipt")

    refreshed = json.loads(json.dumps(value))
    for input_result in refreshed["inputs"]:
        input_name = str(input_result["input_name"])
        baseline = _run_worker(by_name[input_name], mode="pysam", threads=1)
        baseline.update(
            {
                "repetition": 1,
                "cache_state": "warm_process_uncontrolled_os_cache",
            }
        )
        measurements = [
            measurement
            for measurement in input_result["measurements"]
            if measurement["mode"] != "pysam"
        ]
        measurements.append(baseline)
        input_result["measurements"] = measurements
    refreshed.pop("receipt_sha256")
    refreshed["receipt_sha256"] = payload_sha256(refreshed)
    _assert_path_safe(refreshed)
    validate_artifact("streaming-benchmark", refreshed)
    return refreshed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--threads", type=int, action="append")
    parser.add_argument("--no-baseline", action="store_true")
    parser.add_argument("--refresh-baselines", type=Path)
    parser.add_argument("--source-commit")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--worker-input", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--worker-mode", choices=("stats", "pysam"), help=argparse.SUPPRESS)
    parser.add_argument("--worker-threads", type=int, default=1, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        if args.worker_input is None or args.worker_mode is None:
            parser.error("worker input and mode are required")
        print(
            json.dumps(
                worker(args.worker_input, mode=args.worker_mode, threads=args.worker_threads)
            )
        )
        return
    if not args.input or args.output is None:
        parser.error("at least one --input and --output are required")
    if args.refresh_baselines is None and args.source_commit is None:
        parser.error("--source-commit is required for a new benchmark receipt")
    for source in args.input:
        assert_distinct_paths(source.resolve(strict=True), args.output)
    if args.refresh_baselines is not None:
        assert_distinct_paths(args.refresh_baselines.resolve(strict=True), args.output)
        receipt = json.loads(args.refresh_baselines.read_text(encoding="utf-8"))
        if not isinstance(receipt, dict):
            parser.error("benchmark receipt root must be an object")
        result = refresh_baselines(receipt, tuple(args.input))
    else:
        result = benchmark(
            tuple(args.input),
            repetitions=args.repetitions,
            threads=tuple(args.threads or (1,)),
            include_baseline=not args.no_baseline,
            source_commit=args.source_commit,
        )
    write_json_atomic(args.output, result)


if __name__ == "__main__":
    main()
