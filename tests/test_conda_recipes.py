from __future__ import annotations

from pathlib import Path

from vcf_sv_stats import __version__

ROOT = Path(__file__).parents[1]


def test_bioconda_recipe_matches_runtime_contract() -> None:
    recipe = (ROOT / "packaging/bioconda/meta.yaml").read_text(encoding="utf-8")
    assert "name: vcf-sv-stats" in recipe
    assert "python >=3.11,<3.14" in recipe
    assert "cli-core-yo ==2.1.1" in recipe
    assert "pysam ==0.24.0" in recipe
    assert "vcf-sv-stats-verify-install" in recipe
    assert "license: Apache-2.0" in recipe
    assert "SETUPTOOLS_SCM_PRETEND_VERSION" in recipe
    assert __version__ != "0.1.0.dev0"


def test_public_only_supporting_recipes_are_digest_pinned() -> None:
    expected = {
        "cli-core-yo": "cc73bc220e48051843294f4d4d97067492ce01b41b961a1da23ad6af39153c86",
        "rfc8785": "e545841329fe0eee4f6a3b44e7034343100c12b4ec566dc06ca9735681deb4da",
    }
    for package, digest in expected.items():
        recipe = (ROOT / f"packaging/conda/{package}/meta.yaml").read_text(encoding="utf-8")
        assert "https://files.pythonhosted.org/" in recipe
        assert f"sha256: {digest}" in recipe
        assert "noarch: python" in recipe
