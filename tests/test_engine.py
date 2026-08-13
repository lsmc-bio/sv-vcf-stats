from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from conftest import write_vcf

from vcf_sv_stats.engine import discrepancies, inspect, stats, validate
from vcf_sv_stats.exceptions import InputError
from vcf_sv_stats.io import input_metadata
from vcf_sv_stats.models import OperationRequest
from vcf_sv_stats.schemas import load_schema, validate_artifact
from vcf_sv_stats.serialization import file_sha256


def test_inspection_statistics_and_determinism(valid_vcf: Path) -> None:
    request = OperationRequest(valid_vcf)
    inspection = inspect(request)
    first = stats(request)
    second = stats(request)

    assert inspection.callset == {
        "vcf_sample_ids": ["HG002"],
        "single_sample": True,
        "record_count": 4,
        "allele_count": 4,
    }
    assert inspection.detection.selected.producer == "Manta"
    assert first.summary == second.summary
    assert first.summary["statistics"]["alleles"]["types"] == {
        "BND": 2,
        "DEL": 1,
        "INS": 1,
    }
    assert first.summary["statistics"]["breakends"]["reciprocal_pairs"] == 1
    assert first.summary["reports"][0]["analysis_unit"]["status"] == "unresolved"
    validate_artifact("summary", first.summary)


def test_limited_inspection_marks_incomplete(valid_vcf: Path) -> None:
    result = inspect(OperationRequest(valid_vcf), max_records=2)
    assert result.complete is False
    assert result.callset["record_count"] == 2


def test_malformed_and_relationship_findings(tmp_path: Path) -> None:
    orphan = "chr1\t500\tbnd-a\tN\tN]chr1:700]\t40\tPASS\tSVTYPE=BND;MATEID=missing\tGT:CN\t0/1:2"
    duplicate = "chr1\t900\tdup-id\tN\t<DEL>\t40\tPASS\tEND=999;SVTYPE=DEL;SVLEN=-100\tGT:CN\t0/1:1"
    path = write_vcf(tmp_path / "invalid.vcf", records=(orphan, duplicate, duplicate))
    result = validate(OperationRequest(path))
    codes = {item.code for item in result.diagnostics}
    assert not result.valid
    assert {"VSS-BND-MATE-UNRESOLVED", "VSS-ID-DUPLICATE"} <= codes
    assert result.states["operation_safety_state"] == "blocked"

    report_path = tmp_path / "diagnostics.json"
    report = discrepancies(OperationRequest(path), output=report_path)
    assert report.report_path == report_path
    assert json.loads(report_path.read_text())["complete"] is True

    input_digest = file_sha256(path)
    jsonl_path = tmp_path / "diagnostics.jsonl"
    tsv_path = tmp_path / "diagnostics.tsv"
    jsonl = discrepancies(OperationRequest(path), output=jsonl_path, output_format="jsonl")
    tsv = discrepancies(OperationRequest(path), output=tsv_path, output_format="tsv")
    assert len(jsonl_path.read_text(encoding="utf-8").splitlines()) == sum(
        jsonl.counts.values()
    )
    assert len(tsv_path.read_text(encoding="utf-8").splitlines()) - 1 == sum(
        tsv.counts.values()
    )
    assert file_sha256(path) == input_digest


def test_remote_uri_and_unknown_schema_are_rejected() -> None:
    with pytest.raises(InputError, match="Remote input URIs"):
        inspect(OperationRequest("https://example.invalid/callset.vcf"))
    with pytest.raises(Exception, match="Unknown schema"):
        load_schema("not-a-schema")


def test_container_detection_and_uncompressed_size_gate(valid_vcf: Path, tmp_path: Path) -> None:
    import pysam

    compressed = tmp_path / "input.vcf.gz"
    pysam.tabix_compress(str(valid_vcf), str(compressed), force=True)
    bcf = Path("test_data/vcf/manta.native.hg002.subset.bcf")

    assert input_metadata(valid_vcf)["container"] == "vcf"
    assert input_metadata(compressed)["container"] == "vcf.gz"
    assert input_metadata(bcf)["container"] == "bcf"
    with pytest.raises(InputError, match="max_uncompressed_bytes"):
        inspect(OperationRequest(compressed, max_uncompressed_bytes=32))


