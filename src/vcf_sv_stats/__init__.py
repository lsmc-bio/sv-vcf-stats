"""Standards-aware descriptive statistics for SV/CNV VCF and BCF callsets."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("vcf-sv-stats")
except PackageNotFoundError:  # pragma: no cover - only an unpackaged source tree can reach this
    try:
        from ._version import __version__
    except ImportError:
        __version__ = "0.1.0.dev0"

__all__ = ["__version__"]
