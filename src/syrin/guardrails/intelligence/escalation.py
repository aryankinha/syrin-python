"""Escalation detection guardrail for detecting bypass attempts."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from syrin.enums import DecisionAction
from syrin.guardrails.base import Guardrail
from syrin.guardrails.context import GuardrailContext
from syrin.guardrails.decision import GuardrailDecision


@dataclass
class ViolationRecord:
    """Record of a single violation."""

    rule: str
    text: str
    timestamp: datetime


@dataclass
class TacticRecord:
    """Record of a tactic used."""

    tactic: str
    text: str
    timestamp: datetime


class EscalationDetector(Guardrail):
    """Guardrail that detects escalation patterns and bypass attempts.

    Tracks violations and tactics per user to detect:
    - Spike in violations
    - Progressive escalation of tactics
    - Repeated attempts

    Example:
        >>> detector = EscalationDetector(max_violations=3, time_window=300)
        >>> detector.record_violation("user_123", "content_filter", "blocked")
        >>> result = await detector.evaluate(context)
    """

    def __init__(
        self,
        max_violations: int = 5,
        time_window: int = 300,  # 5 minutes
        escalation_threshold: float = 0.7,
        name: str | None = None,
    ):
        """Initialize escalation detector.

        Args:
            max_violations: Maximum violations before escalation.
            time_window: Time window in seconds for violation tracking.
            escalation_threshold: Score threshold for escalation detection.
            name: Optional custom name.
        """
        super().__init__(name)
        self.max_violations = max_violations
        self.time_window = time_window
        self.escalation_threshold = escalation_threshold

        # Track violations per user
        self._violations: dict[str, list[ViolationRecord]] = defaultdict(list)

        # Track tactics per user
        self._tactics: dict[str, list[TacticRecord]] = defaultdict(list)

    async def evaluate(self, context: GuardrailContext) -> GuardrailDecision:
        """Check for escalation patterns.

        Args:
            context: Guardrail context.

        Returns:
            GuardrailDecision indicating escalation status.
        """
        user_id = self._get_user_id(context)

        # Clean old records
        self._clean_old_records(user_id)

        # Count recent violations
        violation_count = len(self._violations[user_id])

        # Check for violation spike
        if violation_count >= self.max_violations:
            return GuardrailDecision(
                passed=False,
                rule="escalation_detected",
                reason=f"Too many violations: {violation_count} in {self.time_window}s",
                action=DecisionAction.BLOCK,
                metadata={
                    "violation_count": violation_count,
                    "max_allowed": self.max_violations,
                    "time_window": self.time_window,
                    "user_id": user_id,
                    "escalation_type": "violation_spike",
                },
                alternatives=[
                    "Wait before making additional requests",
                    "Contact support if you believe this is an error",
                ],
            )

        # Calculate escalation score
        escalation_score = self._calculate_escalation_score(user_id)

        if escalation_score >= self.escalation_threshold:
            tactics = [t.tactic for t in self._tactics[user_id]]
            return GuardrailDecision(
                passed=False,
                rule="escalation_detected",
                reason=f"Escalation pattern detected (score: {escalation_score:.2f})",
                action=DecisionAction.BLOCK,
                metadata={
                    "escalation_score": escalation_score,
                    "threshold": self.escalation_threshold,
                    "tactics_used": len(tactics),
                    "tactics": tactics,
                    "user_id": user_id,
                    "escalation_type": "tactic_progression",
                },
            )

        # No escalation detected
        return GuardrailDecision(
            passed=True,
            rule="no_escalation",
            metadata={
                "violation_count": violation_count,
                "tactics_used": len(self._tactics[user_id]),
                "escalation_score": escalation_score,
                "user_id": user_id,
            },
        )

    def record_violation(
        self, user_id: str, rule: str, text: str, timestamp: datetime | None = None
    ) -> None:
        """Record a violation for a user.

        Args:
            user_id: User identifier.
            rule: Rule that was violated.
            text: Text that caused violation.
            timestamp: Optional timestamp.
        """
        record = ViolationRecord(rule=rule, text=text, timestamp=timestamp or datetime.now())
        self._violations[user_id].append(record)
        self._clean_old_records(user_id)

    def record_tactic(
        self, user_id: str, tactic: str, text: str, timestamp: datetime | None = None
    ) -> None:
        """Record a tactic used by a user.

        Args:
            user_id: User identifier.
            tactic: Tactic type (e.g., "encoding", "social_engineering").
            text: Text using the tactic.
            timestamp: Optional timestamp.
        """
        record = TacticRecord(tactic=tactic, text=text, timestamp=timestamp or datetime.now())
        self._tactics[user_id].append(record)
        self._clean_old_records(user_id)

    def _get_user_id(self, context: GuardrailContext) -> str:
        """Extract user ID from context.

        Args:
            context: Guardrail context.

        Returns:
            User identifier.
        """
        if context.user and hasattr(context.user, "id"):
            return str(context.user.id)
        return str(context.metadata.get("user_id", "anonymous"))

    def _clean_old_records(self, user_id: str) -> None:
        """Remove old records outside time window.

        Args:
            user_id: User to clean.
        """
        cutoff = datetime.now() - timedelta(seconds=self.time_window)

        # Clean violations
        self._violations[user_id] = [v for v in self._violations[user_id] if v.timestamp > cutoff]

        # Clean tactics
        self._tactics[user_id] = [t for t in self._tactics[user_id] if t.timestamp > cutoff]

    def _calculate_escalation_score(self, user_id: str) -> float:
        """Calculate escalation score based on tactics.

        Args:
            user_id: User to check.

        Returns:
            Escalation score (0.0 to 1.0).
        """
        tactics = self._tactics[user_id]
        if not tactics:
            return 0.0

        # Count unique tactics
        unique_tactics = {t.tactic for t in tactics}

        # More unique tactics = higher escalation
        # Weight by recency
        score = 0.0
        for i, _tactic in enumerate(tactics):
            # Later tactics weighted more
            weight = (i + 1) / len(tactics)
            score += 0.1 * weight

        # Bonus for diversity of tactics
        score += len(unique_tactics) * 0.15

        return min(score, 1.0)

    def get_stats(self, user_id: str | None = None) -> dict[str, object]:
        """Get escalation statistics.

        Args:
            user_id: Specific user or None for all.

        Returns:
            Statistics dictionary.
        """
        if user_id:
            return {
                "user_id": user_id,
                "violation_count": len(self._violations[user_id]),
                "tactic_count": len(self._tactics[user_id]),
                "escalation_score": self._calculate_escalation_score(user_id),
            }
        else:
            return {
                "total_users": len(set(self._violations.keys()) | set(self._tactics.keys())),
                "total_violations": sum(len(v) for v in self._violations.values()),
                "total_tactics": sum(len(t) for t in self._tactics.values()),
            }
