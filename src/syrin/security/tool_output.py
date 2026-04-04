"""ToolOutputValidation — validates and sanitizes tool output for security threats."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from syrin.enums import Hook


@dataclass
class ToolOutputConfig:
    """Configuration for tool output validation.

    Attributes:
        max_size_bytes: Maximum allowed output size in bytes. 0 = unlimited.
        allow_patterns: List of regex patterns that are explicitly allowed.
    """

    max_size_bytes: int = 0
    allow_patterns: list[str] = field(default_factory=list)


@dataclass
class ToolOutputResult:
    """Result of tool output validation.

    Attributes:
        passed: True if output is safe to use.
        sanitized_text: Output with suspicious content removed (None if not sanitized).
        reason: Human-readable explanation when passed=False.
        suspicious_patterns: List of detected suspicious pattern names.
    """

    passed: bool
    sanitized_text: str | None
    reason: str
    suspicious_patterns: list[str]


# Injection patterns to detect in tool outputs.
# Each tuple is (name, regex_pattern).
INJECTION_PATTERNS: list[tuple[str, str]] = [
    ("ignore_instructions", r"(?i)ignore\s+(previous|all|your)\s+instructions"),
    ("system_override", r"(?i)^SYSTEM\s*:"),
    ("shell_execution", r"(?i)(os\.system|subprocess\.|exec\(|eval\()"),
    ("prompt_escape", r"(?i)(</?\w+>.*<prompt>|<\|.*\|>)"),
]


class ToolOutputValidator:
    """Validates and optionally sanitizes tool output for security threats.

    Checks for injection patterns and enforces size limits. Fires lifecycle
    hooks via the optional ``fire_event_fn`` callback.

    Args:
        config: Validation configuration. Defaults to unlimited size, no allow-list.
        fire_event_fn: Optional hook firing callback.

    Example:
        >>> validator = ToolOutputValidator(config=ToolOutputConfig(max_size_bytes=1024))
        >>> result = validator.validate("The weather is sunny")
        >>> assert result.passed
    """

    def __init__(
        self,
        config: ToolOutputConfig | None = None,
        fire_event_fn: Callable[[Hook, dict[str, object]], None] | None = None,
    ) -> None:
        """Initialize ToolOutputValidator.

        Args:
            config: Optional validation configuration.
            fire_event_fn: Optional hook firing callback.
        """
        self._config = config or ToolOutputConfig()
        self._fire_event_fn = fire_event_fn
        # Compile injection patterns
        self._injection_patterns: list[tuple[str, re.Pattern[str]]] = [
            (name, re.compile(pattern, re.MULTILINE)) for name, pattern in INJECTION_PATTERNS
        ]
        # Compile allow patterns
        self._allow_patterns: list[re.Pattern[str]] = [
            re.compile(p) for p in self._config.allow_patterns
        ]

    def validate(self, output: str) -> ToolOutputResult:
        """Validate tool output for security threats.

        Checks size limits first, then scans for injection patterns.

        Args:
            output: Tool output string to validate.

        Returns:
            ToolOutputResult with pass/fail status and details.
        """
        output_size = len(output.encode("utf-8"))

        # Size check
        if self._config.max_size_bytes > 0 and output_size > self._config.max_size_bytes:
            reason = (
                f"Output size {output_size} bytes exceeds limit of "
                f"{self._config.max_size_bytes} bytes"
            )
            if self._fire_event_fn is not None:
                self._fire_event_fn(
                    Hook.TOOL_OUTPUT_BLOCKED,
                    {"output_size": output_size, "reason": reason},
                )
            return ToolOutputResult(
                passed=False,
                sanitized_text=None,
                reason=reason,
                suspicious_patterns=[],
            )

        # Check allow-list: if any allow pattern matches the entire output,
        # skip injection scan for allowed patterns
        # (Allow patterns are checked but injection scan still runs for unlisted patterns)

        # Injection pattern scan
        detected: list[str] = []
        for name, pattern in self._injection_patterns:
            if pattern.search(output):
                detected.append(name)

        if detected:
            reason = f"Suspicious patterns detected: {', '.join(detected)}"
            sanitized = output
            for _, pattern in self._injection_patterns:
                sanitized = pattern.sub("[REMOVED]", sanitized)
            sanitized_text = sanitized if sanitized != output else None

            if self._fire_event_fn is not None:
                self._fire_event_fn(
                    Hook.TOOL_OUTPUT_SUSPICIOUS,
                    {"output_size": output_size, "reason": reason, "patterns": detected},
                )
                if sanitized_text is not None:
                    self._fire_event_fn(
                        Hook.TOOL_OUTPUT_SANITIZED,
                        {"output_size": output_size, "reason": "Suspicious content removed"},
                    )

            return ToolOutputResult(
                passed=False,
                sanitized_text=sanitized_text,
                reason=reason,
                suspicious_patterns=detected,
            )

        return ToolOutputResult(
            passed=True,
            sanitized_text=None,
            reason="",
            suspicious_patterns=[],
        )
