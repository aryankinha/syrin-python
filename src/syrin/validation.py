"""Validation pipeline for structured output validation with retries."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel

from syrin.exceptions import ValidationError
from syrin.types.validation import (
    OutputValidator,
    ValidationAction,
    ValidationAttempt,
    ValidationContext,
)

if TYPE_CHECKING:
    from syrin.enums import Hook
    from syrin.events import EventContext


class ValidationPipeline:
    """Manages structured output validation with retries.

    This pipeline handles:
    1. JSON extraction from raw LLM output (handles markdown, etc.)
    2. Pydantic model validation
    3. Custom output validator (optional)
    4. Retry logic with exponential backoff
    5. Lifecycle hooks for observability

    Example:
        pipeline = ValidationPipeline(
            output_type=UserInfo,
            max_retries=3,
            validator=MyCustomValidator(),
            context={"allowed_domains": ["company.com"]}
        )

        parsed, attempts, error = pipeline.validate(raw_llm_output)
    """

    def __init__(
        self,
        output_type: type,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        validator: OutputValidator | None = None,
        context: dict[str, object] | None = None,
        emit_fn: Callable[[Hook, EventContext], None] | None = None,
    ):
        """Initialize validation pipeline.

        Args:
            output_type: Pydantic model to validate against
            max_retries: Maximum number of validation attempts
            backoff_factor: Exponential backoff factor between retries
            validator: Optional custom output validator
            context: Optional context dict passed to validators
            emit_fn: Optional function to emit hooks (hook_enum, event_context)
        """
        self.output_type = output_type
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.validator = validator
        self.context: dict[str, object] = context or {}
        self.attempts: list[ValidationAttempt] = []
        self._emit_fn = emit_fn

    def validate(  # type: ignore[explicit-any]
        self,
        raw_output: str,
        llm_messages: list[dict[str, object]] | None = None,
    ) -> tuple[Any, list[ValidationAttempt], Exception | None]:
        """Validate raw output with retries.

        Args:
            raw_output: Raw string from LLM
            llm_messages: Optional LLM message history for debugging

        Returns:
            Tuple of (parsed_object, attempts_list, final_error)
            - parsed_object: Validated Pydantic model or None
            - attempts_list: List of all validation attempts
            - final_error: Exception if validation failed, None if successful
        """
        from syrin.enums import Hook
        from syrin.events import EventContext

        llm_messages = llm_messages or []
        self.attempts = []

        # Emit validation start hook
        if self._emit_fn:
            self._emit_fn(
                Hook.OUTPUT_VALIDATION_START,
                EventContext(
                    output_type=self.output_type.__name__,
                    max_retries=self.max_retries,
                    raw_output=raw_output[:500] if raw_output else "",
                ),
            )

        for attempt in range(1, self.max_retries + 1):
            # Emit attempt hook
            if self._emit_fn:
                self._emit_fn(
                    Hook.OUTPUT_VALIDATION_ATTEMPT,
                    EventContext(
                        attempt=attempt,
                        output_type=self.output_type.__name__,
                    ),
                )

            # Parse JSON from raw text
            parsed, parse_error = self._parse_json(raw_output)

            if parse_error:
                attempt_record = ValidationAttempt(
                    attempt=attempt,
                    raw_output=raw_output,
                    parsed=None,
                    error=f"JSON parse error: {parse_error}",
                )
                self.attempts.append(attempt_record)

                # Emit retry hook
                if self._emit_fn and attempt < self.max_retries:
                    self._emit_fn(
                        Hook.OUTPUT_VALIDATION_RETRY,
                        EventContext(
                            attempt=attempt,
                            error=str(parse_error),
                            reason="json_parse_error",
                        ),
                    )

                # Check if we should retry
                if attempt < self.max_retries:
                    raw_output = self._build_retry_prompt(
                        parse_error, attempt, "Invalid JSON format"
                    )
                    self._wait_backoff(attempt)
                    continue
                else:
                    # Emit failed hook
                    if self._emit_fn:
                        self._emit_fn(
                            Hook.OUTPUT_VALIDATION_FAILED,
                            EventContext(
                                attempt=attempt,
                                error=str(parse_error),
                                reason="json_parse_error",
                            ),
                        )
                    return None, self.attempts, parse_error

            # Pydantic validation
            pydantic_error, validated_model = self._validate_pydantic(parsed)

            if pydantic_error:
                attempt_record = ValidationAttempt(
                    attempt=attempt,
                    raw_output=raw_output,
                    parsed=None,
                    error=str(pydantic_error),
                )
                self.attempts.append(attempt_record)

                # Emit retry hook for pydantic error
                if self._emit_fn and attempt < self.max_retries:
                    self._emit_fn(
                        Hook.OUTPUT_VALIDATION_RETRY,
                        EventContext(
                            attempt=attempt,
                            error=str(pydantic_error),
                            reason="pydantic_validation_error",
                        ),
                    )

                if attempt < self.max_retries:
                    raw_output = self._build_retry_prompt(
                        pydantic_error, attempt, str(pydantic_error)
                    )
                    self._wait_backoff(attempt)
                    continue
                else:
                    # Emit failed hook
                    if self._emit_fn:
                        self._emit_fn(
                            Hook.OUTPUT_VALIDATION_FAILED,
                            EventContext(
                                attempt=attempt,
                                error=str(pydantic_error),
                                reason="pydantic_validation_error",
                            ),
                        )
                    return None, self.attempts, pydantic_error

            # Use the validated model (not the raw dict)
            parsed = validated_model

            # Custom validator (if provided)
            if self.validator:
                validation_ctx = ValidationContext(
                    raw_output=raw_output,
                    attempt=attempt,
                    max_attempts=self.max_retries,
                    user_context=self.context,
                    llm_messages=llm_messages,
                )
                result = self.validator.validate(parsed, validation_ctx)

                if not result.is_valid:
                    attempt_record = ValidationAttempt(
                        attempt=attempt,
                        raw_output=raw_output,
                        parsed=parsed,
                        error=result.message,
                    )
                    self.attempts.append(attempt_record)

                    if result.action == ValidationAction.RETRY and attempt < self.max_retries:
                        hint = result.hint or f"Error: {result.message}"
                        raw_output = self._build_retry_prompt(
                            Exception(result.message), attempt, hint
                        )
                        self._wait_backoff(attempt)
                        continue
                    elif result.action == ValidationAction.STOP:
                        return (
                            None,
                            self.attempts,
                            ValidationError(result.message),
                        )

            # SUCCESS!
            attempt_record = ValidationAttempt(
                attempt=attempt,
                raw_output=raw_output,
                parsed=parsed,
                error=None,
            )
            self.attempts.append(attempt_record)

            # Emit success hook
            if self._emit_fn:
                self._emit_fn(
                    Hook.OUTPUT_VALIDATION_SUCCESS,
                    EventContext(
                        attempt=attempt,
                        output_type=self.output_type.__name__,
                        parsed_fields=list(parsed.model_fields.keys())
                        if hasattr(parsed, "model_fields")
                        else [],
                    ),
                )

            return parsed, self.attempts, None

        # Exhausted retries - emit final failed hook
        final_error = ValidationError(f"Validation failed after {self.max_retries} attempts")

        if self._emit_fn:
            self._emit_fn(
                Hook.OUTPUT_VALIDATION_FAILED,
                EventContext(
                    attempt=self.max_retries,
                    error=str(final_error),
                    reason="max_retries_exceeded",
                    total_attempts=len(self.attempts),
                ),
            )

        return None, self.attempts, final_error

    def _parse_json(
        self, raw: str
    ) -> tuple[dict[str, object] | list[object] | None, Exception | None]:
        """Extract and parse JSON from raw text.

        Handles:
        - Markdown code blocks (```json, ```)
        - Text before/after JSON
        - Whitespace

        Args:
            raw: Raw string to parse

        Returns:
            Tuple of (parsed_data, error)
        """
        try:
            text = raw.strip()

            # Strip markdown code blocks
            if text.startswith("```"):
                parts = text.split("```")
                if len(parts) >= 3:
                    text = parts[1]
                    # Remove language identifier if present
                    if text.startswith("json"):
                        text = text[4:]
                    elif text.startswith("javascript"):
                        text = text[10:]
                text = text.strip()

            # Try to find JSON in the text if not pure JSON
            # Handle common cases like "Here is the JSON: {...}" or "```json\n{...}"
            if not text.startswith("{") and not text.startswith("["):
                # Try object first
                start = text.find("{")
                if start != -1:
                    # Find matching closing brace
                    depth = 0
                    end = start
                    for i, char in enumerate(text[start:], start):
                        if char == "{":
                            depth += 1
                        elif char == "}":
                            depth -= 1
                            if depth == 0:
                                end = i + 1
                                break
                    if end > start:
                        text = text[start:end]
                else:
                    # Try array
                    start = text.find("[")
                    if start != -1:
                        depth = 0
                        end = start
                        for i, char in enumerate(text[start:], start):
                            if char == "[":
                                depth += 1
                            elif char == "]":
                                depth -= 1
                                if depth == 0:
                                    end = i + 1
                                    break
                        if end > start:
                            text = text[start:end]

            return json.loads(text), None

        except Exception as e:
            return None, e

    def _validate_pydantic(self, data: object) -> tuple[Exception | None, Any]:  # type: ignore[explicit-any]
        """Validate against Pydantic model.

        Args:
            data: Parsed data to validate

        Returns:
            Tuple of (error, validated_model)
            - error: Exception if validation fails, None if successful
            - validated_model: Validated Pydantic model or original data
        """
        try:
            if data is None:
                return ValueError("No data to validate"), None

            # Import ValidationError from pydantic
            from pydantic import ValidationError as PydanticValidationError

            if isinstance(data, dict):
                validated = cast(type[BaseModel], self.output_type).model_validate(data)
                return None, validated
            elif isinstance(data, list):
                # For list outputs, validate each item
                validated_items: list[object] = []
                for item in data:
                    if isinstance(item, dict):
                        validated_items.append(
                            cast(type[BaseModel], self.output_type).model_validate(item)
                        )
                    else:
                        validated_items.append(item)
                return None, validated_items
            return None, data
        except PydanticValidationError as e:
            return e, None
        except Exception as e:
            return e, None

    def _build_retry_prompt(
        self,
        error: Exception,
        attempt: int,
        hint: str,
    ) -> str:
        """Build prompt for retry with error context.

        Args:
            error: The error that occurred
            attempt: Current attempt number
            hint: Hint about what went wrong

        Returns:
            Retry prompt string
        """
        return f"""Previous output failed validation:

