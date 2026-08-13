from __future__ import annotations

from pathlib import Path

import pytest

from tools.benchmark_streaming import benchmark
from vcf_sv_stats.exceptions import UsageError


def test_streaming_benchmark_uses_path_safe_deterministic_measurements(
    valid_vcf: Path,
) -> None:
    result = benchmark((valid_vcf,), repetitions=2)

    measurement = result["inputs"][0]
    assert measurement["input_name"] == valid_vcf.name
    assert measurement["deterministic_payload"] is True
    assert len(measurement["repetitions"]) == 2
    assert {run["records"] for run in measurement["repetitions"]} == {4}
    assert all(run["process_peak_rss_bytes"] > 0 for run in measurement["repetitions"])


def test_streaming_benchmark_requires_positive_repetitions(valid_vcf: Path) -> None:
    with pytest.raises(UsageError, match="positive"):
        benchmark((valid_vcf,), repetitions=0)
