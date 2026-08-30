"""Input materialization, locality, container, and alias safety."""

from __future__ import annotations

import contextlib
import gzip
import os
import shutil
import stat
import sys
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pysam

from .exceptions import InputError, OutputError, UsageError
from .serialization import file_sha256

DEFAULT_MAX_INPUT_BYTES = 100_000_000_000


@dataclass(frozen=True, slots=True)
class Region:
    contig: str
    start: int | None = None
    end: int | None = None


def parse_regions(values: tuple[str, ...]) -> tuple[Region, ...]:
    regions: list[Region] = []
    for value in values:
        contig, separator, interval = value.partition(":")
        if not contig or (separator and not interval):
            raise InputError(f"Invalid region: {value}")
        if not separator:
            regions.append(Region(contig))
            continue
        start_text, dash, end_text = interval.replace(",", "").partition("-")
        try:
            start = int(start_text)
            end = int(end_text) if dash and end_text else start
        except ValueError as exc:
            raise InputError(f"Invalid region: {value}") from exc
        if start < 1 or end < start:
            raise InputError(f"Invalid region: {value}")
        regions.append(Region(contig, start, end))
    return tuple(regions)


def record_in_regions(record: Any, regions: tuple[Region, ...]) -> bool:
    if not regions:
        return True
    contig = str(record.contig)
    start = int(record.pos)
    stop_value = record.stop
    end = start if stop_value is None else int(stop_value)
    return any(
        region.contig == contig
        and (region.start is None or end >= region.start)
        and (region.end is None or start <= region.end)
        for region in regions
    )


def has_variant_index(path: str | Path) -> bool:
    value = Path(path)
    return any(
        candidate.is_file() for candidate in (Path(str(value) + ".tbi"), Path(str(value) + ".csi"))
    )


def _reject_remote(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme and parsed.scheme != "file":
        raise InputError(f"Remote input URIs are not supported: {parsed.scheme}")
    if parsed.scheme == "file":
        raise InputError("file:// URIs are not accepted; provide a local path")


def _enforce_uncompressed_limit(path: Path, limit: int | None) -> None:
    if limit is None:
        return
    if limit < 1:
        raise InputError("max_uncompressed_bytes must be positive")
    with path.open("rb") as raw:
        compressed = raw.read(2) == b"\x1f\x8b"
    total = 0
    try:
        opener = gzip.open if compressed else Path.open
        with opener(path, "rb") as handle:
            while chunk := handle.read(1024 * 1024):
                total += len(chunk)
                if total > limit:
                    raise InputError(
                        f"Input exceeds max_uncompressed_bytes: greater than {limit}"
                    )
    except (gzip.BadGzipFile, EOFError, OSError) as exc:
        raise InputError(f"Unable to inspect compressed input safely: {exc}") from exc


@contextlib.contextmanager
def materialize_input(
    input_path: str | Path,
    *,
    temp_dir: str | Path | None = None,
    max_input_bytes: int | None = None,
    max_uncompressed_bytes: int | None = None,
) -> Iterator[Path]:
    value = str(input_path)
    limit = DEFAULT_MAX_INPUT_BYTES if max_input_bytes is None else max_input_bytes
    if limit < 1:
        raise InputError("max_input_bytes must be positive")
    if value != "-":
        _reject_remote(value)
        path = Path(value)
        if not path.exists():
            raise InputError(f"Input does not exist: {path}")
        mode = path.stat().st_mode
        if not stat.S_ISREG(mode):
            raise InputError(f"Input is not a regular file: {path}")
        if path.stat().st_size > limit:
            raise InputError(f"Input exceeds max_input_bytes: {path.stat().st_size} > {limit}")
        resolved = path.resolve(strict=True)
        _enforce_uncompressed_limit(resolved, max_uncompressed_bytes)
        yield resolved
        return

    directory = None if temp_dir is None else Path(temp_dir)
    if directory is not None and not directory.is_dir():
        raise InputError(f"Temporary directory does not exist: {directory}")
    fd, name = tempfile.mkstemp(prefix="vcf-sv-stats.stdin.", suffix=".input", dir=directory)
    path = Path(name)
    total = 0
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as handle:
            while chunk := sys.stdin.buffer.read(1024 * 1024):
                total += len(chunk)
                if total > limit:
                    raise InputError(f"Standard input exceeds max_input_bytes: {limit}")
                handle.write(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        _enforce_uncompressed_limit(path, max_uncompressed_bytes)
        yield path
    finally:
        path.unlink(missing_ok=True)


def input_metadata(path: str | Path, *, display_name: str | None = None) -> dict[str, object]:
    source = Path(path)
    with source.open("rb") as handle:
        magic = handle.read(4)
    if magic.startswith(b"BCF"):
        container = "bcf"
    elif magic[:2] == b"\x1f\x8b":
        try:
            with gzip.open(source, "rb") as handle:
                inner_magic = handle.read(5)
        except (gzip.BadGzipFile, EOFError, OSError) as exc:
            raise InputError(f"Unable to inspect compressed input safely: {exc}") from exc
        container = "bcf" if inner_magic.startswith(b"BCF") else "vcf.gz"
    else:
        container = "vcf"
    return {
        "sha256": file_sha256(source),
        "size_bytes": source.stat().st_size,
        "container": container,
        "display_name": display_name or source.name,
        "complete": True,
    }


def validate_threads(threads: int) -> None:
    if threads < 1:
        raise UsageError("threads must be positive")


def open_variant(path: str | Path, *, threads: int = 1) -> pysam.VariantFile:
    validate_threads(threads)
    try:
        return pysam.VariantFile(str(path), "r", threads=threads)
    except (OSError, ValueError) as exc:
        raise InputError(f"Unable to open VCF/BCF input: {exc}") from exc


def iter_record_texts(path: str | Path, *, threads: int = 1) -> Iterator[str]:
    """Yield exact VCF records when textual, or HTSlib-rendered records for BCF."""
    validate_threads(threads)
    source = Path(path)
    container = str(input_metadata(source)["container"])
    if container == "bcf":
        with open_variant(source, threads=threads) as variant:
            for record in variant:
                yield str(record).rstrip("\n")
        return
    try:
        if container == "vcf.gz":
            with gzip.open(source, "rt", encoding="utf-8", newline="") as handle:
                for line in handle:
                    if not line.startswith("#"):
                        yield line.rstrip("\r\n")
        else:
            with source.open("rt", encoding="utf-8", newline="") as handle:
                for line in handle:
                    if not line.startswith("#"):
                        yield line.rstrip("\r\n")
    except (gzip.BadGzipFile, EOFError, OSError, UnicodeError) as exc:
        raise InputError(f"Unable to read VCF record text safely: {exc}") from exc


def assert_distinct_paths(input_path: str | Path, output_path: str | Path) -> None:
    source = Path(input_path)
    target = Path(output_path)
    try:
        if source.exists() and target.exists() and os.path.samefile(source, target):
            raise OutputError("Output aliases the input")
    except OSError as exc:
        raise OutputError(f"Unable to compare input/output identities: {exc}") from exc
    if source.resolve(strict=True) == target.resolve(strict=False):
        raise OutputError("Output aliases the input")


def copy_stream(source: Path, destination: Path) -> None:
    with source.open("rb") as src, destination.open("xb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
        dst.flush()
        os.fsync(dst.fileno())
