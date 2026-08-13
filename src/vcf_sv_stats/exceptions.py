"""Typed errors returned by the library and converted only at the CLI boundary."""

from __future__ import annotations


class VcfSvStatsError(Exception):
    """Base class for expected product failures."""

    code = "VCFSVSTATS_ERROR"


class UsageError(VcfSvStatsError):
    """The request is malformed or internally contradictory."""

    code = "VCFSVSTATS_USAGE"


class InputError(VcfSvStatsError):
    """The input cannot be read safely."""

    code = "VCFSVSTATS_INPUT"


class ValidationFailure(VcfSvStatsError):
    """The input violates the requested validation contract."""

    code = "VCFSVSTATS_VALIDATION"


class OutputError(VcfSvStatsError):
    """An output cannot be staged, validated, or published safely."""

    code = "VCFSVSTATS_OUTPUT"


class ReferenceError(VcfSvStatsError):
    """A reference request is unsupported or cannot be verified."""

    code = "VCFSVSTATS_REFERENCE"
