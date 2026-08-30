#!/usr/bin/env python3
"""Generate a coordinate-sorted, indexed, reference-block-heavy gVCF."""

from __future__ import annotations

import argparse
from pathlib import Path

import pysam

CONTIGS = 24


def generate(output: Path, *, records: int = 1_000_000) -> Path:
    if records != 1_000_000:
        raise ValueError("benchmark contract requires exactly 1,000,000 records")
    if output.exists() or not output.parent.is_dir():
        raise ValueError("output must be new and its parent must exist")
    header = ["##fileformat=VCFv4.3", "##source=vcf-sv-stats-gvcf-benchmark/1"]
    header.extend(f"##contig=<ID=chr{i},length=100000000>" for i in range(1, CONTIGS + 1))
    header.extend(
        [
            '##ALT=<ID=NON_REF,Description="Represents any possible alternative allele">',
            '##INFO=<ID=END,Number=1,Type=Integer,Description="End position">',
            '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">',
            "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE",
        ]
    )
    with pysam.BGZFile(str(output), "w") as handle:
        handle.write(("\n".join(header) + "\n").encode())
        for contig in range(1, CONTIGS + 1):
            count = (records // CONTIGS) + (contig <= records % CONTIGS)
            for block in range(count):
                start = 1 + block * 100
                end = start + 99
                row = f"chr{contig}\t{start}\t.\tA\t<NON_REF>\t.\tPASS\tEND={end}\tGT\t0/0\n"
                handle.write(row.encode())
    pysam.tabix_index(str(output), preset="vcf", force=False)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--records", type=int, default=1_000_000)
    args = parser.parse_args()
    generate(args.output, records=args.records)


if __name__ == "__main__":
    main()
