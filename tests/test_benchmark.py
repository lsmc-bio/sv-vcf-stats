from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from tools.benchmark_streaming import _assert_path_safe, benchmark, refresh_baselines
from vcf_sv_stats.exceptions import UsageError
from vcf_sv_stats.schemas import validate_artifact
from vcf_sv_stats.serialization import payload_sha256


def test_streaming_benchmark_uses_path_safe_deterministic_measurements(
    valid_vcf: Path,
) -> None:
    result = benchmark((valid_vcf,), repetitions=2)

    validate_artifact("streaming-benchmark", result)
    unsigned = deepcopy(result)
    assert unsigned.pop("receipt_sha256") == payload_sha256(unsigned)

    input_result = result["inputs"][0]
    assert input_result["input_name"] == valid_vcf.name
    assert input_result["deterministic_stats_payload"] is True
    stats_runs = [run for run in input_result["measurements"] if run["mode"] == "stats"]
    baseline_runs = [run for run in input_result["measurements"] if run["mode"] == "pysam"]
    assert len(stats_runs) == 2
    assert len(baseline_runs) == 1
    assert {run["records"] for run in stats_runs} == {4}
    assert all(run["process_peak_rss_bytes"] > 0 for run in stats_runs)
    assert stats_runs[0]["cache_state"] == "cold_process_uncontrolled_os_cache"
    assert stats_runs[1]["cache_state"] == "warm_process_uncontrolled_os_cache"


def test_streaming_benchmark_requires_positive_repetitions(valid_vcf: Path) -> None:
    with pytest.raises(UsageError, match="positive"):
        benchmark((valid_vcf,), repetitions=0)


def test_streaming_benchmark_rejects_path_bearing_receipts() -> None:
    with pytest.raises(UsageError, match="filesystem path"):
        _assert_path_safe({"unsafe": "/private/example.vcf.gz"})


def test_streaming_benchmark_refreshes_only_pinned_baselines(valid_vcf: Path) -> None:
    original = benchmark((valid_vcf,), repetitions=1)
    original_stats = [
        run for run in original["inputs"][0]["measurements"] if run["mode"] == "stats"
    ]
    refreshed = refresh_baselines(original, (valid_vcf,))
    refreshed_stats = [
        run for run in refreshed["inputs"][0]["measurements"] if run["mode"] == "stats"
    ]
    refreshed_baselines = [
        run for run in refreshed["inputs"][0]["measurements"] if run["mode"] == "pysam"
    ]
    assert refreshed_stats == original_stats
    assert len(refreshed_baselines) == 1
    unsigned = deepcopy(refreshed)
    assert unsigned.pop("receipt_sha256") == payload_sha256(unsigned)
