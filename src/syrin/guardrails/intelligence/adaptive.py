"""Adaptive threshold guardrail that auto-tunes based on feedback."""

from __future__ import annotations

from dataclasses import dataclass

from syrin.enums import DecisionAction
from syrin.guardrails.base import Guardrail
from syrin.guardrails.context import GuardrailContext
from syrin.guardrails.decision import GuardrailDecision


@dataclass
class FeedbackRecord:
    """Record of feedback for threshold adaptation."""

    was_false_positive: bool
    was_violation: bool
    timestamp: float


class AdaptiveThresholdGuardrail(Guardrail):
    """Guardrail with adaptive threshold based on feedback.

    Automatically adjusts threshold based on:
    - False positive rate (threshold decreases if too high)
    - Missed violations (threshold increases if too low)

    Example:
        >>> guardrail = AdaptiveThresholdGuardrail(
        ...     base_threshold=0.7,
        ...     target_false_positive_rate=0.05
        ... )
        >>> result = await guardrail.evaluate(context, confidence=0.8)
        >>> guardrail.report_result(context, result, was_false_positive=False)
    """

    def __init__(
        self,
        base_threshold: float = 0.7,
        min_threshold: float = 0.3,
        max_threshold: float = 0.95,
        target_false_positive_rate: float = 0.05,
        adaptation_rate: float = 0.05,
        use_confidence: bool = True,
        name: str | None = None,
    ):
        """Initialize adaptive threshold guardrail.

        Args:
            base_threshold: Starting threshold value.
            min_threshold: Minimum allowed threshold.
            max_threshold: Maximum allowed threshold.
            target_false_positive_rate: Target false positive rate (0-1).
            adaptation_rate: Rate of threshold adjustment (0-1).
            use_confidence: Whether to use confidence scores.
            name: Optional custom name.
        """
        super().__init__(name)
        self.base_threshold = base_threshold
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self.target_false_positive_rate = target_false_positive_rate
        self.adaptation_rate = adaptation_rate
        self.use_confidence = use_confidence

        self._current_threshold = base_threshold
        self._feedback_history: list[FeedbackRecord] = []
        self._window_size = 100  # Keep last 100 feedback records

    async def evaluate(
        self, context: GuardrailContext, confidence: float | None = None
    ) -> GuardrailDecision:
        """Evaluate using adaptive threshold.

        Args:
            context: Guardrail context.
            confidence: Confidence score (0-1).

        Returns:
            GuardrailDecision.
        """
        # Get confidence
        if confidence is None:
            confidence = 0.5  # Default if not provided

        # Apply threshold
        passed = confidence >= self._current_threshold

        metadata = {
            "threshold": self._current_threshold,
            "confidence": confidence,
            "adaptation_enabled": True,
            "target_fp_rate": self.target_false_positive_rate,
        }

        if passed:
            return GuardrailDecision(passed=True, rule="adaptive_check_passed", metadata=metadata)  # type: ignore[arg-type]
        else:
            return GuardrailDecision(
                passed=False,
                rule="below_threshold",
                reason=f"Confidence {confidence:.2f} below threshold {self._current_threshold:.2f}",
                action=DecisionAction.BLOCK,
                metadata=metadata,  # type: ignore[arg-type]
            )

    def report_result(
        self,
        context: GuardrailContext,
        result: GuardrailDecision,
        was_false_positive: bool,
        was_violation: bool = False,
    ) -> None:
        """Report feedback for threshold adaptation.

        Args:
            context: Guardrail context.
            result: Result that was returned.
            was_false_positive: True if this was a false positive.
            was_violation: True if this was an actual violation (false negative).
        """
        import time

        # Record feedback
        record = FeedbackRecord(
            was_false_positive=was_false_positive,
            was_violation=was_violation,
            timestamp=time.time(),
        )
        self._feedback_history.append(record)

        # Keep only recent history
        if len(self._feedback_history) > self._window_size:
            self._feedback_history = self._feedback_history[-self._window_size :]

        # Adapt threshold
        self._adapt_threshold()

    def _adapt_threshold(self) -> None:
        """Adapt threshold based on feedback history."""
        if len(self._feedback_history) < 10:
            return  # Need more data

        # Calculate rates
        false_positives = sum(1 for f in self._feedback_history if f.was_false_positive)
        violations_missed = sum(1 for f in self._feedback_history if f.was_violation)

        fp_rate = false_positives / len(self._feedback_history)
        fn_rate = violations_missed / len(self._feedback_history)

        # Adjust threshold
        if fp_rate > self.target_false_positive_rate:
            # Too many false positives, lower threshold
            adjustment = -self.adaptation_rate * (fp_rate - self.target_false_positive_rate)
        elif fn_rate > 0.1:  # Missing more than 10% of violations
            # Missing violations, raise threshold
            adjustment = self.adaptation_rate * fn_rate
        else:
            # Within targets, small adjustment toward base
            adjustment = (
                self.adaptation_rate * 0.1 * (self.base_threshold - self._current_threshold)
            )

        # Apply adjustment with bounds
        new_threshold = self._current_threshold + adjustment
        self._current_threshold = max(self.min_threshold, min(self.max_threshold, new_threshold))

    def get_current_threshold(self) -> float:
        """Get current adaptive threshold.

        Returns:
            Current threshold value.
        """
        return self._current_threshold

    def get_stats(self) -> dict[str, object]:
        """Get adaptation statistics.

        Returns:
            Statistics dictionary.
        """
        if not self._feedback_history:
            return {
                "current_threshold": self._current_threshold,
                "feedback_count": 0,
            }

        false_positives = sum(1 for f in self._feedback_history if f.was_false_positive)
        violations_missed = sum(1 for f in self._feedback_history if f.was_violation)

        return {
            "current_threshold": self._current_threshold,
            "base_threshold": self.base_threshold,
            "min_threshold": self.min_threshold,
            "max_threshold": self.max_threshold,
            "feedback_count": len(self._feedback_history),
            "false_positive_rate": false_positives / len(self._feedback_history),
            "missed_violation_rate": violations_missed / len(self._feedback_history),
        }

    def reset(self) -> None:
        """Reset threshold to base and clear history."""
        self._current_threshold = self.base_threshold
        self._feedback_history.clear()
