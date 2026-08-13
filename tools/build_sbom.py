#!/usr/bin/env python3
"""Build a reproducible CycloneDX SBOM without embedding checkout paths."""

from __future__ import annotations

import argparse
import email
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any, cast

from vcf_sv_stats.serialization import json_bytes


def _wheel_version(wheel: Path) -> str:
    with zipfile.ZipFile(wheel) as archive:
        metadata_names = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_names) != 1:
            raise ValueError("wheel must contain exactly one distribution metadata file")
        metadata = email.message_from_bytes(archive.read(metadata_names[0]))
    if metadata.get("Name") != "vcf-sv-stats" or metadata.get("Version") is None:
        raise ValueError("wheel identity does not match vcf-sv-stats")
    return str(metadata["Version"])


def build(output: Path, pyproject: Path, wheel: Path) -> None:
    exported = subprocess.run(
        ("uv", "export", "--locked", "--no-dev", "--no-emit-project", "--no-hashes"),
        check=True,
        capture_output=True,
    ).stdout
    with tempfile.TemporaryDirectory(prefix="vcf-sv-stats.sbom.") as directory:
        generated = Path(directory) / "sbom.json"
        subprocess.run(
            (
                "cyclonedx-py",
                "requirements",
                "--pyproject",
                str(pyproject),
                "--mc-type",
                "application",
                "--short-PURLs",
                "--output-reproducible",
                "--output-format",
                "JSON",
                "--output-file",
                str(generated),
                "-",
            ),
            check=True,
            input=exported,
        )
        value = cast(dict[str, Any], json.loads(generated.read_text(encoding="utf-8")))
    project_version = _wheel_version(wheel)
    component = value["metadata"]["component"]
    component["version"] = project_version
    component["purl"] = f"pkg:pypi/vcf-sv-stats@{component['version']}"
    component_refs = sorted(
        item["bom-ref"] for item in value.get("components", []) if "bom-ref" in item
    )
    dependencies = [
        item for item in value.get("dependencies", []) if item.get("ref") != "root-component"
    ]
    dependencies.append({"ref": "root-component", "dependsOn": component_refs})
    value["dependencies"] = sorted(dependencies, key=lambda item: item["ref"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(json_bytes(value))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--pyproject", type=Path, default=Path("pyproject.toml"))
    args = parser.parse_args()
    build(
        args.output.resolve(strict=False),
        args.pyproject.resolve(strict=True),
        args.wheel.resolve(strict=True),
    )


if __name__ == "__main__":
    main()
