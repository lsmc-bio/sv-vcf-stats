from __future__ import annotations

import json
import os
import stat
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
        "output_records": 4,
        "record_mappings": 4,
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


def test_unimplemented_canonical_profile_fails_instead_of_copying(
    valid_vcf: Path, tmp_path: Path
) -> None:
    output = tmp_path / "canonical.vcf.gz"
    assessment = tmp_path / "canonical-assessment.json"

    with pytest.raises(ValidationFailure, match="profile is not implemented"):
        normalize(
            OperationRequest(valid_vcf),
            output,
            profile="canonical",
            assessment_output=assessment,
        )

    payload = json.loads(assessment.read_text(encoding="utf-8"))
    assert "VSS-NORMALIZATION-PROFILE-UNIMPLEMENTED" in {
        item["code"] for item in payload["diagnostics"]
    }
    assert not output.exists()


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
