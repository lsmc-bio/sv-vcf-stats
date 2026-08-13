"""Explicit, pinned public-reference acquisition and cache verification."""

from __future__ import annotations

import fcntl
import gzip
import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, cast

import pysam

from .exceptions import ReferenceError, UsageError
from .serialization import file_sha256, write_json_atomic

REFERENCE_PROFILE: dict[str, Any] = {
    "assembly": "GCF_000001405.40",
    "name": "GRCh38.p14",
    "distribution": "ncbi-refseq",
    "url": "https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/001/405/GCF_000001405.40_GRCh38.p14/GCF_000001405.40_GRCh38.p14_genomic.fna.gz",
    "expected_size": 972_898_531,
    "expected_md5": "c30471567037b2b2389d43c908c653e1",
    "terms_url": "https://www.ncbi.nlm.nih.gov/home/about/policies/",
}


def _profile(assembly: str, distribution: str) -> dict[str, Any]:
    if assembly not in {REFERENCE_PROFILE["assembly"], REFERENCE_PROFILE["name"]}:
        raise UsageError("Assembly must be the precise accession GCF_000001405.40 or GRCh38.p14")
    if distribution != REFERENCE_PROFILE["distribution"]:
        raise UsageError("Only the ncbi-refseq distribution is supported in v1")
    return dict(REFERENCE_PROFILE)


def _verify_cache(directory: Path) -> dict[str, Any]:
    manifest_path = directory / "manifest.json"
    fasta = directory / "reference.fasta"
    fai = directory / "reference.fasta.fai"
    if not manifest_path.is_file() or not fasta.is_file() or not fai.is_file():
        raise ReferenceError(f"Verified reference cache is incomplete: {directory}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if file_sha256(fasta) != manifest.get("fasta_sha256"):
        raise ReferenceError("Cached reference digest does not match its manifest")
    return cast(dict[str, Any], manifest)


def fetch_reference(
    *,
    assembly: str,
    distribution: str,
    cache_dir: str | Path,
    yes: bool,
    offline: bool,
    dry_run: bool,
) -> dict[str, Any]:
    profile = _profile(assembly, distribution)
    cache_root = Path(cache_dir).expanduser().resolve(strict=False)
    target = cache_root / f"{profile['assembly']}-{profile['distribution']}"
    if target.exists():
        return {"status": "verified", "cache": str(target), **_verify_cache(target)}
    if offline:
        raise ReferenceError(f"Reference is not present in the offline cache: {target}")
    if not yes:
        raise UsageError("Reference transfer requires interactive confirmation or --yes")
    planned = {
        "status": "planned" if dry_run else "downloading",
        "assembly": profile["assembly"],
        "distribution": profile["distribution"],
        "url": profile["url"],
        "expected_size": profile["expected_size"],
        "expected_md5": profile["expected_md5"],
        "terms_url": profile["terms_url"],
        "cache": str(target),
    }
    if dry_run:
        return planned
    cache_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_path = cache_root / ".reference-fetch.lock"
    with lock_path.open("a+b") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        if target.exists():
            return {"status": "verified", "cache": str(target), **_verify_cache(target)}
        stage = Path(tempfile.mkdtemp(prefix=".reference-stage.", dir=cache_root))
        compressed = stage / "reference.fasta.gz"
        fasta = stage / "reference.fasta"
        md5 = hashlib.md5(usedforsecurity=False)
        sha256 = hashlib.sha256()
        total = 0
        try:
            with (
                urllib.request.urlopen(profile["url"], timeout=60) as response,
                compressed.open("xb") as output,
            ):
                os.chmod(compressed, 0o600)
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > profile["expected_size"]:
                        raise ReferenceError("Reference transfer exceeds the pinned size")
                    md5.update(chunk)
                    sha256.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            if total != profile["expected_size"] or md5.hexdigest() != profile["expected_md5"]:
                raise ReferenceError("Reference transfer does not match pinned size and digest")
            with gzip.open(compressed, "rb") as source, fasta.open("xb") as output:
                os.chmod(fasta, 0o600)
                shutil.copyfileobj(source, output, length=1024 * 1024)
                output.flush()
                os.fsync(output.fileno())
            pysam.faidx(str(fasta))
            manifest = {
                "schema_name": "vcf-sv-stats.reference-cache",
                "schema_version": "1.0.0",
                "assembly": profile["assembly"],
                "distribution": profile["distribution"],
                "source_url": profile["url"],
                "compressed_size": total,
                "compressed_md5": md5.hexdigest(),
                "compressed_sha256": sha256.hexdigest(),
                "fasta_sha256": file_sha256(fasta),
            }
            write_json_atomic(stage / "manifest.json", manifest)
            compressed.unlink()
            os.replace(stage, target)
            return {"status": "downloaded", "cache": str(target), **manifest}
        except Exception:
            shutil.rmtree(stage, ignore_errors=True)
            raise
