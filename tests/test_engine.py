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
from vcf_sv_stats.vcf45 import parse_genotype_layout


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
        + "\t50\tPASS\tSVCLAIM=.\tGT:CN\t1/1:3",
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
    text = text.replace("ID=MATEID,Number=.", "ID=MATEID,Number=A")
    text = text.replace("ID=EVENT,Number=1", "ID=EVENT,Number=A")
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


def _write_finalized_v45_matrix(path: Path, *, version: str = "VCFv4.5") -> Path:
    path.write_text(
        "\n".join(
            (
                f"##fileformat={version}",
                "##contig=<ID=chr1,length=248956422>",
                '##ALT=<ID=DEL,Description="Deletion">',
                '##ALT=<ID=DUP,Description="Duplication">',
                '##INFO=<ID=END,Number=1,Type=Integer,Description="Deprecated end">',
                '##INFO=<ID=SVLEN,Number=A,Type=Integer,Description="Length">',
                '##INFO=<ID=SVCLAIM,Number=A,Type=String,Description="Claim">',
                '##INFO=<ID=EVENT,Number=A,Type=String,Description="Event">',
                '##INFO=<ID=EVENTTYPE,Number=A,Type=String,Description="Event type">',
                '##INFO=<ID=IG,Number=G,Type=Float,Description="Genotype vector">',
                '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">',
                '##FORMAT=<ID=LAA,Number=.,Type=Integer,Description="Local ALT indexes">',
                '##FORMAT=<ID=LAD,Number=LR,Type=Integer,Description="Local depths">',
                '##FORMAT=<ID=LEC,Number=LA,Type=Integer,Description="Local counts">',
                '##FORMAT=<ID=LPL,Number=LG,Type=Integer,Description="Local likelihoods">',
                '##FORMAT=<ID=FA,Number=A,Type=Integer,Description="ALT vector">',
                '##FORMAT=<ID=FR,Number=R,Type=Integer,Description="Allele vector">',
                '##FORMAT=<ID=FG,Number=G,Type=Integer,Description="Genotype vector">',
                '##FORMAT=<ID=PSL,Number=P,Type=String,Description="Phase sets">',
                '##FORMAT=<ID=PSO,Number=P,Type=Integer,Description="Phase ordinals">',
                '##FORMAT=<ID=PSQ,Number=P,Type=Integer,Description="Phase quality">',
                '##FORMAT=<ID=LEN,Number=1,Type=Integer,Description="Reference-block length">',
                "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tHG002",
                "chr1\t100\tmulti\tN\t<DEL>,<DUP>\t60\tPASS\t"
                "END=300;SVLEN=100,200;SVCLAIM=D,DJ;EVENT=event-del,event-dup;"
                "EVENTTYPE=DEL,DUP;IG=0,1,2,3,4,5\t"
                "GT:LAA:LAD:LEC:LPL:FA:FR:FG:PSL:PSO:PSQ\t"
                "1|2:1,2:30,10,20:4,6:0,1,2,3,4,5:7,8:9,10,11:"
                "12,13,14,15,16,17:.,phase-b:.,2:.,50",
                "chr1\t500\tblock\tA\t<NON_REF>\t.\tPASS\tEND=509\tGT:LEN\t0/0:10",
                "",
            )
        ),
        encoding="utf-8",
    )
    return path


def test_finalized_vcf45_construct_matrix_validates_exact_rules(tmp_path: Path) -> None:
    path = _write_finalized_v45_matrix(tmp_path / "finalized.vcf")

    result = validate(OperationRequest(path))

    assert result.valid
    assert result.diagnostics == ()
    summary = stats(OperationRequest(path)).summary
    assert summary["statistics"]["source_records"]["multiallelic_records"] == 1
    assert summary["statistics"]["alleles"]["types"] == {
        "DEL": 1,
        "DUP": 1,
        "NON_SV": 1,
    }


