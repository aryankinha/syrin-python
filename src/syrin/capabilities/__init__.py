"""Public capabilities package facade.

This package exposes capability models that describe what agent inputs are
allowed. Import from ``syrin.capabilities`` for reusable capability contracts
such as input file rules.
"""

from syrin.capabilities._core import InputFileRules

__all__ = ["InputFileRules"]
