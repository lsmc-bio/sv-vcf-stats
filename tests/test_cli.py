from __future__ import annotations

import json
from pathlib import Path

from cli_core_yo.conformance import (
    assert_exit_code,
    assert_json_output,
    assert_no_ansi,
    assert_stdout_only,
    invoke,
    stdout_text,
)
from conftest import write_vcf
from typer.testing import CliRunner

from vcf_sv_stats.cli import app

runner = CliRunner()


def test_help_and_registry_are_exposed() -> None:
    help_result = runner.invoke(app, ["--help"])
    assert help_result.exit_code == 0
    for command in ("inspect", "validate", "discrepancies", "normalize", "stats", "run"):
        assert command in help_result.stdout

    registry = runner.invoke(app, ["--json", "adapters", "list"])
    assert registry.exit_code == 0
    assert any(item["producer"] == "Manta" for item in json.loads(registry.stdout))


def test_stats_json_and_validation_exit(valid_vcf: Path) -> None:
    result = runner.invoke(app, ["--json", "stats", str(valid_vcf)])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["content_signature"] == "vcf-sv-stats:summary:1"


def test_library_failure_does_not_exit_process() -> None:
    from vcf_sv_stats.api.v1 import inspect
    from vcf_sv_stats.exceptions import InputError
    from vcf_sv_stats.models import OperationRequest

    try:
        inspect(OperationRequest("missing.vcf"))
    except InputError:
        pass
    else:
        raise AssertionError("Expected a structured library exception")


def test_cli_core_conformance_contract() -> None:
    result = invoke(app, ["--json", "--no-color", "adapters", "list"])
    assert_exit_code(result, 0)
    assert isinstance(assert_json_output(result), list)
    assert_stdout_only(result)
    assert_no_ansi(stdout_text(result))

    usage = invoke(app, ["stats"])
    assert_exit_code(usage, 2)
    assert_no_ansi(stdout_text(usage))


def test_discrepancy_fail_on_publishes_before_exit(tmp_path: Path) -> None:
    output_path = tmp_path / "diagnostics.jsonl"
    duplicate = "chr1\t900\tdup-id\tN\t<DEL>\t40\tPASS\tEND=999;SVTYPE=DEL;SVLEN=-100\tGT:CN\t0/1:1"
    input_path = write_vcf(tmp_path / "invalid.vcf", records=(duplicate, duplicate))

    result = runner.invoke(
        app,
        [
            "--json",
            "discrepancies",
            str(input_path),
            "--output",
            str(output_path),
            "--format",
            "jsonl",
            "--fail-on",
            "error",
        ],
    )

    assert result.exit_code == 1
    assert output_path.is_file()
    assert output_path.read_text(encoding="utf-8").strip()
