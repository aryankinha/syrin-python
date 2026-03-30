"""Public budget-store package facade.

This package exposes budget persistence helpers used to save and restore
``BudgetTracker`` state across runs. Import from ``syrin.budget_store`` when you
need the high-level ``BudgetStore`` wrapper or the backend protocol for custom
storage integrations.
"""

from syrin.budget_store._core import BudgetBackend, BudgetStore, BudgetTracker

__all__ = ["BudgetStore", "BudgetBackend", "BudgetTracker"]

_ = BudgetTracker
