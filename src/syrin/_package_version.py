"""Package version helpers for the public ``syrin`` facade."""

from __future__ import annotations


def _get_version() -> str:
    try:
        from importlib.metadata import version

        return version("syrin")
    except Exception:
        return "0.0.0.dev"


__version__ = _get_version()
