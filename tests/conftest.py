from __future__ import annotations

from pathlib import Path

import pytest


def write_vcf(
    path: Path,
    *,
    records: tuple[str, ...] | None = None,
    source: str = "Manta_1.6.0",
) -> Path:
    body = records or (
        "chr1\t100\tdel-1\tN\t<DEL>\t60\tPASS\tEND=199;SVTYPE=DEL;SVLEN=-100\tGT:CN\t0/1:1",
        "chr1\t300\tins-1\tA\t" + "A" + "T" * 60 + "\t50\tPASS\tSVTYPE=INS;SVLEN=60\tGT:CN\t1/1:3",
        "chr1\t500\tbnd-a\tN\tN]chr1:700]\t40\tPASS"
        "\tSVTYPE=BND;MATEID=bnd-b;EVENT=event-1\tGT:CN\t0/1:2",
        "chr1\t700\tbnd-b\tN\tN]chr1:500]\t.\tq10"
        "\tSVTYPE=BND;MATEID=bnd-a;EVENT=event-1\tGT:CN\t./.:.",
    )
    text = "\n".join(
        (
            "##fileformat=VCFv4.3",
            f"##source={source}",
            "##reference=GRCh38",
            "##contig=<ID=chr1,length=248956422>",
            '##ALT=<ID=DEL,Description="Deletion">',
            '##ALT=<ID=BND,Description="Breakend">',
            '##FILTER=<ID=q10,Description="Quality below ten">',
            '##INFO=<ID=END,Number=1,Type=Integer,Description="End position">',
            '##INFO=<ID=SVTYPE,Number=1,Type=String,Description="SV type">',
            '##INFO=<ID=SVLEN,Number=A,Type=Integer,Description="SV length">',
            '##INFO=<ID=MATEID,Number=.,Type=String,Description="Mate identifier">',
            '##INFO=<ID=EVENT,Number=1,Type=String,Description="Event identifier">',
            '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">',
            '##FORMAT=<ID=CN,Number=1,Type=Integer,Description="Copy number">',
            "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tHG002",
            *body,
            "",
        )
    )
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def valid_vcf(tmp_path: Path) -> Path:
    return write_vcf(tmp_path / "valid.vcf")
