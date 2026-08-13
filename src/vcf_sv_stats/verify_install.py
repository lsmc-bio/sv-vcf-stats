"""Network-free, self-contained verification for an installed distribution."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pysam

from . import __version__
from .engine import stats, validate
from .exceptions import ValidationFailure
from .models import OperationRequest
from .normalize import normalize
from .schemas import validate_artifact
from .serialization import file_sha256, payload_sha256, write_json_atomic

EMBEDDED_VCF = """##fileformat=VCFv4.3
##source=vcf-sv-stats-verify-install
##reference=GRCh38
##contig=<ID=chr1,length=248956422>
##ALT=<ID=DEL,Description="Deletion">
##INFO=<ID=END,Number=1,Type=Integer,Description="End position">
##INFO=<ID=SVTYPE,Number=1,Type=String,Description="Structural variant type">
##INFO=<ID=SVLEN,Number=A,Type=Integer,Description="Structural variant length">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=CN,Number=1,Type=Integer,Description="Copy number">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE1
chr1\t100\tverify-del\tN\t<DEL>\t60\tPASS\tEND=149;SVTYPE=DEL;SVLEN=-50\tGT:CN\t0/1:1
chr1\t300\tverify-ins\tA\tATTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT\t50\tPASS\tSVTYPE=INS;SVLEN=52\tGT:CN\t1/1:3
"""


def _projection(summary: dict[str, Any]) -> dict[str, Any]:
    callset = summary["callset"]
    return {
        "callset": {
            "record_count": callset["record_count"],
            "allele_count": callset["allele_count"],
            "vcf_sample_ids": callset["vcf_sample_ids"],
            "producer_kind": callset["producer_kind"],
        },
        "validation": summary["validation"],
        "statistics": summary["statistics"],
    }


def _write_inputs(directory: Path) -> tuple[Path, Path]:
    plain = directory / "embedded.vcf"
    plain.write_text(EMBEDDED_VCF, encoding="utf-8")
    compressed = directory / "embedded.vcf.gz"
    pysam.tabix_compress(str(plain), str(compressed), force=False)
    pysam.tabix_index(str(compressed), preset="vcf", force=False)
    bcf = directory / "embedded.bcf"
    with (
        pysam.VariantFile(str(compressed)) as source,
        pysam.VariantFile(str(bcf), "wb", header=source.header.copy()) as destination,
    ):
        for record in source:
            destination.write(record)
    pysam.bcftools.index("--csi", str(bcf), catch_stdout=False)
    return compressed, bcf


def _run_cli(command: list[str], arguments: list[str], directory: Path) -> None:
    result = subprocess.run(
        [*command, *arguments],
        cwd=directory,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=60,
    )
    if result.returncode != 0:
        raise ValidationFailure(f"installed CLI smoke failed: {arguments[0]}")


def verify() -> dict[str, Any]:
    """Build private embedded inputs and verify API, CLI, VCF, BCF, and indexes."""
    cli_command = [sys.executable, "-m", "vcf_sv_stats"]
    with tempfile.TemporaryDirectory(prefix="vcf-sv-stats.verify-install.") as directory_name:
        directory = Path(directory_name)
        vcf, bcf = _write_inputs(directory)
        source_summaries = []
        normalized_summaries = []
        formats: list[dict[str, Any]] = []
        for source in (vcf, bcf):
            validation = validate(OperationRequest(source))
            if not validation.valid:
                raise ValidationFailure(f"embedded {source.suffix} input did not validate")
            source_result = stats(OperationRequest(source))
            source_summaries.append(source_result.summary)
            normalized = directory / (
                "normalized.vcf.gz" if source.name.endswith(".vcf.gz") else "normalized.bcf"
            )
            normalization = normalize(OperationRequest(source), normalized)
            normalized_result = stats(OperationRequest(normalized))
            normalized_summaries.append(normalized_result.summary)
            formats.append(
                {
                    "container": "vcf.gz" if source.name.endswith(".vcf.gz") else "bcf",
                    "input_sha256": file_sha256(source),
                    "input_index_sha256": file_sha256(
                        Path(str(source) + (".tbi" if source.name.endswith(".vcf.gz") else ".csi"))
                    ),
                    "normalized_sha256": normalization.output_sha256,
                    "normalized_index_sha256": normalization.index_sha256,
                    "semantic_sha256": payload_sha256(_projection(source_result.summary)),
                    "normalized_semantic_sha256": payload_sha256(
                        _projection(normalized_result.summary)
                    ),
                }
            )

        semantic_digests = {payload_sha256(_projection(value)) for value in source_summaries}
        normalized_digests = {payload_sha256(_projection(value)) for value in normalized_summaries}
        if len(semantic_digests) != 1 or normalized_digests != semantic_digests:
            raise ValidationFailure("embedded VCF/BCF semantic parity failed")

        cli_output = directory / "cli-summary.json"
        _run_cli(cli_command, ["version"], directory)
        _run_cli(cli_command, ["--json", "info"], directory)
        _run_cli(cli_command, ["--json", "validate", str(vcf)], directory)
        _run_cli(cli_command, ["stats", str(bcf), "--output", str(cli_output)], directory)
        if not cli_output.is_file():
            raise ValidationFailure("installed CLI did not publish its summary")

        value: dict[str, Any] = {
            "schema_name": "vcf-sv-stats.install-verification",
            "schema_version": "1.0.0",
            "environment": {
                "operating_system": platform.system(),
                "machine": platform.machine(),
                "python_version": platform.python_version(),
                "tool_version": __version__,
                "pysam_version": str(vars(pysam).get("__version__", "unavailable")),
                "htslib_version": getattr(pysam, "__samtools_version__", "unavailable"),
            },
            "embedded_input": {
                "records": 2,
                "samples": ["SAMPLE1"],
                "source_derived": False,
            },
            "formats": formats,
            "semantic_sha256": next(iter(semantic_digests)),
            "cli_commands": ["version", "info", "validate", "stats"],
            "network_required": False,
            "passed": True,
        }
        value["receipt_sha256"] = payload_sha256(value)
        validate_artifact("install-verification", value)
        return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    value = verify()
    if args.output is None:
        print(json.dumps(value, indent=2, sort_keys=True))
    else:
        write_json_atomic(args.output, value)


if __name__ == "__main__":
    main()
