"""Standards-aware descriptive statistics for SV/CNV VCF and BCF callsets."""

from __future__ import annotations

try:
    from ._version import __version__
except ImportError:  # pragma: no cover - only an unpackaged source tree can reach this
    __version__ = "0.1.0.dev0"

__all__ = ["__version__"]
