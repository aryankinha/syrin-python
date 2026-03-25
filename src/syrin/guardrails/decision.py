"""GuardrailDecision - Structured decision from guardrail evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field

from syrin.guardrails.enums import DecisionAction


@dataclass
class GuardrailDecision:
    """Structured decision from guardrail evaluation.

    Provides comprehensive information about the evaluation result,
    including reasoning, alternatives, and metadata for debugging.

    Example:
        >>> decision = GuardrailDecision(
        ...     passed=False,
        ...     rule="blocked_word",
        ...     reason="Word 'password' is not allowed",
        ...     confidence=1.0,
        ...     alternatives=["Use 'credential' instead"]
        ... )
    """

    # Core decision
    passed: bool
    """Whether the guardrail passed (True) or failed (False)."""

    # Rule information
    rule: str = field(default="")
    """Identifier for the rule that was evaluated."""

    reason: str = field(default="")
    """Human-readable explanation of the decision."""

    # Confidence and action
    confidence: float = field(default=1.0)
    """Confidence score (0.0 to 1.0) in this decision."""

    action: DecisionAction | None = field(default=None)
    """Action to take based on this decision."""

    # Additional information
    metadata: dict[str, object] = field(default_factory=dict)
    """Arbitrary metadata about the evaluation (e.g., matched patterns)."""

    alternatives: list[str] = field(default_factory=list)
    """Suggested alternatives if the check failed."""

    # Performance tracking
    latency_ms: float = field(default=0.0)
    """Time taken to make this decision in milliseconds."""

    budget_consumed: float = field(default=0.0)
    """Budget consumed by this evaluation."""

    def __post_init__(self) -> None:
        """Set default action based on passed status if not specified."""
        if self.action is None:
            self.action = DecisionAction.PASS if self.passed else DecisionAction.BLOCK

    def to_dict(self) -> dict[str, object]:
        """Convert decision to dictionary for serialization.

        Returns:
            Dictionary representation of the decision.
        """
        return {
            "passed": self.passed,
            "rule": self.rule,
            "reason": self.reason,
            "confidence": self.confidence,
            "action": self.action.value if self.action else None,
            "metadata": self.metadata,
            "alternatives": self.alternatives,
            "latency_ms": self.latency_ms,
            "budget_consumed": self.budget_consumed,
        }

    def to_json(self) -> str:
        """Convert decision to JSON string.

        Returns:
            JSON string representation.
        """
        import json

        return json.dumps(self.to_dict(), indent=2)
