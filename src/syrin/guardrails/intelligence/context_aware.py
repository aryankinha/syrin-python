"""Context awareness guardrail for multi-turn conversation tracking."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from syrin.guardrails.base import Guardrail
from syrin.guardrails.context import GuardrailContext
from syrin.guardrails.decision import GuardrailDecision


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""

    text: str
    timestamp: float
    metadata: dict[str, object] = field(default_factory=dict)


class ContextAwareGuardrail(Guardrail):
    """Guardrail that tracks multi-turn conversation context.

    Maintains conversation history and detects patterns like:
    - Topic escalation
    - Repeated attempts
    - Session-based tracking

    Example:
        >>> guardrail = ContextAwareGuardrail(max_history_turns=10)
        >>> result = await guardrail.evaluate(context)
        >>> # Access conversation history in result
    """

    def __init__(
        self,
        max_history_turns: int = 20,
        escalation_patterns: list[tuple[str, ...]] | None = None,
        name: str | None = None,
    ):
        """Initialize context-aware guardrail.

        Args:
            max_history_turns: Maximum turns to keep per session.
            escalation_patterns: List of topic escalation patterns to detect.
            name: Optional custom name.
        """
        super().__init__(name)
        self.max_history_turns = max_history_turns
        self.escalation_patterns = escalation_patterns or []

        # Track conversations per session: session_id -> list of turns
        self._history: dict[str, list[ConversationTurn]] = defaultdict(list)

        # Track action attempts: (session_id, action) -> count
        self._action_counts: dict[tuple[str, str], int] = defaultdict(int)

    async def evaluate(self, context: GuardrailContext) -> GuardrailDecision:
        """Evaluate with context awareness.

        Args:
            context: Guardrail context.

        Returns:
            GuardrailDecision with context metadata.
        """
        import time

        session_id = context.metadata.get("session_id", "default")

        # Record this turn
        turn = ConversationTurn(
            text=context.text, timestamp=time.time(), metadata=context.metadata.copy()
        )

        self._history[session_id].append(turn)  # type: ignore[index]

        # Enforce history limit
        if len(self._history[session_id]) > self.max_history_turns:  # type: ignore[index]
            self._history[session_id] = self._history[session_id][-self.max_history_turns :]  # type: ignore[index]

        # Track action if specified
        action = context.metadata.get("action")
        if action:
            key = (session_id, action)
            self._action_counts[key] += 1  # type: ignore[index]

        # Build metadata
        metadata = {
            "turn_count": len(self._history[session_id]),  # type: ignore[index]
            "history": [
                {"text": t.text, "metadata": t.metadata}
                for t in self._history[session_id]  # type: ignore[index]
            ],
            "session_id": session_id,
        }

        # Check for escalation patterns
        escalation_detected, escalation_pattern = self._check_escalation(session_id)  # type: ignore[arg-type]
        if escalation_detected:
            metadata["escalation_detected"] = True
            metadata["escalation_pattern"] = escalation_pattern

        # Check for repeated attempts
        if action:
            attempt_count = self._action_counts[(session_id, action)]  # type: ignore[index]
            metadata["repeated_attempts"] = attempt_count
            if attempt_count > 2:
                metadata["repetition_detected"] = True

        return GuardrailDecision(passed=True, rule="context_tracked", metadata=metadata)

    def _check_escalation(self, session_id: str) -> tuple[bool, list[str] | None]:
        """Check for topic escalation patterns.

        Args:
            session_id: Session to check.

        Returns:
            Tuple of (detected, pattern).
        """
        if not self.escalation_patterns:
            return False, None

        history = self._history[session_id]
        if len(history) < 2:
            return False, None

        # Get topics from last N turns
        recent_topics = []
        for turn in history[-5:]:  # Check last 5 turns
            topic = turn.metadata.get("topic")
            if topic and topic not in recent_topics:
                recent_topics.append(topic)

        # Check if any escalation pattern matches
        for pattern in self.escalation_patterns:
            if len(recent_topics) >= len(pattern):
                # Check if pattern appears in sequence
                for i in range(len(recent_topics) - len(pattern) + 1):
                    if tuple(recent_topics[i : i + len(pattern)]) == pattern:
                        return True, list(pattern)

        return False, None

    def get_history(self, session_id: str = "default") -> list[dict[str, object]]:
        """Get conversation history for a session.

        Args:
            session_id: Session identifier.

        Returns:
            List of conversation turns.
        """
        return [
            {"text": t.text, "timestamp": t.timestamp, "metadata": t.metadata}
            for t in self._history.get(session_id, [])
        ]

    def clear_history(self, session_id: str | None = None) -> None:
        """Clear conversation history.

        Args:
            session_id: Session to clear, or None for all.
        """
        if session_id:
            self._history.pop(session_id, None)
        else:
            self._history.clear()