def test_finalized_vcf45_invalid_matrix_is_deterministic(tmp_path: Path) -> None:
    path = _write_finalized_v45_matrix(tmp_path / "invalid-finalized.vcf")
    text = path.read_text(encoding="utf-8")
    text = text.replace("END=300", "END=301")
    text = text.replace("SVLEN=100,200", "SVLEN=-100,200")
    text = text.replace("IG=0,1,2,3,4,5", "IG=0,1")
    text = text.replace("SVCLAIM=D,DJ", "SVCLAIM=X,D")
    text = text.replace("GT:LAA:LAD", "GT:LAD:LAA")
    text = text.replace("1|2:1,2:30,10,20", "1|2:30,10:1,1")
    text = text.replace("PSL:PSO:PSQ", "PS:PSL:PSO:PSQ")
    text = text.replace(
        "12,13,14,15,16,17:.,phase-b:.,2:.,50",
        "12,13,14,15,16,17:99:phase-a:1:40",
    )
    text = text.replace(
        '##FORMAT=<ID=PSL',
        '##FORMAT=<ID=PS,Number=1,Type=Integer,Description="Phase set">\n'
        '##FORMAT=<ID=PSL',
    )
    path.write_text(text, encoding="utf-8")

    first = validate(OperationRequest(path))
    second = validate(OperationRequest(path))
    codes = [item.code for item in first.diagnostics]

    assert first.diagnostics == second.diagnostics
    assert not first.valid
    assert {
        "VSS-CARDINALITY-INFO",
        "VSS-CARDINALITY-FORMAT",
        "VSS-LOCAL-ALLELE-INVALID",
        "VSS-LOCAL-ALLELE-ORDER",
        "VSS-PHASE-PS-PSL-CONFLICT",
        "VSS-V45-SVLEN-LEGACY-SIGN",
        "VSS-V45-SVCLAIM-INVALID",
        "VSS-V45-END-COMPUTED-MISMATCH",
    } <= set(codes)


@pytest.mark.parametrize("version", ["VCFv4.5-draft", "VCFv4.6", "VCFv5.0"])
def test_draft_and_future_vcf_versions_do_not_pass_as_finalized(
    tmp_path: Path, version: str
) -> None:
    path = _write_finalized_v45_matrix(tmp_path / "unsupported.vcf", version=version)

    result = validate(OperationRequest(path))

    assert not result.valid
    assert "VSS-VCF-VERSION-UNSUPPORTED-FINAL-OR-DRAFT" in {
        item.code for item in result.diagnostics
    }


def test_vcf45_prefix_phasing_is_parsed_exactly(tmp_path: Path) -> None:
    layout = parse_genotype_layout("|0|1/2")
    assert layout.alleles == (0, 1, 2)
    assert layout.separators == ("|", "|", "/")

    path = tmp_path / "prefix-phase.vcf"
    path.write_text(
        "\n".join(
            (
                "##fileformat=VCFv4.5",
                "##contig=<ID=chr1,length=1000>",
                '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">',
                '##FORMAT=<ID=PSL,Number=P,Type=String,Description="Phase sets">',
                "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tHG002",
                "chr1\t10\tphase\tA\tT\t.\tPASS\t.\tGT:PSL\t|0|1:phase-a,phase-b",
                "",
            )
        ),
        encoding="utf-8",
    )

    result = validate(OperationRequest(path))

    assert result.valid
    assert result.diagnostics == ()


