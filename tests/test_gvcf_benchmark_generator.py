from pathlib import Path

import pysam

from tools.generate_gvcf_benchmark import generate


def test_gvcf_benchmark_is_sorted_indexed_and_reference_block_heavy(tmp_path: Path) -> None:
    path = generate(tmp_path / "benchmark.g.vcf.gz", records=1_000_000)
    assert path.with_suffix(path.suffix + ".tbi").is_file()
    with pysam.VariantFile(str(path)) as vcf:
        assert len(vcf.header.contigs) == 24
        records = list(vcf.fetch("chr1", 1, 101))
        assert records[0].id == "."
        assert records[0].alts == ("<NON_REF>",)
        assert records[0].info["END"] == 100
        assert sum(1 for _ in vcf.fetch("chr24")) == 41_666
