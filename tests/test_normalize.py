from __future__ import annotations

import gzip
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pysam
import pytest

from vcf_sv_stats.exceptions import OutputError, ValidationFailure
from vcf_sv_stats.models import OperationRequest
from vcf_sv_stats.normalize import normalize, run_bundle
from vcf_sv_stats.serialization import file_sha256


@pytest.mark.parametrize("suffix", [".vcf.gz", ".bcf"])
def test_normalization_digest_graph_and_semantic_parity(
    valid_vcf: Path, tmp_path: Path, suffix: str
) -> None:
    output = tmp_path / f"normalized{suffix}"
    input_digest = file_sha256(valid_vcf)
    result = normalize(OperationRequest(valid_vcf), output)

    assert all(
        path.is_file()
        for path in (
            result.output_path,
            result.index_path,
            result.manifest_path,
            result.receipt_path,
        )
    )
    assert result.output_sha256 == file_sha256(output)
    assert file_sha256(valid_vcf) == input_digest
    manifest = json.loads(result.manifest_path.read_text())
    receipt = json.loads(result.receipt_path.read_text())
    assert manifest["output"]["sha256"] == result.output_sha256
    assert manifest["index"]["sha256"] == result.index_sha256
    assert receipt["request_sha256"] == manifest["request_sha256"]
    assert receipt["manifest"]["sha256"] == result.manifest_sha256
    assert manifest["adapter"]["adapter_id"] == "urn:vcf-sv-stats:adapter:manta:1"
    assert manifest["cardinality"] == {
        "input_records": 4,
        "input_alleles": 4,
        "output_records": 4,
        "record_mappings": 4,
        "event_identifiers": 0,
    }
    assert manifest["reference"] == {"status": "not_provided"}
    assert manifest["schemas"]["manifest"] == (
        "urn:vcf-sv-stats:schema:transforms:1.0.0"
    )
    with pysam.VariantFile(str(output)) as variant:
        assert list(variant.header.samples) == ["HG002"]
        assert sum(1 for _ in variant) == 4
        assert "VCFSVSTATS1_REQUEST_SHA256" in str(variant.header)


def test_normalization_refuses_alias_and_unowned_overwrite(valid_vcf: Path, tmp_path: Path) -> None:
    alias = tmp_path / "input-alias.vcf.gz"
    alias.symlink_to(valid_vcf)
    with pytest.raises(OutputError, match="aliases"):
        normalize(OperationRequest(valid_vcf), alias)

    output = tmp_path / "existing.vcf.gz"
    output.write_bytes(b"not-owned")
    with pytest.raises(OutputError, match="already exists"):
        normalize(OperationRequest(valid_vcf), output)
    with pytest.raises(OutputError, match="complete prior owned"):
        normalize(OperationRequest(valid_vcf), output, force=True)


def test_alias_matrix_preserves_indexed_input_bytes(valid_vcf: Path, tmp_path: Path) -> None:
    compressed = tmp_path / "input.vcf.gz"
    pysam.tabix_compress(str(valid_vcf), str(compressed), force=True)
    pysam.tabix_index(str(compressed), preset="vcf", force=True)
    index = Path(str(compressed) + ".tbi")
    original = {compressed: file_sha256(compressed), index: file_sha256(index)}

    with pytest.raises(OutputError, match="aliases"):
        normalize(OperationRequest(compressed), compressed)

    hard_link = tmp_path / "hard-link.vcf.gz"
    os.link(compressed, hard_link)
    with pytest.raises(OutputError, match="aliases"):
        normalize(OperationRequest(compressed), hard_link, force=True)

    symlink = tmp_path / "symlink.vcf.gz"
    symlink.symlink_to(compressed)
    with pytest.raises(OutputError, match="aliases"):
        normalize(OperationRequest(compressed), symlink, force=True)

    assert {file_path: file_sha256(file_path) for file_path in original} == original