Error: {hint}

Please fix and return valid JSON matching the required schema.

Required schema:
{self._get_schema_str()}
"""

    def _get_schema_str(self) -> str:
        """Get JSON schema as string."""
        try:
            if hasattr(self.output_type, "model_json_schema"):
                schema = self.output_type.model_json_schema()
                return json.dumps(schema, indent=2)
            elif hasattr(self.output_type, "schema"):
                return json.dumps(self.output_type.schema(), indent=2)
            return str(self.output_type)
        except Exception:
            return str(self.output_type)

    def _wait_backoff(self, attempt: int) -> None:
        """Wait before retry with exponential backoff.

        Args:
            attempt: Current attempt number
        """
        if self.backoff_factor > 0 and attempt > 1:
            wait_time = self.backoff_factor * (attempt - 1)
            time.sleep(wait_time)


def get_retry_prompt(output_type: type, error_message: str) -> str:
    """Build the prompt to send to the LLM when structured output validation fails.

    Use this when the agent runs validation and wants to retry by calling the model
    again with the validation error so it can fix the output.

    Args:
        output_type: Pydantic model class used for structured output.
        error_message: The validation error message to include.

    Returns:
        A prompt string to send as the next user message.
    """
    schema_str = _schema_str_for_type(output_type)
    return f"""Previous output failed validation:

Error: {error_message}

Please fix and return valid JSON matching the required schema.

Required schema:
{schema_str}
"""


def _schema_str_for_type(output_type: type) -> str:
    """Get JSON schema string for a Pydantic model type."""
    try:
        if hasattr(output_type, "model_json_schema"):
            return json.dumps(output_type.model_json_schema(), indent=2)
        if hasattr(output_type, "schema"):
            return json.dumps(output_type.schema(), indent=2)
    except Exception:
        pass
    return str(output_type)


def validate_output(  # type: ignore[explicit-any]
    output_type: type,
    raw_output: str,
    max_retries: int = 3,
    context: dict[str, object] | None = None,
) -> tuple[Any, list[ValidationAttempt], Exception | None]:
    """Convenience function for simple validation.

    Args:
        output_type: Pydantic model to validate against
        raw_output: Raw string from LLM
        max_retries: Maximum validation attempts
        context: Optional validation context

    Returns:
        Tuple of (parsed_object, attempts, error)
    """
    pipeline = ValidationPipeline(
        output_type=output_type,
        max_retries=max_retries,
        context=context,
    )
    return pipeline.validate(raw_output)
