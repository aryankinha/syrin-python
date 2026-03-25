"""Syrin exception hierarchy."""

from __future__ import annotations

from typing import Any


class SyrinError(Exception):
    """Base exception for all Syrin errors. Catch this for generic handling."""

    pass


class BudgetExceededError(SyrinError):
    """Raised when a budget limit is exceeded.

    Attributes:
        message: Human-readable error message.
        current_cost: Current cost or token count that exceeded the limit.
        limit: The limit that was exceeded.
        budget_type: Which limit was exceeded (str, one of BudgetLimitType values).
    """

    def __init__(  # type: ignore[explicit-any]
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
    """Raised when a budget threshold triggers a stop action.

    When a BudgetThreshold action raises stop_on_exceeded or similar,
    this is raised. Use for graceful handling when budget is nearly exhausted.

    Attributes:
        message: Error message.
        threshold_percent: Threshold percentage that was crossed.
        action_taken: Action identifier (e.g. "stop").
    """

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
    """Raised when a requested model is not found in the registry.

    Typically when ModelRegistry.resolve() cannot find a model by name.
    """

    pass


class ToolExecutionError(SyrinError):
    """Raised when a tool execution fails.

    Wraps the underlying exception. Check __cause__ for the original error.
    """

    pass


class TaskError(SyrinError):
    """Raised when a task execution fails.

    Use when AgentTask or similar task orchestration fails.
    """

    pass


class ProviderError(SyrinError):
    """Raised when an LLM provider returns an error.

    API errors, rate limits, auth failures, etc. Check message for details.
    """

    pass


class ProviderNotFoundError(SyrinError):
    """Raised when a requested provider name is not registered.

    Typically a typo in provider= or model_id prefix. Check ModelRegistry.
    """

    pass


class CodegenError(SyrinError):
    """Raised when .syrin DSL code generation fails.

    Parsing or translation errors from Syrin DSL to Python.
    """

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


class HandoffBlockedError(SyrinError):
    """Raised when handoff is blocked by a before-handler or validation.

    Emitted as Hook.HANDOFF_BLOCKED when a handler blocks the transfer.

    Attributes:
        message: Reason for blocking
        source_agent: Source agent class or name
        target_agent: Target agent class or name
        task: Task that would have been passed
    """

    def __init__(
        self,
        message: str,
        source_agent: str = "",
        target_agent: str = "",
        task: str = "",
    ) -> None:
        super().__init__(message)
        self.source_agent = source_agent
        self.target_agent = target_agent
        self.task = task


class HandoffRetryRequested(SyrinError):
    """Target agent signals: data invalid, please retry with this hint.

    Raise this from the target (or a wrapper) to ask the caller to reformat
    and retry handoff. The caller implements the retry loop.

    Attributes:
        format_hint: Instructions for correct format (e.g. JSON schema, required fields)
    """

    def __init__(self, message: str, format_hint: str = "") -> None:
        super().__init__(message)
        self.format_hint = format_hint or message


class ModalityNotSupportedError(SyrinError):
    """Raised when Agent declares input/output modalities that no router profile supports.

    Use at construction time when input_modalities or output_modalities are provided
    and the router profiles do not cover them.

    Attributes:
        message: Human-readable error.
        required: Modalities that were required.
        supported: Modalities the router profiles actually support.
    """

    def __init__(
        self,
        message: str,
        *,
        required: set[str] | None = None,
        supported: set[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.required = required or set()
        self.supported = supported or set()


class NoMatchingProfileError(SyrinError):
    """Raised when no router profile matches the required task type and modality.

    Attributes:
        message: Human-readable error message.
        required_task_type: TaskType that was required (from classification or override).
        required_modalities: Modalities present in the input that must be supported.
        available_profiles: Profile names that were considered.
    """

    def __init__(
        self,
        message: str,
        *,
        required_task_type: object = None,
        required_modalities: object = None,
        available_profiles: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.required_task_type = required_task_type
        self.required_modalities = required_modalities or set()
        self.available_profiles = available_profiles or []


class CircuitBreakerOpenError(SyrinError):
    """Raised when circuit breaker is open and request is blocked."""

    def __init__(
        self,
        message: str,
        *,
        agent_name: str = "",
        circuit_state: object = None,
        recovery_at: float = 0.0,
        fallback_model: str | None = None,
    ) -> None:
        super().__init__(message)
        self.agent_name = agent_name
        self.circuit_state = circuit_state
        self.recovery_at = recovery_at
        self.fallback_model = fallback_model
