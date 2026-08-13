"""Strict configuration loading with no interpolation or inferred locations."""

from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from .exceptions import UsageError

DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": 1,
    "validation": {"mode": "standard"},
    "io": {
        "threads": 1,
        "temp_dir": None,
        "max_input_bytes": 100_000_000_000,
        "max_uncompressed_bytes": 500_000_000_000,
    },
    "reference": {"cache_dir": None, "offline": True},
    "normalization": {"profile": "conservative", "target_vcf": "4.5", "index_format": "auto"},
    "report": {"redaction": "values", "histogram_policy": "vss-bins/1"},
}

_ALLOWED_KEYS: dict[str, set[str]] = {
    "": set(DEFAULT_CONFIG),
    "validation": set(DEFAULT_CONFIG["validation"]),
    "io": set(DEFAULT_CONFIG["io"]),
    "reference": set(DEFAULT_CONFIG["reference"]),
    "normalization": set(DEFAULT_CONFIG["normalization"]),
    "report": set(DEFAULT_CONFIG["report"]),
}


class _UniqueLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: _UniqueLoader, node: yaml.MappingNode, deep: bool = False) -> Any:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise UsageError(f"Duplicate configuration key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


def _validate_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise UsageError("Configuration must be a YAML mapping")
    for key in value:
        if key not in _ALLOWED_KEYS[""]:
            raise UsageError(f"Unknown configuration key: {key}")
    if value.get("schema_version", 1) != 1:
        raise UsageError("Only configuration schema_version 1 is supported")
    for section, allowed in _ALLOWED_KEYS.items():
        if not section or section not in value:
            continue
        section_value = value[section]
        if not isinstance(section_value, dict):
            raise UsageError(f"Configuration section {section} must be a mapping")
        unknown = set(section_value) - allowed
        if unknown:
            raise UsageError(f"Unknown configuration key: {section}.{sorted(unknown)[0]}")
    return value


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    config = deepcopy(DEFAULT_CONFIG)
    if path is not None:
        source = Path(path)
        if not source.is_file():
            raise UsageError(f"Configuration file does not exist: {source}")
        try:
            parsed = yaml.load(source.read_text(encoding="utf-8"), Loader=_UniqueLoader)
        except yaml.YAMLError as exc:
            raise UsageError(f"Invalid YAML configuration: {exc}") from exc
        values = _validate_mapping(parsed)
        for key, value in values.items():
            if isinstance(value, dict):
                config[key].update(value)
            else:
                config[key] = value

    env_values = {
        "VCF_SV_STATS_THREADS": ("io", "threads", int),
        "VCF_SV_STATS_TMPDIR": ("io", "temp_dir", str),
        "VCF_SV_STATS_CACHE_DIR": ("reference", "cache_dir", str),
    }
    for env_name, (section, key, converter) in env_values.items():
        if env_name in os.environ:
            try:
                config[section][key] = converter(os.environ[env_name])
            except ValueError as exc:
                raise UsageError(f"Invalid value for {env_name}") from exc
    if not isinstance(config["io"]["threads"], int) or config["io"]["threads"] < 1:
        raise UsageError("io.threads must be a positive integer")
    if config["validation"]["mode"] not in {"compatible", "standard", "strict", "pedantic"}:
        raise UsageError("validation.mode is unsupported")
    return config


def validate_config_text(text: str) -> list[str]:
    try:
        parsed = yaml.load(text, Loader=_UniqueLoader)
        _validate_mapping(parsed)
    except (UsageError, yaml.YAMLError) as exc:
        return [str(exc)]
    return []
