"""`cli-core-yo` command registry and CLI boundary."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from importlib.metadata import version
from pathlib import Path
from typing import Annotated, Any, Literal, cast

import pysam
import typer
from cli_core_yo import output
from cli_core_yo.app import create_app, run
from cli_core_yo.registry import CommandRegistry
from cli_core_yo.runtime import get_context
from cli_core_yo.spec import (
    CliSpec,
    CommandPolicy,
    ConfigSpec,
    OutputSpec,
    PluginSpec,
    PolicySpec,
    XdgSpec,
)

from . import __version__
from .adapters import get_adapter, list_adapters, registry_as_dict
from .config import load_config, validate_config_text
from .diagnostics import explain
from .engine import discrepancies, inspect, stats, validate
from .exceptions import VcfSvStatsError
from .models import OperationRequest
from .normalize import normalize, run_bundle
from .reference import REFERENCE_PROFILE, fetch_reference
from .schemas import SCHEMA_NAMES, load_schema
from .serialization import write_json_atomic


def _info_hook() -> list[tuple[str, str]]:
    return [
        ("vcf-sv-stats", __version__),
        ("cli-core-yo", version("cli-core-yo")),
        ("pysam", version("pysam")),
        ("HTSlib", str(vars(pysam)["__samtools_version__"])),
        ("summary schema", "1.0.0"),
        ("adapter registry", "1"),
    ]


CLI_SPEC = CliSpec(
    prog_name="vcf-sv-stats",
    app_display_name="vcf-sv-stats",
    dist_name="vcf-sv-stats",
    root_help="Inspect, validate, summarize, and safely normalize SV/CNV VCF and BCF callsets.",
    xdg=XdgSpec(app_dir_name="vcf-sv-stats"),
    policy=PolicySpec(profile="platform-v2"),
    config=ConfigSpec(
        xdg_relative_path="config.yaml",
        template_resource=("vcf_sv_stats", "data/default-config.yaml"),
        validator=validate_config_text,
    ),
    runtime=None,
    output=OutputSpec(support_json=True, support_no_color_flag=True),
    plugins=PluginSpec(explicit=["vcf_sv_stats.cli.register_commands"]),
    info_hooks=[_info_hook],
)


def _emit(value: Any, *, human: str | None = None) -> None:
    if get_context().json_mode:
        output.emit_json(value)
    elif human is not None:
        output.print_text(human)
    else:
        output.print_text(json.dumps(value, indent=2, sort_keys=True))


def _fail(exc: VcfSvStatsError) -> None:
    if get_context().json_mode:
        output.emit_error_json(exc.code, str(exc))
    else:
        output.error(str(exc))
    raise typer.Exit(code=1)


def _guard(operation: Callable[[], Any]) -> Any:
    try:
        return operation()
    except VcfSvStatsError as exc:
        _fail(exc)


def _effective_config() -> dict[str, Any]:
    context = get_context()
    config_path = context.config_path
    explicit_env = os.environ.get("VCF_SV_STATS_CONFIG")
    if explicit_env:
        config_path = Path(explicit_env)
    if config_path is not None and not config_path.exists():
        config_path = None
    return load_config(config_path)


def _request(
    input_path: str,
    adapter: str | None,
    accept_untested_producer_version: bool,
    identity_context: Path | None,
    reference: Path | None,
    mode: str | None,
    threads: int | None,
    temp_dir: Path | None,
    regions: list[str] | None = None,
    regions_scan: bool = False,
) -> OperationRequest:
    config = _effective_config()
    effective_threads = config["io"]["threads"] if threads is None else threads
    if effective_threads < 1 or effective_threads > (os.cpu_count() or 1):
        raise typer.BadParameter("threads must be between 1 and the logical CPU count")
    effective_mode = mode or str(config["validation"]["mode"])
    if effective_mode not in {"compatible", "standard", "strict", "pedantic"}:
        raise typer.BadParameter("mode must be compatible, standard, strict, or pedantic")
    validation_mode = cast(Literal["compatible", "standard", "strict", "pedantic"], effective_mode)
    return OperationRequest(
        input_path=input_path,
        adapter_id=adapter,
        accept_untested_producer_version=accept_untested_producer_version,
        identity_context=identity_context,
        reference=reference,
        mode=validation_mode,
        threads=effective_threads,
        temp_dir=temp_dir or config["io"]["temp_dir"],
        max_input_bytes=config["io"]["max_input_bytes"],
        max_uncompressed_bytes=config["io"]["max_uncompressed_bytes"],
        regions=tuple(regions or ()),
        regions_scan=regions_scan,
    )


InputArg = Annotated[str, typer.Argument(help="Local VCF/BCF path or '-' for standard input.")]
AdapterOpt = Annotated[str | None, typer.Option("--adapter", help="Explicit adapter URN.")]
UntestedOpt = Annotated[
    bool,
    typer.Option("--accept-untested-producer-version", help="Allow provisional interpretation."),
]
IdentityOpt = Annotated[
    Path | None, typer.Option("--identity-context", exists=True, dir_okay=False)
]
ReferenceOpt = Annotated[Path | None, typer.Option("--reference", exists=True, dir_okay=False)]
ModeOpt = Annotated[
    str | None,
    typer.Option("--mode", help="Validation mode: compatible, standard, strict, or pedantic."),
]
ThreadsOpt = Annotated[int | None, typer.Option("--threads", min=1)]
TempOpt = Annotated[Path | None, typer.Option("--temp-dir", exists=True, file_okay=False)]
RegionsOpt = Annotated[list[str] | None, typer.Option("--regions", help="Restrict by region.")]
RegionsScanOpt = Annotated[
    bool,
    typer.Option("--regions-scan", help="Permit a full scan when regional access lacks an index."),
]


def inspect_command(
    input_path: InputArg,
    adapter: AdapterOpt = None,
    accept_untested_producer_version: UntestedOpt = False,
    identity_context: IdentityOpt = None,
    reference: ReferenceOpt = None,
    mode: ModeOpt = "compatible",
    threads: ThreadsOpt = None,
    temp_dir: TempOpt = None,
    regions: RegionsOpt = None,
    regions_scan: RegionsScanOpt = False,
    max_records: Annotated[int | None, typer.Option("--max-records", min=1)] = None,
) -> None:
    def operation() -> None:
        result = inspect(
            _request(
                input_path,
                adapter,
                accept_untested_producer_version,
                identity_context,
                reference,
                mode,
                threads,
                temp_dir,
                regions,
                regions_scan,
            ),
            max_records=max_records,
        )
        _emit(result.as_dict())

    _guard(operation)


def validate_command(
    input_path: InputArg,
    adapter: AdapterOpt = None,
    accept_untested_producer_version: UntestedOpt = False,
    identity_context: IdentityOpt = None,
    reference: ReferenceOpt = None,
    mode: ModeOpt = "standard",
    threads: ThreadsOpt = None,
    temp_dir: TempOpt = None,
    regions: RegionsOpt = None,
    regions_scan: RegionsScanOpt = False,
    diagnostics_output: Annotated[Path | None, typer.Option("--diagnostics-output")] = None,
    diagnostics_format: Annotated[str, typer.Option("--diagnostics-format")] = "jsonl",
) -> None:
    def operation() -> None:
        request = _request(
            input_path,
            adapter,
            accept_untested_producer_version,
            identity_context,
            reference,
            mode,
            threads,
            temp_dir,
            regions,
            regions_scan,
        )
        result = validate(request)
        if diagnostics_output is not None:
            discrepancies(
                request,
                output=diagnostics_output,
                output_format=diagnostics_format,
            )
        _emit(result.as_dict())
        if not result.valid:
            raise typer.Exit(code=1)

    _guard(operation)


def discrepancies_command(
    input_path: InputArg,
    output_path: Annotated[Path, typer.Option("--output")],
    adapter: AdapterOpt = None,
    accept_untested_producer_version: UntestedOpt = False,
    identity_context: IdentityOpt = None,
    reference: ReferenceOpt = None,
    mode: ModeOpt = "standard",
    threads: ThreadsOpt = None,
    temp_dir: TempOpt = None,
    regions: RegionsOpt = None,
    regions_scan: RegionsScanOpt = False,
    output_format: Annotated[str, typer.Option("--format")] = "json",
    fail_on: Annotated[str, typer.Option("--fail-on")] = "never",
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    def operation() -> None:
        if fail_on not in {"never", "warning", "error"}:
            raise typer.BadParameter("fail-on must be never, warning, or error")
        result = discrepancies(
            _request(
                input_path,
                adapter,
                accept_untested_producer_version,
                identity_context,
                reference,
                mode,
                threads,
                temp_dir,
                regions,
                regions_scan,
            ),
            output=output_path,
            output_format=output_format,
            force=force,
        )
        _emit(result.as_dict(), human=f"Wrote {output_path}")
        if fail_on == "warning" and (
            result.counts.get("warning", 0) or result.counts.get("error", 0)
        ):
            raise typer.Exit(code=1)
        if fail_on == "error" and result.counts.get("error", 0):
            raise typer.Exit(code=1)

    _guard(operation)


def stats_command(
    input_path: InputArg,
    adapter: AdapterOpt = None,
    accept_untested_producer_version: UntestedOpt = False,
    identity_context: IdentityOpt = None,
    reference: ReferenceOpt = None,
    mode: ModeOpt = "compatible",
    threads: ThreadsOpt = None,
    temp_dir: TempOpt = None,
    regions: RegionsOpt = None,
    regions_scan: RegionsScanOpt = False,
    output_path: Annotated[Path | None, typer.Option("--output")] = None,
) -> None:
    def operation() -> None:
        result = stats(
            _request(
                input_path,
                adapter,
                accept_untested_producer_version,
                identity_context,
                reference,
                mode,
                threads,
                temp_dir,
                regions,
                regions_scan,
            )
        )
        if output_path is None:
            _emit(result.summary)
        else:
            write_json_atomic(output_path, result.summary)
            _emit(
                {"output": str(output_path), "payload_sha256": result.summary["payload_sha256"]},
                human=f"Wrote {output_path}",
            )

    _guard(operation)


def normalize_command(
    input_path: InputArg,
    output_path: Annotated[Path, typer.Option("--output")],
    adapter: AdapterOpt = None,
    accept_untested_producer_version: UntestedOpt = False,
    identity_context: IdentityOpt = None,
    reference: ReferenceOpt = None,
    mode: ModeOpt = "standard",
    threads: ThreadsOpt = None,
    temp_dir: TempOpt = None,
    profile: Annotated[str, typer.Option("--profile")] = "conservative",
    output_format: Annotated[str | None, typer.Option("--output-format")] = None,
    index_format: Annotated[str, typer.Option("--index-format")] = "auto",
    authorize_loss: Annotated[list[str] | None, typer.Option("--authorize-loss")] = None,
    assessment_output: Annotated[Path | None, typer.Option("--assessment-output")] = None,
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    def operation() -> None:
        request = _request(
            input_path,
            adapter,
            accept_untested_producer_version,
            identity_context,
            reference,
            mode,
            threads,
            temp_dir,
        )
        if get_context().dry_run:
            validation_result = validate(request)
            _emit(
                {
                    "status": "planned",
                    "output": str(output_path),
                    "profile": profile,
                    "validation_valid": validation_result.valid,
                }
            )
            return
        normalization_result = normalize(
            request,
            output_path,
            profile=profile,
            output_format=output_format,
            index_format=index_format,
            authorize_loss=tuple(authorize_loss or ()),
            assessment_output=assessment_output,
            force=force,
        )
        _emit(
            normalization_result.as_dict(),
            human=f"Published {normalization_result.output_path}",
        )

    _guard(operation)


def run_command(
    input_path: InputArg,
    output_dir: Annotated[Path, typer.Option("--output-dir")],
    adapter: AdapterOpt = None,
    accept_untested_producer_version: UntestedOpt = False,
    identity_context: IdentityOpt = None,
    reference: ReferenceOpt = None,
    mode: ModeOpt = "standard",
    threads: ThreadsOpt = None,
    temp_dir: TempOpt = None,
    include_normalized: Annotated[bool, typer.Option("--normalize")] = False,
    profile: Annotated[str, typer.Option("--profile")] = "conservative",
) -> None:
    def operation() -> None:
        request = _request(
            input_path,
            adapter,
            accept_untested_producer_version,
            identity_context,
            reference,
            mode,
            threads,
            temp_dir,
        )
        if get_context().dry_run:
            validation = validate(request)
            _emit(
                {
                    "status": "planned",
                    "output_dir": str(output_dir),
                    "normalize": include_normalized,
                    "validation_valid": validation.valid,
                }
            )
            return
        result = run_bundle(
            request,
            output_dir,
            include_normalized=include_normalized,
            profile=profile,
        )
        _emit(result.as_dict(), human=f"Published {result.output_dir}")

    _guard(operation)


def adapters_list_command(
    status: Annotated[str | None, typer.Option("--status")] = None,
) -> None:
    _guard(lambda: _emit(registry_as_dict(list_adapters(status=status))))


def adapters_show_command(adapter_id: Annotated[str, typer.Argument()]) -> None:
    _guard(lambda: _emit(get_adapter(adapter_id).as_dict()))


def adapters_detect_command(
    input_path: InputArg,
    all_candidates: Annotated[bool, typer.Option("--all-candidates")] = False,
) -> None:
    def operation() -> None:
        result = inspect(OperationRequest(input_path=input_path), max_records=1)
        value = result.detection.as_dict()
        if not all_candidates:
            value["candidates"] = [
                item for item in value["candidates"] if float(item["score"]) >= 0.1
            ]
        _emit(value)

    _guard(operation)


def schema_show_command(name: Annotated[str | None, typer.Argument()] = None) -> None:
    def operation() -> None:
        if name is None:
            _emit({"schemas": list(SCHEMA_NAMES), "schema_version": "1.0.0"})
        else:
            _emit(load_schema(name))

    _guard(operation)


def diagnostics_explain_command(code: Annotated[str, typer.Argument()]) -> None:
    _guard(lambda: _emit(explain(code)))


def reference_fetch_command(
    assembly: Annotated[str, typer.Option("--assembly")],
    distribution: Annotated[str, typer.Option("--distribution")],
    cache_dir: Annotated[Path | None, typer.Option("--cache-dir")] = None,
    yes: Annotated[bool, typer.Option("--yes")] = False,
    offline: Annotated[bool, typer.Option("--offline")] = False,
) -> None:
    def operation() -> None:
        effective_cache = cache_dir or Path(
            os.environ.get(
                "VCF_SV_STATS_CACHE_DIR", Path.home() / ".cache" / "vcf-sv-stats" / "references"
            )
        )
        confirmed = yes
        if not offline and not confirmed and sys.stdin.isatty():
            output.print_text(
                f"Source: {REFERENCE_PROFILE['url']}\n"
                f"Expected bytes: {REFERENCE_PROFILE['expected_size']}\n"
                f"Terms: {REFERENCE_PROFILE['terms_url']}"
            )
            confirmed = typer.confirm("Download this pinned reference?")
        value = fetch_reference(
            assembly=assembly,
            distribution=distribution,
            cache_dir=effective_cache,
            yes=confirmed,
            offline=offline,
            dry_run=get_context().dry_run,
        )
        _emit(value)

    _guard(operation)


READ_ONLY = CommandPolicy(
    supports_json=True,
    runtime_guard="exempt",
    long_running=True,
)
REPORTING = CommandPolicy(
    mutates_state=True,
    supports_json=True,
    runtime_guard="exempt",
    long_running=True,
)
MUTATING = CommandPolicy(
    mutates_state=True,
    supports_json=True,
    supports_dry_run=True,
    runtime_guard="required",
    long_running=True,
)
METADATA = CommandPolicy(supports_json=True, runtime_guard="exempt")


def register_commands(registry: CommandRegistry, _spec: CliSpec) -> None:
    registry.add_command(
        None, "inspect", inspect_command, help_text="Inspect a callset.", policy=READ_ONLY
    )
    registry.add_command(
        None, "validate", validate_command, help_text="Validate a callset.", policy=REPORTING
    )
    registry.add_command(
        None,
        "discrepancies",
        discrepancies_command,
        help_text="Write an exhaustive discrepancy report.",
        policy=REPORTING,
    )
    registry.add_command(
        None,
        "normalize",
        normalize_command,
        help_text="Write a safe normalized callset.",
        policy=MUTATING,
    )
    registry.add_command(
        None,
        "stats",
        stats_command,
        help_text="Calculate descriptive statistics.",
        policy=REPORTING,
    )
    registry.add_command(
        None, "run", run_command, help_text="Create a complete report bundle.", policy=MUTATING
    )
    registry.add_group("adapters", help_text="Inspect the built-in adapter registry.")
    registry.add_command(
        "adapters", "list", adapters_list_command, help_text="List adapters.", policy=METADATA
    )
    registry.add_command(
        "adapters", "show", adapters_show_command, help_text="Show an adapter.", policy=METADATA
    )
    registry.add_command(
        "adapters",
        "detect",
        adapters_detect_command,
        help_text="Detect producer evidence.",
        policy=READ_ONLY,
    )
    registry.add_group("schema", help_text="Inspect embedded JSON Schemas.")
    registry.add_command(
        "schema", "show", schema_show_command, help_text="Show a schema.", policy=METADATA
    )
    registry.add_group("diagnostics", help_text="Inspect diagnostic definitions.")
    registry.add_command(
        "diagnostics",
        "explain",
        diagnostics_explain_command,
        help_text="Explain a code.",
        policy=METADATA,
    )
    registry.add_group("reference", help_text="Manage explicitly requested public references.")
    registry.add_command(
        "reference",
        "fetch",
        reference_fetch_command,
        help_text="Fetch or verify a pinned reference.",
        policy=MUTATING,
    )


app = create_app(CLI_SPEC)


def main() -> None:
    raise SystemExit(run(CLI_SPEC))