def test_force_never_removes_an_unrelated_directory(valid_vcf: Path, tmp_path: Path) -> None:
    output_directory = tmp_path / "unrelated.vcf.gz"
    output_directory.mkdir()
    marker = output_directory / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(OutputError, match="complete prior owned"):
        normalize(OperationRequest(valid_vcf), output_directory, force=True)

    assert marker.read_text(encoding="utf-8") == "keep"


def test_thread_variation_preserves_normalized_bytes(valid_vcf: Path, tmp_path: Path) -> None:
    first = normalize(OperationRequest(valid_vcf, threads=1), tmp_path / "one.vcf.gz")
    second = normalize(
        OperationRequest(valid_vcf, threads=max(1, os.cpu_count() or 1)),
        tmp_path / "many.vcf.gz",
    )

    assert file_sha256(first.output_path) == file_sha256(second.output_path)
    assert file_sha256(first.index_path) == file_sha256(second.index_path)


def test_unsafe_merged_rewrite_publishes_assessment_only(
    valid_vcf: Path, tmp_path: Path
) -> None:
    input_path = tmp_path / "provisional.vcf"
    input_path.write_text(
        valid_vcf.read_text(encoding="utf-8").replace(
            "##source=Manta_1.6.0",
            "##source=OctopuSV_0.4.1",
        ),
        encoding="utf-8",
    )
    output = tmp_path / "unsafe.vcf.gz"
    assessment = tmp_path / "assessment.json"

    with pytest.raises(OutputError, match="must differ"):
        normalize(
            OperationRequest(input_path),
            output,
            profile="canonical",
            assessment_output=output,
        )
    with pytest.raises(ValidationFailure, match="does not support caller-specific rewriting"):
        normalize(
            OperationRequest(input_path),
            output,
            profile="canonical",
            assessment_output=assessment,
        )

    payload = json.loads(assessment.read_text(encoding="utf-8"))
    assert payload["complete"] is True
    assert "VSS-NORMALIZATION-ADAPTER-UNPROVEN" in {
        item["code"] for item in payload["diagnostics"]
    }
    assert not output.exists()


def test_canonical_profile_refuses_pre_45_input_with_assessment(
    valid_vcf: Path, tmp_path: Path
) -> None:
    output = tmp_path / "canonical.vcf.gz"
    assessment = tmp_path / "canonical-assessment.json"

    with pytest.raises(ValidationFailure, match=r"requires finalized VCF 4\.5"):
        normalize(
            OperationRequest(valid_vcf),
            output,
            profile="canonical",
            assessment_output=assessment,
        )

    payload = json.loads(assessment.read_text(encoding="utf-8"))
    assert "VSS-NORMALIZATION-CANONICAL-INPUT-VERSION" in {
        item["code"] for item in payload["diagnostics"]
    }
    assert not output.exists()


