from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any, cast

import pysam

from vcf_sv_stats.canonical import iter_canonical
from vcf_sv_stats.diagnostics import CATALOG
from vcf_sv_stats.engine import stats
from vcf_sv_stats.models import OperationRequest
from vcf_sv_stats.serialization import file_sha256

ROOT = Path(__file__).resolve().parents[1] / "test_data"


def _manifest() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((ROOT / "manifest.json").read_text()))


def test_manifest_binds_all_hg002_fixtures() -> None:
    manifest = _manifest()
    assert manifest["subject"] == "HG002"
    assert len(manifest["fixtures"]) == 21
    assert len(manifest["source_identity_evidence"]) == 22
    assert manifest["totals"]["source_derived_records"] < 2_500
    assert manifest["totals"]["compressed_vcf_bytes"] < 10 * 1024 * 1024

    for entry in manifest["fixtures"]:
        path = ROOT / entry["fixture_path"]
        assert entry["subject"] == "HG002"
        assert entry["oversized_relationship_exclusions"] == []
        assert file_sha256(path) == entry["fixture_sha256"]
        assert file_sha256(Path(str(path) + ".tbi")) == entry["index_sha256"]
        with pysam.VariantFile(str(path)) as variant:
            assert tuple(variant.header.samples) == ("HG002",)
            assert sum(1 for _ in variant.fetch()) == entry["fixture_record_count"]


def test_fixture_goldens_cover_every_role() -> None:
    for entry in _manifest()["fixtures"]:
        fixture_id = entry["fixture_id"]
        path = ROOT / entry["fixture_path"]
        expected = json.loads((ROOT / "expected" / f"{fixture_id}.expected.json").read_text())
        result = stats(OperationRequest(path))
        observed = {
            "fixture": path.name,
            "detection": json.loads(json.dumps(result.summary["callset"]["producer"])),
            "callset": {
                key: result.summary["callset"][key]
                for key in ("vcf_sample_ids", "single_sample", "record_count", "allele_count")
            },
            "statistics": result.summary["statistics"],
            "diagnostic_codes": sorted(item.code for item in result.diagnostics),
        }
        assert observed == expected
        assert set(observed["diagnostic_codes"]) <= set(CATALOG)


def test_plain_compressed_and_bcf_semantic_parity() -> None:
    plain = ROOT / "vcf/truvari.query.hg002.subset.vcf"
    compressed = ROOT / "vcf/truvari.query.hg002.subset.vcf.gz"
    assert gzip.decompress(compressed.read_bytes()) == plain.read_bytes()

    source = ROOT / "vcf/manta.native.hg002.subset.vcf.gz"
    bcf = ROOT / "vcf/manta.native.hg002.subset.bcf"
    assert Path(str(bcf) + ".csi").is_file()
    with (
        pysam.VariantFile(str(source)) as source_variant,
        pysam.VariantFile(str(bcf)) as bcf_variant,
    ):
        assert tuple(bcf_variant.header.samples) == ("HG002",)
        source_rows = [
            (record.contig, record.pos, record.id, record.ref, record.alts)
            for record in source_variant
        ]
        bcf_rows = [
            (record.contig, record.pos, record.id, record.ref, record.alts)
            for record in bcf_variant.fetch()
        ]
    assert bcf_rows == source_rows
    assert tuple(iter_canonical(OperationRequest(source))) == tuple(
        iter_canonical(OperationRequest(bcf))
    )
    assert stats(OperationRequest(source)).summary["statistics"] == stats(
        OperationRequest(bcf)
    ).summary["statistics"]
