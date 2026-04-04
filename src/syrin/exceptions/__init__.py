"""Public exception package facade.

This package exposes Syrin's exception hierarchy. Import from
``syrin.exceptions`` when you need framework-level error types for budgeting,
providers, validation, handoffs, templates, or tool execution.
"""

from syrin.exceptions._core import (
    BudgetExceededError,
    BudgetThresholdError,
    CircuitBreakerOpenError,
    CodegenError,
    ForecastAbortError,
    HandoffBlockedError,
    HandoffRetryRequested,
    InputTooLargeError,
    ModalityNotSupportedError,
    ModelNotFoundError,
    NoMatchingProfileError,
    OutputValidationError,
    ProviderError,
    ProviderNotFoundError,
    SyrinError,
    TaskError,
    TemplateParseError,
    ToolArgumentError,
    ToolExecutionError,
    ValidationError,
)

__all__ = [
    "SyrinError",
    "BudgetExceededError",
    "BudgetThresholdError",
    "ForecastAbortError",
    "ModelNotFoundError",
    "ToolExecutionError",
    "ToolArgumentError",
    "TaskError",
    "ProviderError",
    "ProviderNotFoundError",
    "CodegenError",
    "ValidationError",
    "HandoffBlockedError",
    "HandoffRetryRequested",
    "ModalityNotSupportedError",
    "NoMatchingProfileError",
    "CircuitBreakerOpenError",
    "TemplateParseError",
    "OutputValidationError",
    "InputTooLargeError",
]
