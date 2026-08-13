from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vcf_sv_stats.cli import app
from vcf_sv_stats.engine import discrepancies
from vcf_sv_stats.exceptions import InputError, OutputError, ValidationFailure
from vcf_sv_stats.models import OperationRequest
from vcf_sv_stats.normalize import normalize
from vcf_sv_stats.schemas import validate_artifact
from vcf_sv_stats.serialization import file_sha256
from vcf_sv_stats.sources import compare_sources, load_source_manifest

runner = CliRunner()


def _write_source(path: Path) -> Path:
    path.write_text(
        "\n".join(
            (
                "##fileformat=VCFv4.3",
                "##source=Manta_1.6.0",
                "##contig=<ID=chr1,length=1000000>",
                '##ALT=<ID=DEL,Description="Deletion">',
                '##ALT=<ID=DUP,Description="Duplication">',
                '##INFO=<ID=END,Number=1,Type=Integer,Description="End">',
                '##INFO=<ID=SVTYPE,Number=1,Type=String,Description="Type">',
                '##INFO=<ID=SVLEN,Number=A,Type=Integer,Description="Length">',
                '##INFO=<ID=MATEID,Number=.,Type=String,Description="Mate">',
                '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">',
                "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tHG002",
                "chr1\t100\tsrc-del\tN\t<DEL>\t50\tPASS\tEND=199;SVTYPE=DEL;SVLEN=-100\tGT\t0/1",
                "chr1\t300\tsrc-a\tN\tN]chr1:500]\t40\tPASS\tSVTYPE=BND;MATEID=src-b\tGT\t0/1",
                "chr1\t500\tsrc-b\tN\tN]chr1:300]\t40\tPASS\tSVTYPE=BND;MATEID=src-a\tGT\t0/1",
                "chr1\t700\tsrc-amb\tA\tATTT\t30\tPASS\tSVTYPE=INS;SVLEN=3\tGT\t0/1",
                "chr1\t900\tsrc-missing\tN\t<DUP>\t30\tPASS\tEND=999;SVTYPE=DUP;SVLEN=100\tGT\t0/1",
                "",
            )
        ),
        encoding="utf-8",
    )
    return path


def _write_combined(path: Path) -> Path:
    path.write_text(
        "\n".join(
            (
                "##fileformat=VCFv4.3",
                "##source=neutral-merger",
                "##contig=<ID=chr1,length=1000000>",
                '##ALT=<ID=DEL,Description="Deletion">',
                '##INFO=<ID=END,Number=1,Type=Integer,Description="End">',
                '##INFO=<ID=SVTYPE,Number=1,Type=String,Description="Type">',
                '##INFO=<ID=SVLEN,Number=A,Type=Integer,Description="Length">',
                '##INFO=<ID=SOURCE_IDS,Number=.,Type=String,Description="Source IDs">',
                '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">',
                "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tHG002",
                "chr1\t100\tmerged-del\tN\t<DEL>\t50\tPASS\tEND=199;SVTYPE=DEL;SVLEN=-100;SOURCE_IDS=src-del\tGT\t0/1",
                "chr1\t300\tmerged-a\tN\tN]chr1:500]\t40\tPASS\tSVTYPE=BND\tGT\t0/1",
                "chr1\t500\tmerged-b\tN\tN]chr1:300]\t40\tPASS\tSVTYPE=BND\tGT\t0/1",
                "chr1\t700\tmerged-amb-a\tA\tATTT\t30\tPASS\tSVTYPE=INS;SVLEN=3\tGT\t0/1",
                "chr1\t700\tmerged-amb-b\tA\tATTT\t30\tPASS\tSVTYPE=INS;SVLEN=3\tGT\t0/1",
                "",
            )
        ),
        encoding="utf-8",
    )
    return path


