from __future__ import annotations

from pathlib import Path

from conftest import write_vcf

from vcf_sv_stats.engine import stats
from vcf_sv_stats.events import EventStore
from vcf_sv_stats.models import OperationRequest


def test_event_store_preserves_relationship_diagnostics() -> None:
    with EventStore() as store:
        assert (
            store.connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
            == []
        )
        store.add(1, "bnd-a", "event-bnd", ("bnd-b",), is_bnd=True)
        store.add(2, "bnd-b", "event-bnd", ("bnd-a",), is_bnd=True)
        store.add(3, "orphan", None, ("missing",), is_bnd=True)
        store.add(4, "duplicate", None, (), is_bnd=False)
        store.add(5, "duplicate", None, (), is_bnd=False)
        store.add(6, None, "explicit-event", (), is_bnd=False)
        store.add(7, None, None, (), is_bnd=True)

        assert store.summarize() == {
            "duplicate_ids": (("duplicate", 2),),
            "unresolved_mate_references": 1,
            "bnd_total": 4,
            "bnd_without_mate": 1,
            "reciprocal_pairs": 1,
            "resolved_events": 2,
        }
        assert {
            row[0]
            for row in store.connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            )
        } == {"records_id", "records_event", "mates_ordinal", "mates_id"}


def test_reciprocal_cross_contig_bnds_remain_one_event(tmp_path: Path) -> None:
    records = (
        "chr1\t100\tbnd-a\tN\tN]chr2:200]\t.\tPASS\tSVTYPE=BND;MATEID=bnd-b;EVENT=pair\tGT\t0/1",
        "chr2\t200\tbnd-b\tN\tN]chr1:100]\t.\tPASS\tSVTYPE=BND;MATEID=bnd-a;EVENT=pair\tGT\t0/1",
    )
    path = write_vcf(tmp_path / "cross-contig.vcf", records=records)
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "##contig=<ID=chr1,length=248956422>",
            "##contig=<ID=chr1,length=248956422>\n##contig=<ID=chr2,length=242193529>",
        ),
        encoding="utf-8",
    )

    result = stats(OperationRequest(path))

    assert result.summary["statistics"]["breakends"] == {
        "total": 2,
        "reciprocal_pairs": 1,
        "without_declared_mate": 0,
        "unresolved_mate_references": 0,
    }
    assert result.summary["statistics"]["events"] == {"resolved": 1}


def test_nonrelationship_gvcf_blocks_are_not_persisted(tmp_path: Path) -> None:
    reference_blocks = tuple(
        f"chr1\t{position}\t.\tA\t<NON_REF>\t.\tPASS\tEND={position + 9}\tGT\t0/0"
        for position in range(1, 10001, 10)
    )
    path = write_vcf(tmp_path / "reference-blocks.vcf", records=reference_blocks)
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            '##ALT=<ID=DEL,Description="Deletion">',
            "\n".join(
                (
                    '##ALT=<ID=DEL,Description="Deletion">',
                    '##ALT=<ID=NON_REF,Description="Reference block">',
                )
            ),
        ),
        encoding="utf-8",
    )

    with EventStore(temp_dir=tmp_path) as store:
        for ordinal in range(1, 1001):
            store.add(ordinal, None, None, (), is_bnd=False)
        assert store.connection.execute("SELECT COUNT(*) FROM records").fetchone() == (0,)
        assert store.summarize() == {
            "duplicate_ids": (),
            "unresolved_mate_references": 0,
            "bnd_total": 0,
            "bnd_without_mate": 0,
            "reciprocal_pairs": 0,
            "resolved_events": 0,
        }

    result = stats(OperationRequest(path))
    assert result.summary["statistics"]["source_records"]["total"] == 1000
    assert result.summary["statistics"]["events"] == {"resolved": 0}
