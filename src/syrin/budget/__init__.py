"""Public budget package facade.

This package exposes Syrin's budgeting and token-limit API while keeping the
implementation in private modules. Import from ``syrin.budget`` when you need
cost budgets, token caps, budget tracking, threshold handlers, or related
summary/state models.

Why use this package:
    - Define per-run and rolling-window cost budgets.
    - Configure token caps separately from dollar-based limits.
    - Inspect accumulated usage and react to thresholds or limit breaches.
    - Reuse built-in exceed handlers such as raise, warn, or stop behaviors.

Typical usage:
    >>> from syrin.budget import Budget, TokenLimits, TokenRateLimit, raise_on_exceeded
    >>> budget = Budget(max_cost=1.0, on_exceeded=raise_on_exceeded)
    >>> token_limits = TokenLimits(max_tokens=50_000, rate_limits=TokenRateLimit(hour=200_000))

Exported surface:
    - ``Budget`` and ``BudgetTracker`` for budgeting configuration and runtime tracking
    - ``TokenLimits`` and ``TokenRateLimit`` for token-based caps
    - ``BudgetState`` and summary/result models for reporting
    - built-in exceed handlers and enums used throughout the public API
"""

from syrin.budget._core import (
    Budget,
    BudgetExceededContext,
    BudgetLimitType,
    BudgetReservationToken,
    BudgetState,
    BudgetStatus,
    BudgetSummary,
    BudgetThreshold,
    BudgetTracker,
    CheckBudgetResult,
    CostEntry,
    ExceedPolicy,
    ModelPricing,
    Pricing,
    RateLimit,
    TokenLimits,
    TokenRateLimit,
    raise_on_exceeded,
    stop_on_exceeded,
    warn_on_exceeded,
)

__all__ = [
    "Budget",
    "BudgetExceededContext",
    "BudgetState",
    "BudgetLimitType",
    "BudgetReservationToken",
    "BudgetStatus",
    "BudgetSummary",
    "BudgetTracker",
    "CheckBudgetResult",
    "CostEntry",
    "ExceedPolicy",
    "ModelPricing",
    "Pricing",
    "RateLimit",
    "TokenLimits",
    "TokenRateLimit",
    "raise_on_exceeded",
    "stop_on_exceeded",
    "BudgetThreshold",
    "warn_on_exceeded",
]