def test_generic_vcf45_canonical_and_cnv_states(tmp_path: Path) -> None:
    from vcf_sv_stats.api.v1 import iter_canonical

    records = (
        "chr1\t100\t.\tN\t<CNV>\t.\t.\tEND=199;SVTYPE=CNV;SVLEN=100\tGT:CN\t0/1:1",
        "chr1\t300\t.\tN\t<CNV>\t30\tPASS\tEND=399;SVTYPE=CNV;SVLEN=100\tGT:CN\t1|1:3",
        "chr1\t400\t.\tN\t<CNV>\t30\tPASS\tEND=499;SVTYPE=CNV;SVLEN=100\tGT:CN\t0/0:2",
        "chr1\t500\tsingle\tN\tN.\t.\tPASS\tSVTYPE=BND\tGT:CN\t./.:.",
    )
    path = write_vcf(tmp_path / "generic.vcf", records=records, source="public-unknown")
    text = path.read_text().replace("VCFv4.3", "VCFv4.5")
    path.write_text(text)

    result = stats(OperationRequest(path))
    observations = tuple(iter_canonical(OperationRequest(path)))
    assert result.summary["callset"]["producer"]["producer"] == "unknown"
    assert result.summary["statistics"]["filters"]["missing"] == 1
    assert result.summary["statistics"]["copy_number"] == {
        "1": 1,
        "2": 1,
        "3": 1,
        "missing": 1,
    }
    assert result.summary["statistics"]["copy_number_interpretation"] == {
        "baseline_status": "unavailable",
        "reason": "no_explicit_baseline_context",
        "cnv_records_by_genotype_state": {"alternate": 2, "reference_segment": 1},
        "gain_loss_neutral_inference": "not_performed",
    }
    assert result.summary["statistics"]["genotypes"]["phased"] == 1
    assert result.summary["statistics"]["genotypes"]["ploidy:2"] == 4
    assert [item.normalized_type for item in observations] == [
        "CNV",
        "CNV",
        "CNV",
        "SINGLE_BND",
    ]
    assert observations[-1].representation == "single_breakend"


def test_generic_vcf45_sv_statistics_match_exact_scopes(tmp_path: Path) -> None:
    records = (
        "chr1\t100\tdel-1\tN\t<DEL>\t60\tPASS\tSVLEN=100;SVCLAIM=D\tGT:CN\t0/1:1",
        "chr1\t300\tins-1\tA\t" + "A" + "T" * 60
        + "\t50\tPASS\tSVLEN=60;SVCLAIM=J\tGT:CN\t1/1:3",
        "chr1\t500\tbnd-a\tN\tN]chr1:700]\t40\tPASS"
        "\tMATEID=bnd-b;EVENT=event-1;SVCLAIM=J\tGT:CN\t0/1:2",
        "chr1\t700\tbnd-b\tN\tN]chr1:500]\t.\tq10"
        "\tMATEID=bnd-a;EVENT=event-1;SVCLAIM=J\tGT:CN\t./.:.",
    )
    path = write_vcf(
        tmp_path / "generic-v45.vcf",
        records=records,
        source="public-unknown",
    )
    text = path.read_text(encoding="utf-8").replace("VCFv4.3", "VCFv4.5")
    text = text.replace(
        '##FORMAT=<ID=GT',
        '##INFO=<ID=SVCLAIM,Number=A,Type=String,Description="Claim">\n##FORMAT=<ID=GT',
    )
    path.write_text(text, encoding="utf-8")

    result = stats(OperationRequest(path))

    assert result.summary["callset"]["producer"]["producer"] == "unknown"
    assert result.summary["statistics"]["source_records"]["total"] == 4
    assert result.summary["statistics"]["alleles"] == {
        "total": 4,
        "types": {"BND": 2, "DEL": 1, "INS": 1},
    }
    assert result.summary["statistics"]["breakends"] == {
        "total": 2,
        "reciprocal_pairs": 1,
        "without_declared_mate": 0,
        "unresolved_mate_references": 0,
    }
    assert result.summary["statistics"]["events"] == {"resolved": 3}
    assert result.summary["statistics"]["filters"] == {
        "PASS": 3,
        "filtered_any": 1,
        "q10": 1,
    }
    assert result.diagnostics == ()


def test_regional_results_are_explicitly_partial(valid_vcf: Path, tmp_path: Path) -> None:
    with pytest.raises(InputError, match="requires an index"):
        stats(OperationRequest(valid_vcf, regions=("chr1:90-210",)))

    request = OperationRequest(
        valid_vcf,
        regions=("chr1:90-210",),
        regions_scan=True,
    )
    result = stats(request)
    assert result.summary["input"]["complete"] is False
    assert result.summary["input"]["regions"] == ["chr1:90-210"]
    assert result.summary["statistics"]["source_records"]["total"] == 1

    compressed = tmp_path / "indexed.vcf.gz"
    import pysam

    pysam.tabix_compress(str(valid_vcf), str(compressed), force=True)
    pysam.tabix_index(str(compressed), preset="vcf", force=True)
    indexed = stats(OperationRequest(compressed, regions=("chr1:290-310",)))
    assert indexed.summary["statistics"]["source_records"]["total"] == 1


def test_thread_variation_preserves_canonical_payload(valid_vcf: Path) -> None:
    single = stats(OperationRequest(valid_vcf, threads=1)).summary
    maximum = stats(OperationRequest(valid_vcf, threads=max(1, os.cpu_count() or 1))).summary

    assert maximum == single
