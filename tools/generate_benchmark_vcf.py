#!/usr/bin/env python3
"""Generate deterministic, neutral synthetic VCF inputs for qualification runs."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path
from typing import Any

import pysam

from vcf_sv_stats.exceptions import UsageError
from vcf_sv_stats.serialization import file_sha256, write_json_atomic

GENERATOR_VERSION = "neutral-sv-benchmark/1"


def _header(*, samples: int, contigs: int, contig_length: int) -> bytes:
    lines = [
        "##fileformat=VCFv4.3",
        f"##source={GENERATOR_VERSION}",
        *(f"##contig=<ID=chr{index},length={contig_length}>" for index in range(1, contigs + 1)),
        '##ALT=<ID=DEL,Description="Deletion">',
        '##ALT=<ID=INS,Description="Insertion">',
        '##FILTER=<ID=PASS,Description="All filters passed">',
        '##INFO=<ID=SVTYPE,Number=1,Type=String,Description="Structural variant type">',
        '##INFO=<ID=SVLEN,Number=1,Type=Integer,Description="Structural variant length">',
        '##INFO=<ID=END,Number=1,Type=Integer,Description="End position">',
        '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">',
    ]
    columns = ["#CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO", "FORMAT"]
    columns.extend(f"S{index:04d}" for index in range(1, samples + 1))
    lines.append("\t".join(columns))
    return ("\n".join(lines) + "\n").encode()


def _record(
    ordinal: int,
    *,
    samples: int,
    contigs: int,
    contig_length: int,
    seed: int,
) -> bytes:
    contig_index = (ordinal - 1) % contigs + 1
    contig_cycle = (ordinal - 1) // contigs
    coordinate_span = contig_length - 10_000
    pos = 100 + ((contig_cycle * 97 + seed * 1_009) % coordinate_span)
    length = 50 + ((ordinal * 37 + seed) % 1_951)
    is_insertion = ordinal % 5 == 0
    svtype = "INS" if is_insertion else "DEL"
    alt = f"<{svtype}>"
    end = pos if is_insertion else pos + length - 1
    svlen = length if is_insertion else -length
    values = [
        f"chr{contig_index}",
        str(pos),
        f"bench-{ordinal:010d}",
        "N",
        alt,
        "60",
        "PASS",
        f"SVTYPE={svtype};END={end};SVLEN={svlen}",
        "GT",
    ]
    values.extend(
        "1/1" if (ordinal + sample + seed) % 7 == 0 else "0/1" for sample in range(samples)
    )
    return ("\t".join(values) + "\n").encode()


def generate(
    output: Path,
    manifest: Path,
    *,
    class_id: str,
    records: int,
    samples: int,
    contigs: int,
    contig_length: int,
    seed: int,
) -> dict[str, Any]:
    if records < 1 or samples < 1 or contigs < 1:
        raise UsageError("records, samples, and contigs must be positive")
    if contig_length <= 10_000:
        raise UsageError("contig length must exceed 10,000 bases")
    if not class_id or any(
        character not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for character in class_id
    ):
        raise UsageError("class-id must use lowercase letters, digits, hyphens, or underscores")
    if output.suffixes[-2:] != [".vcf", ".gz"]:
        raise UsageError("benchmark output must end with .vcf.gz")
    if not output.parent.is_dir() or not manifest.parent.is_dir():
        raise UsageError("output and manifest parent directories must already exist")
    if output.exists() or manifest.exists():
        raise UsageError("benchmark outputs must not already exist")
    if output.resolve(strict=False) == manifest.resolve(strict=False):
        raise UsageError("benchmark output and manifest must differ")

    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with pysam.BGZFile(str(temporary), "w") as handle:  # type: ignore[call-arg]
            handle.write(_header(samples=samples, contigs=contigs, contig_length=contig_length))
            for ordinal in range(1, records + 1):
                handle.write(
                    _record(
                        ordinal,
                        samples=samples,
                        contigs=contigs,
                        contig_length=contig_length,
                        seed=seed,
                    )
                )
        os.replace(temporary, output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise

    result: dict[str, Any] = {
        "schema_name": "vcf-sv-stats.synthetic-benchmark-input",
        "schema_version": "1.0.0",
        "generator": GENERATOR_VERSION,
        "class_id": class_id,
        "source_derived": False,
        "seed": seed,
        "records": records,
        "samples": samples,
        "contigs": contigs,
        "contig_length": contig_length,
        "output_name": output.name,
        "output_bytes": output.stat().st_size,
        "output_sha256": file_sha256(output),
    }
    write_json_atomic(manifest, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--class-id", required=True)
    parser.add_argument("--records", type=int, required=True)
    parser.add_argument("--samples", type=int, default=1)
    parser.add_argument("--contigs", type=int, default=1)
    parser.add_argument("--contig-length", type=int, default=248_956_422)
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()
    result = generate(
        args.output,
        args.manifest,
        class_id=args.class_id,
        records=args.records,
        samples=args.samples,
        contigs=args.contigs,
        contig_length=args.contig_length,
        seed=args.seed,
    )
    print(f"generated={result['records']} sha256={result['output_sha256']}")


if __name__ == "__main__":
    main()