def _write_canonical_matrix(path: Path) -> Path:
    path.write_text(
        "\n".join(
            (
                "##fileformat=VCFv4.5",
                "##contig=<ID=chr1,length=1000000>",
                '##ALT=<ID=DEL,Description="Deletion">',
                '##ALT=<ID=DUP,Description="Duplication">',
                '##INFO=<ID=END,Number=1,Type=Integer,Description="Deprecated end">',
                '##INFO=<ID=SVLEN,Number=A,Type=Integer,Description="Length">',
                '##INFO=<ID=SVCLAIM,Number=A,Type=String,Description="Claim">',
                '##INFO=<ID=MATEID,Number=A,Type=String,Description="Mate">',
                '##INFO=<ID=EVENT,Number=A,Type=String,Description="Event">',
                '##INFO=<ID=EVENTTYPE,Number=A,Type=String,Description="Event type">',
                '##INFO=<ID=IA,Number=A,Type=Integer,Description="A vector">',
                '##INFO=<ID=IR,Number=R,Type=Integer,Description="R vector">',
                '##INFO=<ID=IG,Number=G,Type=Integer,Description="G vector">',
                '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">',
                '##FORMAT=<ID=LAA,Number=.,Type=Integer,Description="Local ALT indexes">',
                '##FORMAT=<ID=LAD,Number=LR,Type=Integer,Description="Local depths">',
                '##FORMAT=<ID=LEC,Number=LA,Type=Integer,Description="Local counts">',
                '##FORMAT=<ID=LPL,Number=LG,Type=Integer,Description="Local likelihoods">',
                '##FORMAT=<ID=FA,Number=A,Type=Integer,Description="A vector">',
                '##FORMAT=<ID=FR,Number=R,Type=Integer,Description="R vector">',
                '##FORMAT=<ID=FG,Number=G,Type=Integer,Description="G vector">',
                '##FORMAT=<ID=PSL,Number=P,Type=String,Description="Phase sets">',
                '##FORMAT=<ID=PSO,Number=P,Type=Integer,Description="Phase ordinals">',
                '##FORMAT=<ID=PSQ,Number=P,Type=Integer,Description="Phase quality">',
                "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tHG002",
                "chr1\t100\tmulti\tN\t<DEL>,<DUP>\t60\tPASS\t"
                "END=300;SVLEN=100,200;SVCLAIM=D,DJ;EVENT=event-del,event-dup;"
                "EVENTTYPE=DEL,DUP;IA=7,8;IR=9,10,11;IG=12,13,14,15,16,17\t"
                "GT:LAA:LAD:LEC:LPL:FA:FR:FG:PSL:PSO:PSQ\t"
                "1|2:1,2:30,10,20:4,6:0,1,2,3,4,5:7,8:9,10,11:"
                "12,13,14,15,16,17:.,phase-b:.,2:.,50",
                "chr1\t500\tbnd-a\tN\tN]chr1:700]\t40\tPASS\t"
                "SVLEN=.;MATEID=bnd-b;EVENT=event-bnd;EVENTTYPE=BND\tGT\t0/1",
                "chr1\t700\tbnd-b\tN\tN]chr1:500]\t40\tPASS\t"
                "SVLEN=.;MATEID=bnd-a;EVENT=event-bnd;EVENTTYPE=BND\tGT\t0/1",
                "",
            )
        ),
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize("suffix", [".vcf.gz", ".bcf"])
def test_canonical_multiallelic_split_is_lossless_and_container_independent(
    tmp_path: Path, suffix: str
) -> None:
    source = _write_canonical_matrix(tmp_path / "canonical-source.vcf")
    result = normalize(
        OperationRequest(source, adapter_id="urn:vcf-sv-stats:adapter:generic:1"),
        tmp_path / f"canonical{suffix}",
        profile="canonical",
    )

    with pysam.VariantFile(str(result.output_path)) as variant:
        header = str(variant.header)
        records = [str(record).rstrip("\n").split("\t") for record in variant]
    assert header.startswith("##fileformat=VCFv4.5\n")
    assert "##VCFSVSTATS1_PROFILE=canonical" in header
    assert len(records) == 4
    first, second = records[:2]
    assert first[2:5] == ["VCFSVSTATS1_R000000001A0001", "N", "<DEL>"]
    assert second[2:5] == ["VCFSVSTATS1_R000000001A0002", "N", "<DUP>"]
    assert "END=200" in first[7]
    assert "END=300" in second[7]
    assert "IA=7" in first[7] and "IR=9,10" in first[7]
    assert "IG=12,13,14" in first[7]
    assert "IA=8" in second[7] and "IR=9,11" in second[7]
    assert "IG=12,15,17" in second[7]
    assert first[9].startswith("1|0:1:30,10:4:0,1,2:7:9,10:12,13,14")
    assert second[9].startswith("0|1:1:30,20:6:0,3,5:8:9,11:12,15,17")
    assert records[2][7].split(";")[1].endswith("R000000003A0001")
    assert records[3][7].split(";")[1].endswith("R000000002A0001")
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["cardinality"] == {
        "input_records": 3,
        "input_alleles": 4,
        "output_records": 4,
        "record_mappings": 4,
        "event_identifiers": 3,
    }
    mappings = manifest["record_mappings"]
    assert len(mappings) == 4
    assert len({item["source_record_key"] for item in mappings}) == 4
    assert [item["output_ordinal"] for item in mappings] == [1, 2, 3, 4]
    if shutil.which("bcftools") is not None:
        subprocess.run(
            ["bcftools", "view", "--no-version", "-Ou", str(result.output_path)],
            check=True,
            stdout=subprocess.DEVNULL,
        )


@pytest.mark.parametrize(
    ("gt", "g_values", "p_values", "expected_gt", "expected_g"),
    [
        ("2", "0,1,2", "phase-a", ("0", "1"), ("0,1", "0,2")),
        (
            "1|.|2",
            "0,1,2,3,4,5,6,7,8,9",
            "phase-a,.,phase-b",
            ("1|.|0", "0|.|1"),
            ("0,1,2,3", "0,4,7,9"),
        ),
    ],
)
def test_canonical_g_and_p_projection_supports_arbitrary_ploidy(
    tmp_path: Path,
    gt: str,
    g_values: str,
    p_values: str,
    expected_gt: tuple[str, str],
    expected_g: tuple[str, str],
) -> None:
    source = tmp_path / "ploidy.vcf"
    source.write_text(
        "\n".join(
            (
                "##fileformat=VCFv4.5",
                "##contig=<ID=chr1,length=1000>",
                '##INFO=<ID=IG,Number=G,Type=Integer,Description="G vector">',
                '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">',
                '##FORMAT=<ID=FG,Number=G,Type=Integer,Description="G vector">',
                '##FORMAT=<ID=FP,Number=P,Type=String,Description="P vector">',
                "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tHG002",
                f"chr1\t10\tmulti\tA\tT,G\t.\tPASS\tIG={g_values}\t"
                f"GT:FG:FP\t{gt}:{g_values}:{p_values}",
                "",
            )
        ),
        encoding="utf-8",
    )
    result = normalize(
        OperationRequest(source, adapter_id="urn:vcf-sv-stats:adapter:generic:1"),
        tmp_path / "ploidy.vcf.gz",
        profile="canonical",
    )
    with pysam.VariantFile(str(result.output_path)) as variant:
        records = [str(record).rstrip("\n").split("\t") for record in variant]
    assert tuple(record[9].split(":", 2)[0] for record in records) == expected_gt
    assert tuple(record[9].split(":", 2)[1] for record in records) == expected_g
    assert tuple(record[7].partition("=")[2] for record in records) == expected_g
    assert all(record[9].split(":", 2)[2] == p_values for record in records)


def test_canonical_preserves_leading_phase_indicator_or_refuses_bcf(
    tmp_path: Path,
) -> None:
    source = tmp_path / "leading-phase.vcf"
    source.write_text(
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

    vcf_output = tmp_path / "leading-phase.vcf.gz"
    normalize(
        OperationRequest(source, adapter_id="urn:vcf-sv-stats:adapter:generic:1"),
        vcf_output,
        profile="canonical",
    )
    with gzip.open(vcf_output, "rt", encoding="utf-8") as handle:
        record = next(line for line in handle if not line.startswith("#"))
    assert record.rstrip("\n").endswith("\t|0|1:phase-a,phase-b")

    bcf_output = tmp_path / "leading-phase.bcf"
    with pytest.raises(ValidationFailure, match="cannot preserve a leading GT phase"):
        normalize(
            OperationRequest(source, adapter_id="urn:vcf-sv-stats:adapter:generic:1"),
            bcf_output,
            profile="canonical",
        )
    assert not bcf_output.exists()


def test_run_bundle_is_transactional(valid_vcf: Path, tmp_path: Path) -> None:
    output = tmp_path / "report"
    result = run_bundle(OperationRequest(valid_vcf), output, include_normalized=True)
    names = {path.name for path in result.artifacts}
    assert {
        "summary.vcf-sv-stats.json",
        "diagnostics.jsonl",
        "provenance.json",
        "callset.normalized.vcf.gz",
        "callset.normalized.vcf.gz.tbi",
    } <= names
    with pytest.raises(OutputError, match="already exists"):
        run_bundle(OperationRequest(valid_vcf), output)


@pytest.mark.parametrize(
    "destination_suffix",
    [".tbi", ".transforms.json", ".receipt.json", ""],
)
def test_each_publication_boundary_leaves_no_false_complete_set(
    valid_vcf: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    destination_suffix: str,
) -> None:
    output = tmp_path / "failure.vcf.gz"
    failure_target = Path(str(output) + destination_suffix)
    real_replace = os.replace

    def fail_selected_commit(source: str | Path, destination: str | Path) -> None:
        if Path(destination) == failure_target:
            raise OSError("injected publication failure")
        real_replace(source, destination)

    monkeypatch.setattr(os, "replace", fail_selected_commit)
    with pytest.raises(OSError, match="injected"):
        normalize(OperationRequest(valid_vcf), output)
    assert not output.exists()
    assert not Path(str(output) + ".tbi").exists()
    assert not Path(str(output) + ".transforms.json").exists()
    assert not Path(str(output) + ".receipt.json").exists()


def test_directory_sync_failure_leaves_no_false_complete_set(
    valid_vcf: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "sync-failure.vcf.gz"
    real_fsync = os.fsync

    def fail_directory_sync(file_descriptor: int) -> None:
        if stat.S_ISDIR(os.fstat(file_descriptor).st_mode):
            raise OSError("injected directory sync failure")
        real_fsync(file_descriptor)

    monkeypatch.setattr(os, "fsync", fail_directory_sync)
    with pytest.raises(OSError, match="injected"):
        normalize(OperationRequest(valid_vcf), output)
    assert not output.exists()
    assert not Path(str(output) + ".tbi").exists()
    assert not Path(str(output) + ".transforms.json").exists()
    assert not Path(str(output) + ".receipt.json").exists()


def test_force_failure_restores_complete_prior_set(
    valid_vcf: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "owned.vcf.gz"
    first = normalize(OperationRequest(valid_vcf), output)
    original = {
        path: file_sha256(path)
        for path in (first.output_path, first.index_path, first.manifest_path, first.receipt_path)
    }
    real_replace = os.replace
    failed = False

    def fail_new_data_once(source: str | Path, destination: str | Path) -> None:
        nonlocal failed
        if not failed and Path(destination) == output and ".stage." in str(source):
            failed = True
            raise OSError("injected replacement failure")
        real_replace(source, destination)

    monkeypatch.setattr(os, "replace", fail_new_data_once)
    with pytest.raises(OSError, match="injected"):
        normalize(OperationRequest(valid_vcf), output, force=True)
    assert {path: file_sha256(path) for path in original} == original


def test_backup_move_failure_restores_complete_prior_set(
    valid_vcf: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "owned-backup.vcf.gz"
    first = normalize(OperationRequest(valid_vcf), output)
    original = {
        file_path: file_sha256(file_path)
        for file_path in (
            first.output_path,
            first.index_path,
            first.manifest_path,
            first.receipt_path,
        )
    }
    real_replace = os.replace

    def fail_second_backup_move(source: str | Path, destination: str | Path) -> None:
        if Path(source) == first.index_path and Path(destination).parent.name == "prior":
            raise OSError("injected backup failure")
        real_replace(source, destination)

    monkeypatch.setattr(os, "replace", fail_second_backup_move)
    with pytest.raises(OSError, match="injected"):
        normalize(OperationRequest(valid_vcf), output, force=True)
    assert {file_path: file_sha256(file_path) for file_path in original} == original
