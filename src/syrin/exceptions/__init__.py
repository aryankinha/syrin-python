"""Syrin exception hierarchy."""

from __future__ import annotations

from typing import Any


class SyrinError(Exception):
    """Base exception for all Syrin errors."""

    pass


class BudgetExceededError(SyrinError):
    """Raised when a budget limit is exceeded.

    Attributes:
        message: Human-readable error message.
        current_cost: Current cost or token count that exceeded the limit.
        limit: The limit that was exceeded.
        budget_type: Which limit was exceeded (str, one of BudgetLimitType values).
    """

    def __init__(
        self,
        message: str,
        current_cost: float = 0.0,
        limit: float = 0.0,
        budget_type: str | Any = "run",
    ) -> None:
        super().__init__(message)
        self.current_cost = current_cost
        self.limit = limit
        _bt = budget_type
        self.budget_type: str = _bt.value if hasattr(_bt, "value") else _bt


class BudgetThresholdError(SyrinError):
    """Raised when a budget threshold triggers an action."""

    def __init__(
        self,
        message: str,
        threshold_percent: float = 0.0,
        action_taken: str = "",
    ) -> None:
        super().__init__(message)
        self.threshold_percent = threshold_percent
        self.action_taken = action_taken


class ModelNotFoundError(SyrinError):
    """Raised when a requested model is not found in the registry."""

    pass


class ToolExecutionError(SyrinError):
    """Raised when a tool execution fails."""

    pass


class TaskError(SyrinError):
    """Raised when a task execution fails."""

    pass


class ProviderError(SyrinError):
    """Raised when an LLM provider returns an error."""

    pass


class CodegenError(SyrinError):
    """Raised when DSL code generation fails."""

    pass


class ValidationError(SyrinError):
    """Raised when structured output validation fails.

    This exception includes information about validation attempts for debugging.

    Attributes:
        message: Error message
        attempts: List of validation attempts made
        last_error: Last error that occurred
    """

    def __init__(
        self,
        message: str,
        attempts: list[str] | None = None,
        last_error: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.attempts = attempts or []
        self.last_error = last_error