def _write_manifest(path: Path, combined: Path, source: Path) -> Path:
    value = {
        "schema_name": "vcf-sv-stats.source-manifest",
        "schema_version": "1.0.0",
        "combined_sha256": file_sha256(combined),
        "sources": [
            {
                "producer_label": "manta",
                "path": source.name,
                "display_name": source.name,
                "sha256": file_sha256(source),
                "artifact_role": "caller_native",
                "adapter_id": "urn:vcf-sv-stats:adapter:manta:1",
                "record_namespace": "manta-source",
                "merger_provenance": {
                    "support_ordinal": 0,
                    "source_id_fields": ["SOURCE_IDS"],
                    "relationship_fields": ["MATEID", "EVENT"],
                },
            }
        ],
    }
    validate_artifact("source-manifest", value)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_digest_bound_source_comparison_is_conservative_and_deterministic(
    tmp_path: Path,
) -> None:
    source = _write_source(tmp_path / "source.vcf")
    combined = _write_combined(tmp_path / "combined.vcf")
    manifest = _write_manifest(tmp_path / "sources.json", combined, source)

    first, evidence = compare_sources(combined, manifest)
    second, second_evidence = compare_sources(combined, manifest)

    assert first == second
    assert evidence == second_evidence
    assert evidence["status_counts"] == {
        "ambiguous": 1,
        "not_found": 1,
        "not_preserved": 2,
        "preserved": 1,
    }
    assert all(item["safe_reinsertion"] is False for item in first)
    assert all("src-" not in json.dumps(item) for item in first)
    bnd = [item for item in first if item["source_relationship_available"]]
    assert len(bnd) == 2
    assert all(item["merged_relationship_preserved"] is False for item in bnd)


@pytest.mark.parametrize("output_format", ["json", "jsonl", "tsv"])
def test_source_comparisons_are_integrated_in_every_discrepancy_format(
    tmp_path: Path, output_format: str
) -> None:
    source = _write_source(tmp_path / "source.vcf")
    combined = _write_combined(tmp_path / "combined.vcf")
    manifest = _write_manifest(tmp_path / "sources.json", combined, source)
    output = tmp_path / f"report.{output_format}"

    result = discrepancies(
        OperationRequest(combined, source_manifest=manifest),
        output=output,
        output_format=output_format,
    )

    assert len(result.source_comparisons) == 5
    assert result.source_evidence is not None
    assert result.source_evidence["comparison_count"] == 5
    if output_format == "json":
        payload = json.loads(output.read_text(encoding="utf-8"))
        validate_artifact("discrepancies", payload)
        assert len(payload["source_comparisons"]) == 5
    else:
        assert len(output.read_text(encoding="utf-8").splitlines()) >= 5


def test_source_manifest_rejects_changed_digest_and_input_alias(tmp_path: Path) -> None:
    source = _write_source(tmp_path / "source.vcf")
    combined = _write_combined(tmp_path / "combined.vcf")
    manifest = _write_manifest(tmp_path / "sources.json", combined, source)
    value = json.loads(manifest.read_text(encoding="utf-8"))
    value["combined_sha256"] = "0" * 64
    manifest.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(ValidationFailure, match="combined-artifact digest"):
        load_source_manifest(manifest, combined_path=combined)

    manifest = _write_manifest(tmp_path / "alias-sources.json", combined, source)
    value = json.loads(manifest.read_text(encoding="utf-8"))
    value["sources"][0]["path"] = combined.name
    value["sources"][0]["display_name"] = combined.name
    value["sources"][0]["sha256"] = file_sha256(combined)
    value["sources"][0]["adapter_id"] = "generic"
    manifest.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValidationFailure, match="must not alias"):
        load_source_manifest(manifest, combined_path=combined)


def test_source_manifest_cli_and_fixture_relative_golden() -> None:
    root = Path(__file__).parents[1]
    combined = root / "test_data/vcf/trussv.merged.hg002.subset.vcf.gz"
    manifest = root / "test_data/source_manifests/trussv-manta.source-manifest.json"
    expected = json.loads(
        (root / "test_data/expected/trussv-manta.source-comparison.expected.json").read_text(
            encoding="utf-8"
        )
    )
    comparisons, evidence = compare_sources(combined, manifest)
    dimensions = {
        key: sum(int(item["dimensions"][key]) for item in comparisons)
        for key in ("allele", "endpoint", "record_id", "relationships")
    }
    assert evidence["comparison_count"] == expected["comparison_count"]
    assert evidence["status_counts"] == expected["status_counts"]
    assert evidence["source_order"] == expected["source_order"]
    assert dimensions == expected["preserved_dimension_counts"]
    assert evidence["safe_reinsertion_proposed"] is False

    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            [
                "--json",
                "discrepancies",
                str(combined),
                "--source-manifest",
                str(manifest),
                "--output",
                "comparison.json",
            ],
        )
        assert result.exit_code == 0, result.stdout
        payload = json.loads(Path("comparison.json").read_text(encoding="utf-8"))
        assert payload["source_evidence"]["status_counts"] == expected["status_counts"]


