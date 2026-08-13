from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from tools.build_sbom import _wheel_version


def test_sbom_version_is_bound_to_the_built_wheel(tmp_path: Path) -> None:
    wheel = tmp_path / "vcf_sv_stats-0.2.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "vcf_sv_stats-0.2.0.dist-info/METADATA",
            "Metadata-Version: 2.4\nName: vcf-sv-stats\nVersion: 0.2.0\n",
        )

    assert _wheel_version(wheel) == "0.2.0"


def test_sbom_rejects_an_unrelated_wheel(tmp_path: Path) -> None:
    wheel = tmp_path / "unrelated.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "unrelated-1.0.dist-info/METADATA",
            "Metadata-Version: 2.4\nName: unrelated\nVersion: 1.0\n",
        )

    with pytest.raises(ValueError, match="identity"):
        _wheel_version(wheel)
