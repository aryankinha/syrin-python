"""Validation types for structured output validation."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol


class ValidationAction(StrEnum):
    """What to do when validation fails."""

    RETRY = "retry"
    STOP = "stop"
    FALLBACK = "fallback"


@dataclass
class ValidationAttempt:
    """Single validation attempt for structured output.

    Attributes:
        attempt: Attempt number (1-based).
        raw_output: Raw string from model.
        parsed: Parsed output if successful.
        error: Error message if failed.
        timestamp: When attempt occurred.
    """

    attempt: int
    raw_output: str
    parsed: object | None = None
    error: str | None = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class ValidationResult:
    """Result of structured output validation.

    Attributes:
        is_valid: Whether validation succeeded.
        parsed: Parsed output if valid.
        message: Error message if invalid.
        action: RETRY, STOP, or FALLBACK.
        hint: Hint for retry (e.g. schema correction).
    """

    is_valid: bool
    parsed: object | None = None
    message: str = ""
    action: ValidationAction = ValidationAction.STOP
    hint: str = ""

    @classmethod
    def valid(cls, parsed: object) -> ValidationResult:
        return cls(is_valid=True, parsed=parsed)

    @classmethod
    def invalid(
        cls,
        message: str,
        action: ValidationAction = ValidationAction.STOP,
        hint: str = "",
    ) -> ValidationResult:
        return cls(
            is_valid=False,
            message=message,
            action=action,
            hint=hint,
        )


@dataclass
class ValidationContext:
    """Context passed to OutputValidator.validate().

    Attributes:
        raw_output: Raw string from model.
        attempt: Current attempt number.
        max_attempts: Max attempts allowed.
        user_context: Custom context from Output(context=...).
        llm_messages: Messages sent to model (for retry hints).
    """

    raw_output: str
    attempt: int
    max_attempts: int
    user_context: dict[str, object] = field(default_factory=dict)
    llm_messages: list[dict[str, object]] = field(default_factory=list)


class OutputValidator(Protocol):
    """Protocol for custom output validators.

    Implement this to create custom validation logic:

    class MyValidator:
        max_retries: int = 3
        backoff_factor: float = 1.0

        def validate(self, output: object, context: ValidationContext) -> ValidationResult:
            # Custom validation logic
            if not meets_requirements(output):
                return ValidationResult.invalid(
                    message="Validation failed",
                    action=ValidationAction.RETRY,
                    hint="Fix the following issues..."
                )
            return ValidationResult.valid(output)

        def on_retry(self, error: Exception, attempt: int) -> str:
            # Return prompt to inject on retry
            return f"Error: {error}. Please fix and try again."
    """

    max_retries: int = 3
    backoff_factor: float = 1.0

    def validate(self, output: object, context: ValidationContext) -> ValidationResult:
        """Validate output. Return ValidationResult."""
        ...

    def on_retry(self, error: Exception, attempt: int) -> str:
        """Return prompt to inject on retry."""
        ...


@dataclass
class ToolOutput:
    """Container for tool-based output type.

    Used when an agent can return different shapes of output.

    Example:
        output_type=[
            ToolOutput(SuccessResult, name="success"),
            ToolOutput(ErrorResult, name="error"),
        ]
    """

    output: type
    name: str
    description: str = ""
    max_retries: int | None = None
    strict: bool | None = None

    def get_schema(self) -> dict[str, object]:
        """Get JSON schema for this output type."""
        if hasattr(self.output, "model_json_schema"):
            result = self.output.model_json_schema()
            if isinstance(result, dict):
                return result
        return {}