def test_source_manifest_rejects_remote_adapter_order_and_file_aliases(
    tmp_path: Path,
) -> None:
    source = _write_source(tmp_path / "source.vcf")
    combined = _write_combined(tmp_path / "combined.vcf")
    manifest = _write_manifest(tmp_path / "sources.json", combined, source)
    original = json.loads(manifest.read_text(encoding="utf-8"))

    remote = json.loads(json.dumps(original))
    remote["sources"][0]["path"] = "https://example.invalid/source.vcf"
    manifest.write_text(json.dumps(remote), encoding="utf-8")
    with pytest.raises(InputError, match="local paths only"):
        load_source_manifest(manifest, combined_path=combined)

    wrong_adapter = json.loads(json.dumps(original))
    wrong_adapter["sources"][0]["adapter_id"] = "urn:vcf-sv-stats:adapter:tiddit:1"
    manifest.write_text(json.dumps(wrong_adapter), encoding="utf-8")
    with pytest.raises(ValidationFailure, match="adapter does not match"):
        load_source_manifest(manifest, combined_path=combined)

    wrong_order = json.loads(json.dumps(original))
    wrong_order["sources"][0]["merger_provenance"]["support_ordinal"] = 1
    manifest.write_text(json.dumps(wrong_order), encoding="utf-8")
    with pytest.raises(ValidationFailure, match="support ordinals"):
        load_source_manifest(manifest, combined_path=combined)

    second = tmp_path / "source-hardlink.vcf"
    os.link(source, second)
    duplicate_file = json.loads(json.dumps(original))
    duplicate_file["sources"].append(
        {
            **duplicate_file["sources"][0],
            "producer_label": "manta-second",
            "path": second.name,
            "display_name": second.name,
            "record_namespace": "manta-source-second",
            "merger_provenance": {
                **duplicate_file["sources"][0]["merger_provenance"],
                "support_ordinal": 1,
            },
        }
    )
    manifest.write_text(json.dumps(duplicate_file), encoding="utf-8")
    with pytest.raises(ValidationFailure, match="must not alias"):
        load_source_manifest(manifest, combined_path=combined)

    source_bcf_alias = tmp_path / "source-alias.bcf"
    os.link(source, source_bcf_alias)
    output_alias = json.loads(json.dumps(original))
    output_alias["sources"][0]["path"] = source_bcf_alias.name
    output_alias["sources"][0]["display_name"] = source_bcf_alias.name
    manifest.write_text(json.dumps(output_alias), encoding="utf-8")
    with pytest.raises(OutputError, match="aliases a source-manifest input"):
        normalize(
            OperationRequest(combined, source_manifest=manifest),
            source_bcf_alias,
        )


def test_unsafe_merged_comparison_blocks_canonical_rewrite(tmp_path: Path) -> None:
    source = _write_source(tmp_path / "source.vcf")
    combined = _write_combined(tmp_path / "combined.vcf")
    text = combined.read_text(encoding="utf-8")
    text = text.replace("VCFv4.3", "VCFv4.5")
    text = text.replace("##source=neutral-merger", "##source=Jasmine_1.1.5")
    text = text.replace(
        '##INFO=<ID=SVLEN,Number=A,Type=Integer,Description="Length">',
        '##INFO=<ID=SVLEN,Number=A,Type=Integer,Description="Length">\n'
        '##INFO=<ID=SVCLAIM,Number=A,Type=String,Description="Claim">',
    )
    text = text.replace("SVLEN=-100;SOURCE_IDS", "SVLEN=100;SVCLAIM=D;SOURCE_IDS")
    text = text.replace("SVTYPE=INS;SVLEN=3", "SVTYPE=INS")
    text = text.replace("END=199", "END=200")
    combined.write_text(text, encoding="utf-8")
    manifest = _write_manifest(tmp_path / "sources.json", combined, source)
    assessment = tmp_path / "assessment.json"

    with pytest.raises(ValidationFailure, match="source comparison"):
        normalize(
            OperationRequest(combined, source_manifest=manifest),
            tmp_path / "unsafe.vcf.gz",
            profile="canonical",
            assessment_output=assessment,
        )
    payload = json.loads(assessment.read_text(encoding="utf-8"))
    assert "VSS-NORMALIZATION-SOURCE-COMPARISON-UNSAFE" in {
        item["code"] for item in payload["diagnostics"]
    }
