"""Embedded machine-readable schema access and validation."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any, cast

import jsonschema

from vcf_sv_stats.exceptions import UsageError, ValidationFailure

SCHEMA_NAMES = (
    "summary",
    "diagnostics",
    "discrepancies",
    "distribution-qualification",
    "transforms",
    "identity",
    "install-verification",
    "oci-audit",
    "source-manifest",
    "receipt",
    "recovery-qualification",
    "streaming-benchmark",
)


def load_schema(name: str) -> dict[str, Any]:
    if name not in SCHEMA_NAMES:
        raise UsageError(f"Unknown schema: {name}")
    resource = files("vcf_sv_stats.schemas").joinpath(f"{name}-1.0.0.json")
    return cast(dict[str, Any], json.loads(resource.read_text(encoding="utf-8")))


def validate_artifact(name: str, value: Any) -> None:
    try:
        jsonschema.Draft202012Validator(load_schema(name)).validate(value)
    except jsonschema.ValidationError as exc:
        raise ValidationFailure(f"Artifact does not satisfy {name} schema: {exc.message}") from exc


__all__ = ["SCHEMA_NAMES", "load_schema", "validate_artifact"]
