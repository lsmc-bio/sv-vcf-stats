from __future__ import annotations

import gzip
import io
import tarfile
from pathlib import Path

import pytest

from tools.normalize_sdist import normalize_sdist


def _archive(path: Path, *, timestamp: int) -> None:
    with (
        path.open("wb") as raw,
        gzip.GzipFile(fileobj=raw, mode="wb", filename=path.name, mtime=timestamp) as zipped,
        tarfile.open(fileobj=zipped, mode="w") as archive,
    ):
        info = tarfile.TarInfo("example/payload.txt")
        info.size = 7
        info.mtime = timestamp
        info.uid = 501
        info.gid = 20
        info.uname = "builder"
        archive.addfile(info, io.BytesIO(b"payload"))


def test_sdist_normalization_is_reproducible_and_owner_neutral(tmp_path: Path) -> None:
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"
    _archive(first, timestamp=100)
    _archive(second, timestamp=200)

    normalize_sdist(first, epoch=315532800)
    normalize_sdist(second, epoch=315532800)

    assert first.read_bytes() == second.read_bytes()
    with tarfile.open(first, mode="r:gz") as archive:
        member = archive.getmember("example/payload.txt")
        assert (member.uid, member.gid, member.uname, member.gname) == (0, 0, "", "")
        assert member.mtime == 315532800


def test_sdist_normalization_rejects_invalid_contract(tmp_path: Path) -> None:
    plain = tmp_path / "not-an-archive.txt"
    plain.write_text("value", encoding="utf-8")
    with pytest.raises(ValueError, match=r"tar\.gz"):
        normalize_sdist(plain, epoch=0)