def test_vcf45_symbolic_svlen_reference_and_local_allele_edges(
    tmp_path: Path,
) -> None:
    path = tmp_path / "v45-edges.vcf"
    path.write_text(
        "\n".join(
            (
                "##fileformat=VCFv4.5",
                "##contig=<ID=chr1,length=1000>",
                '##INFO=<ID=END,Number=1,Type=Integer,Description="End">',
                '##INFO=<ID=SVLEN,Number=A,Type=Integer,Description="Length">',
                '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">',
                '##FORMAT=<ID=LEN,Number=1,Type=Integer,Description="Block length">',
                '##FORMAT=<ID=LAA,Number=.,Type=Integer,Description="Local alleles">',
                '##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Depths">',
                '##FORMAT=<ID=LAD,Number=LR,Type=Integer,Description="Local depths">',
                "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tHG002",
                "chr1\t10\tlower\tA\t<del>\t.\tPASS\tSVLEN=10\tGT\t0/1",
                "chr1\t30\tsymbolic-bnd\tA\t<BND>\t.\tPASS\tSVLEN=.\tGT\t0/1",
                "chr1\t50\tsequence\tA\tAT\t.\tPASS\tSVLEN=1\tGT\t0/1",
                "chr1\t70\tlen\tA\tT\t.\tPASS\t.\tGT:LEN\t0/1:2",
                "chr1\t90\tblock\tA\t<*>\t.\tPASS\tEND=99\tGT:LAA\t0/0:.",
                "chr1\t120\tlocal\tA\tT,G\t.\tPASS\t.\tGT:LAA:AD:LAD\t2/2:1:10,20,30:10,99",
                "",
            )
        ),
        encoding="utf-8",
    )

    codes = {item.code for item in validate(OperationRequest(path)).diagnostics}

    assert {
        "VSS-LOCAL-ALLELE-EQUIVALENCE",
        "VSS-LOCAL-ALLELE-GT-CONFLICT",
        "VSS-V45-LEN-WITHOUT-REFERENCE-BLOCK",
        "VSS-V45-REFERENCE-BLOCK-LAA",
        "VSS-V45-SVLEN-NOT-APPLICABLE",
        "VSS-V45-SYMBOLIC-ALT-CASE",
        "VSS-V45-SYMBOLIC-BND-DISALLOWED",
    } <= codes


def test_vcf45_phase_set_cross_record_rules_are_disk_backed(tmp_path: Path) -> None:
    path = tmp_path / "v45-phase-edges.vcf"
    path.write_text(
        "\n".join(
            (
                "##fileformat=VCFv4.5",
                "##contig=<ID=chr1,length=1000>",
                '##ALT=<ID=DEL,Description="Deletion">',
                '##INFO=<ID=SVLEN,Number=A,Type=Integer,Description="Length">',
                '##INFO=<ID=SVCLAIM,Number=A,Type=String,Description="Claim">',
                '##INFO=<ID=MATEID,Number=A,Type=String,Description="Mate">',
                '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">',
                '##FORMAT=<ID=PSL,Number=P,Type=String,Description="Phase sets">',
                '##FORMAT=<ID=PSO,Number=P,Type=Integer,Description="Phase order">',
                '##FORMAT=<ID=PSQ,Number=P,Type=Integer,Description="Phase quality">',
                "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tHG002",
                "chr1\t10\tdel\tA\t<DEL>\t.\tPASS\tSVLEN=10;SVCLAIM=J\tGT:PSL\t0|1:.,phase-del",
                "chr1\t30\tb1\tA\tA]chr1:50]\t.\tPASS\tSVLEN=.;MATEID=b2\tGT:PSL:PSO\t0|1:.,phase-bnd:.,1",
                "chr1\t50\tb2\tA\tA]chr1:30]\t.\tPASS\tSVLEN=.;MATEID=b1\tGT:PSL:PSO\t0|1:.,phase-bnd:.,2",
                "chr1\t70\tplain\tA\tT\t.\tPASS\t.\tGT:PSL:PSO:PSQ\t0/1:phase-plain,.:1,.:20,.",
                "chr1\t80\torphan-phase-values\tA\tG\t.\tPASS\t.\tGT:PSL:PSO:PSQ\t0/1:.,.:1,.:20,.",
                "",
            )
        ),
        encoding="utf-8",
    )

    codes = {item.code for item in validate(OperationRequest(path)).diagnostics}

    assert {
        "VSS-PHASE-BREAKPOINT-MISMATCH",
        "VSS-PHASE-PSL-UNPHASED",
        "VSS-PHASE-PSO-REQUIRED",
        "VSS-PHASE-PSO-WITHOUT-PSL",
        "VSS-PHASE-PSQ-WITHOUT-PSL",
    } <= codes


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
