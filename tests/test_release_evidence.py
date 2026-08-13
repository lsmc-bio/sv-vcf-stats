from __future__ import annotations

import io
import json
import tarfile
import zipfile
from pathlib import Path

import pytest
from cyclonedx.schema import SchemaVersion
from cyclonedx.validation.json import JsonStrictValidator
from spdx_tools.spdx.parser.jsonlikedict.json_like_dict_parser import JsonLikeDictParser
from spdx_tools.spdx.validation.document_validator import validate_full_spdx_document

import tools.build_release_evidence as release_evidence
from tools.build_release_evidence import _inventory, build
from vcf_sv_stats.exceptions import UsageError

ROOT = Path(__file__).parents[1]


def _candidate_artifacts(directory: Path) -> tuple[Path, Path]:
    wheel = directory / "vcf_sv_stats-0.2.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "vcf_sv_stats-0.2.0.dist-info/METADATA",
            "Metadata-Version: 2.4\nName: vcf-sv-stats\nVersion: 0.2.0\n",
        )
    sdist = directory / "vcf_sv_stats-0.2.0.tar.gz"
    pkg_info = b"Metadata-Version: 2.4\nName: vcf-sv-stats\nVersion: 0.2.0\n"
    with tarfile.open(sdist, "w:gz") as archive:
        member = tarfile.TarInfo("vcf_sv_stats-0.2.0/PKG-INFO")
        member.size = len(pkg_info)
        archive.addfile(member, io.BytesIO(pkg_info))
        nested = tarfile.TarInfo("vcf_sv_stats-0.2.0/src/vcf_sv_stats.egg-info/PKG-INFO")
        nested_payload = pkg_info.replace(b"Version: 0.2.0", b"Version: 9.9.9")
        nested.size = len(nested_payload)
        archive.addfile(nested, io.BytesIO(nested_payload))
    return wheel, sdist


def test_license_inventory_exactly_matches_runtime_lock() -> None:
    value = _inventory(ROOT / "packaging/runtime-licenses.json", ROOT / "requirements.lock.txt")
    assert value["project"]["license_expression"] == "Apache-2.0"
    assert any(item["name"] == "htslib" for item in value["native"])
    assert value["fixtures"]["public_release_review_required"] is False


def test_release_evidence_binds_candidate_artifacts(tmp_path: Path) -> None:
    wheel, sdist = _candidate_artifacts(tmp_path)
    result = build(
        wheel=wheel,
        sdist=sdist,
        output_dir=tmp_path,
        source_commit="a" * 40,
        created="2026-08-13T00:00:00Z",
        invocation_id="local-test",
    )

    cyclonedx = json.loads(result["cyclonedx"].read_text())
    spdx = json.loads(result["spdx"].read_text())
    provenance = json.loads(result["provenance"].read_text())
    assert cyclonedx["metadata"]["component"]["version"] == "0.2.0"
    assert spdx["spdxVersion"] == "SPDX-2.3"
    assert provenance["predicateType"] == "https://slsa.dev/provenance/v1"
    assert {item["name"] for item in provenance["subject"]} == {wheel.name, sdist.name}
    checksums = result["checksums"].read_text()
    assert wheel.name in checksums
    assert result["spdx"].name in checksums
    assert (
        JsonStrictValidator(SchemaVersion.V1_6).validate_str(result["cyclonedx"].read_text())
        is None
    )
    parsed_spdx = JsonLikeDictParser().parse(spdx)
    assert validate_full_spdx_document(parsed_spdx) == []


def test_release_evidence_rejects_fixture_integrity_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel, sdist = _candidate_artifacts(tmp_path)

    def fail_fixture_verification(_root: Path) -> dict[str, int]:
        raise ValueError("fixture digest mismatch")

    monkeypatch.setattr(release_evidence, "verify_test_data", fail_fixture_verification)
    with pytest.raises(UsageError, match="fixture corpus failed strict release verification"):
        build(
            wheel=wheel,
            sdist=sdist,
            output_dir=tmp_path,
            source_commit="a" * 40,
            created="2026-08-13T00:00:00Z",
            invocation_id="local-test",
        )
