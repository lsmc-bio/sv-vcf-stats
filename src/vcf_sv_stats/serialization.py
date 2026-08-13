"""Deterministic JSON and digest helpers."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import rfc8785

from .exceptions import OutputError


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize a JSON value using RFC 8785 canonicalization."""
    return rfc8785.dumps(value)


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def file_sha256(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def write_bytes_atomic(path: str | Path, content: bytes, *, force: bool = False) -> Path:
    target = Path(path)
    if not target.parent.is_dir():
        raise OutputError(f"Output parent does not exist: {target.parent}")
    if target.exists() and not force:
        raise OutputError(f"Output already exists: {target}")
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temp_path = Path(temp_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, target)
        directory_fd = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return target


def write_json_atomic(path: str | Path, value: Any, *, force: bool = False) -> Path:
    return write_bytes_atomic(path, json_bytes(value), force=force)
