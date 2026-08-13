from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from urllib.parse import unquote

import pytest
from typer.testing import CliRunner

from vcf_sv_stats.adapters import list_adapters
from vcf_sv_stats.cli import app
from vcf_sv_stats.config import DEFAULT_CONFIG, load_config, validate_config_text
from vcf_sv_stats.engine import stats
from vcf_sv_stats.identity import load_identity_context
from vcf_sv_stats.models import OperationRequest

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
COMMAND_REFERENCE = ROOT / "docs/command-reference.md"
MANTA_FIXTURE = ROOT / "test_data/vcf/manta.native.hg002.subset.vcf.gz"
LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def _marked_block(path: Path, name: str) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(
        rf"<!-- {re.escape(name)}:start -->\s*(.*?)\s*<!-- {re.escape(name)}:end -->",
        text,
        flags=re.DOTALL,
    )
    assert match is not None, f"Missing documentation marker: {path}:{name}"
    return match.group(1)


def _heading_anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    headings = re.findall(
        r"^#{1,6}\s+(.+?)\s*$", path.read_text(encoding="utf-8"), re.MULTILINE
    )
    for heading in headings:
        without_markup = re.sub(r"[`*_~]", "", heading.casefold())
        anchor = re.sub(r"[^\w\- ]", "", without_markup)
        anchors.add(re.sub(r"\s+", "-", anchor.strip()))
    return anchors


def test_relative_markdown_links_resolve() -> None:
    documents = sorted((*ROOT.glob("*.md"), *(ROOT / "docs").rglob("*.md")))
    failures: list[str] = []

    for document in documents:
        for raw_target in LINK_PATTERN.findall(document.read_text(encoding="utf-8")):
            target = raw_target.strip().split()[0].strip("<>")
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if target.startswith("#"):
                resolved = document
                fragment = target[1:]
            else:
                path_part, separator, fragment = target.partition("#")
                resolved = document.parent / unquote(path_part)
                fragment = fragment if separator else ""
            if not resolved.exists():
                failures.append(f"{document.relative_to(ROOT)} -> {target}")
                continue
            if (
                fragment
                and resolved.suffix.casefold() == ".md"
                and unquote(fragment).casefold() not in _heading_anchors(resolved)
            ):
                failures.append(f"{document.relative_to(ROOT)} -> {target} (missing anchor)")

    assert failures == []


def test_readme_showcase_is_computed_from_fixture() -> None:
    summary = stats(OperationRequest(MANTA_FIXTURE)).summary
    statistics = summary["statistics"]
    computed = {
        "producer": summary["callset"]["producer"]["producer"],
        "records": statistics["source_records"]["total"],
        "alleles": statistics["alleles"]["total"],
        "events": statistics["events"]["resolved"],
        "breakends": statistics["breakends"],
        "types": statistics["alleles"]["types"],
    }
    expected = json.loads((ROOT / "docs/examples/manta-showcase.json").read_text())
    readme_block = _marked_block(README, "showcase-json")
    embedded = json.loads(re.sub(r"^```json\s*|\s*```$", "", readme_block.strip()))

    assert embedded == expected == computed


def test_identity_example_validates_and_resolves_hg002() -> None:
    context_path = ROOT / "docs/examples/identity-context.json"
    units = load_identity_context(context_path)
    assert len(units) == 1
    assert units[0].analysis_unit_id == "analysis-001"
    assert units[0].mapped_vcf_sample_ids == ("HG002",)

    report = stats(OperationRequest(MANTA_FIXTURE, identity_context=context_path)).summary[
        "reports"
    ][0]
    assert report["analysis_unit"] == {
        "status": "resolved",
        "analysis_unit_id": "analysis-001",
        "display_id": "HG002 demonstration",
        "algorithm_id": "manta-1.6.0",
        "external_identifiers": [{"namespace": "study", "value": "example-study"}],
    }
    assert report["mapped_vcf_sample_ids"] == ["HG002"]


def test_config_example_is_strict_and_matches_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "VCF_SV_STATS_THREADS",
        "VCF_SV_STATS_TMPDIR",
        "VCF_SV_STATS_CACHE_DIR",
    ):
        monkeypatch.delenv(name, raising=False)
    config_path = ROOT / "docs/examples/config.yaml"

    assert validate_config_text(config_path.read_text(encoding="utf-8")) == []
    assert load_config(config_path) == DEFAULT_CONFIG


def test_documented_command_catalog_has_executable_help() -> None:
    block = _marked_block(COMMAND_REFERENCE, "command-catalog")
    commands = re.findall(r"^\| `([^`]+)` \|", block, flags=re.MULTILINE)
    assert commands == [
        "inspect",
        "validate",
        "discrepancies",
        "stats",
        "normalize",
        "run",
        "adapters list",
        "adapters show",
        "adapters detect",
        "schema show",
        "diagnostics explain",
        "reference fetch",
        "config path",
        "config init",
        "config show",
        "config validate",
        "config edit",
        "config reset",
        "version",
        "info",
    ]

    runner = CliRunner()
    failures = []
    for command in commands:
        result = runner.invoke(app, [*command.split(), "--help"])
        if result.exit_code != 0:
            failures.append(command)
    assert failures == []


def test_documented_adapter_matrix_matches_registry() -> None:
    rows: dict[str, tuple[str, str, str, str]] = {}
    for line in _marked_block(COMMAND_REFERENCE, "adapter-matrix").splitlines():
        if not line.startswith("| `urn:"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
        adapter_id, producer, version, status, rewrite = cells
        rows[adapter_id] = (producer, version, status, rewrite)

    expected = {
        adapter.adapter_id: (
            adapter.producer,
            ", ".join(adapter.versions) if adapter.versions else "—",
            adapter.status,
            "yes" if adapter.rewrite_supported else "no",
        )
        for adapter in list_adapters()
    }
    assert rows == expected


def test_readme_corpus_and_dependency_claims_match_metadata() -> None:
    readme = README.read_text(encoding="utf-8")
    manifest = json.loads((ROOT / "test_data/manifest.json").read_text(encoding="utf-8"))
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert f"**{len(manifest['fixtures'])} deterministic source-derived fixtures**" in readme
    assert f"**{manifest['totals']['source_derived_records']:,} records**" in readme
    assert f"**{manifest['totals']['compressed_vcf_bytes']:,} compressed VCF bytes**" in readme
    assert project["requires-python"] == ">=3.11"
    assert "Python 3.11, 3.12, and 3.13 are tested." in readme
    for dependency in ("cli-core-yo==2.1.1", "pysam==0.24.0"):
        assert dependency in project["dependencies"]
        assert f"`{dependency}`" in readme


def test_every_emitted_diagnostic_is_explainable() -> None:
    source_root = ROOT / "src/vcf_sv_stats"
    emitted = {
        code
        for path in source_root.rglob("*.py")
        if path.name != "diagnostics.py"
        for code in re.findall(r'"(VSS-[A-Z0-9-]+)"', path.read_text(encoding="utf-8"))
    }
    from vcf_sv_stats.diagnostics import CATALOG

    assert emitted <= set(CATALOG)
