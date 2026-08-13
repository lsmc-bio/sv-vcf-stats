#!/usr/bin/env python3
"""Normalize a Python source archive for byte-reproducible release auditing."""

from __future__ import annotations

import argparse
import copy
import gzip
import io
import os
import tarfile
import tempfile
from pathlib import Path


def normalize_sdist(path: Path, *, epoch: int) -> None:
    """Rewrite one local tar.gz with stable order, ownership, timestamps, and gzip header."""
    source = path.resolve(strict=True)
    if not source.is_file() or not source.name.endswith(".tar.gz"):
        raise ValueError("sdist must be a local .tar.gz file")
    if epoch < 0:
        raise ValueError("epoch must be nonnegative")

    with tarfile.open(source, mode="r:gz") as archive:
        members: list[tuple[tarfile.TarInfo, bytes | None]] = []
        for member in archive.getmembers():
            payload: bytes | None = None
            if member.isfile():
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise ValueError(f"unable to read archive member: {member.name}")
                payload = extracted.read()
            members.append((member, payload))

    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{source.name}.", dir=source.parent)
    temporary = Path(temporary_name)
    try:
        with (
            os.fdopen(descriptor, "wb") as raw,
            gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=epoch) as compressed,
            tarfile.open(
                fileobj=compressed,
                mode="w",
                format=tarfile.PAX_FORMAT,
            ) as output,
        ):
            for original, payload in members:
                member = copy.copy(original)
                member.uid = 0
                member.gid = 0
                member.uname = ""
                member.gname = ""
                member.mtime = epoch
                member.pax_headers = {
                    key: value
                    for key, value in member.pax_headers.items()
                    if key not in {"atime", "ctime", "mtime"}
                }
                if payload is None:
                    output.addfile(member)
                else:
                    output.addfile(member, io.BytesIO(payload))
            raw.flush()
            os.fsync(raw.fileno())
        os.replace(temporary, source)
        directory_descriptor = os.open(source.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdist", type=Path, required=True)
    parser.add_argument("--epoch", type=int, required=True)
    args = parser.parse_args()
    normalize_sdist(args.sdist, epoch=args.epoch)


if __name__ == "__main__":
    main()
