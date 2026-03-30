"""6.4: PromptInjectionGuardrail — pattern matching, canary tokens, per-session rate limiting.

Defense-in-depth against prompt injection. Combines:
- Pattern-based detection (common injection phrases)
- Canary token detection (agent embeds tokens; if echoed back, injection suspected)
- Per-session rate limiting (block sessions that repeatedly trigger)

Honest about limitations: pattern matching can be evaded. This is one layer of defense,
not a complete solution. Use with input normalization (6.1) and spotlighting (6.2).
"""

from __future__ import annotations

import re
import secrets
import threading
import time
from collections import defaultdict

from syrin.guardrails.base import Guardrail
from syrin.guardrails.context import GuardrailContext
from syrin.guardrails.decision import GuardrailDecision

# Common injection patterns
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(?:previous|all|above|prior)\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(?:previous|all|above|prior|your)\s+instructions?", re.IGNORECASE),
    re.compile(r"forget\s+(?:all|everything|previous|prior|your)\s+instructions?", re.IGNORECASE),
    re.compile(r"new\s+(?:system\s+)?instruction", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:a|an|the)\b", re.IGNORECASE),
    re.compile(r"override\s+(?:your|previous|all)\s+instructions?", re.IGNORECASE),
    re.compile(r"system\s*(?:prompt|instruction)\s*:", re.IGNORECASE),
    re.compile(r"\[(?:SYSTEM|INST|SYS)\]", re.IGNORECASE),
    re.compile(r"<\|(?:system|im_start|endoftext)\|>", re.IGNORECASE),
    re.compile(r"###\s*(?:system|instruction)", re.IGNORECASE),
    re.compile(r"act\s+as\s+(?:a|an|if|though)\b", re.IGNORECASE),
    re.compile(r"pretend\s+(?:you\s+are|to\s+be)\b", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"DAN\s+mode", re.IGNORECASE),
]


class PromptInjectionGuardrail(Guardrail):
    """Guardrail that detects and blocks prompt injection attempts.

    Combines pattern matching, canary token detection, and per-session
    rate limiting. Integrates with the Hook system to emit
    INJECTION_DETECTED, CANARY_TRIGGERED, and INJECTION_RATE_LIMITED events.

    Args:
        canary_count: Number of canary tokens to embed per session. Default: 3.
        max_flagged_attempts: Block session after N injections detected. Default: 5.
        block_duration: Seconds to block a rate-limited session. Default: 300 (5 min).
        custom_patterns: Additional regex patterns to check. Default: None.

    Example:
        >>> guardrail = PromptInjectionGuardrail(canary_count=3, max_flagged_attempts=3)
        >>> agent = MyAgent(guardrails=[guardrail])
    """

    def __init__(
        self,
        canary_count: int = 3,
        max_flagged_attempts: int = 5,
        block_duration: int = 300,
        custom_patterns: list[str] | None = None,
        name: str | None = None,
    ) -> None:
        """Initialize PromptInjectionGuardrail.

        Args:
            canary_count: How many canary tokens to generate. Default: 3.
            max_flagged_attempts: Flag count before rate-limiting a session. Default: 5.
            block_duration: Seconds a rate-limited session is blocked. Default: 300.
            custom_patterns: Additional regex patterns (plain strings). Default: None.
            name: Guardrail name. Default: "PromptInjectionGuardrail".
        """
        super().__init__(name or "PromptInjectionGuardrail")
        self._canary_count = canary_count
        self._max_flagged_attempts = max_flagged_attempts
        self._block_duration = block_duration

        # Compile custom patterns
        self._patterns = list(_INJECTION_PATTERNS)
        if custom_patterns:
            for p in custom_patterns:
                self._patterns.append(re.compile(p, re.IGNORECASE))

        # Per-session state
        self._lock = threading.Lock()
        self._canaries: set[str] = set()
        self._session_flags: dict[str, int] = defaultdict(int)
        self._session_blocked_until: dict[str, float] = {}

        # Generate initial canary tokens
        for _ in range(canary_count):
            self._canaries.add(self._new_canary())

    def _new_canary(self) -> str:
        """Generate a new unique canary token."""
        return f"SYRIN-CANARY-{secrets.token_hex(8).upper()}"

    def get_canary_tokens(self) -> list[str]:
        """Return current canary tokens for embedding in system prompt.

        Embed these in the system prompt (e.g. in a comment or hidden instruction).
        If an attacker causes the model to echo them back, CANARY_TRIGGERED fires.

        Returns:
            List of canary token strings.
        """
        return list(self._canaries)

    def _session_id(self, context: GuardrailContext) -> str:
        """Extract or generate session ID from context."""
        if isinstance(context.metadata, dict) and "session_id" in context.metadata:
            sid = context.metadata["session_id"]
            return str(sid) if sid is not None else "default"
        if context.agent is not None and hasattr(context.agent, "_conversation_id"):
            conv_id = getattr(context.agent, "_conversation_id", None)
            return str(conv_id) if conv_id else "default"
        return "default"

    async def evaluate(self, context: GuardrailContext) -> GuardrailDecision:
        """Evaluate text for prompt injection attempts.

        Checks:
        1. Rate limit: session already blocked?
        2. Pattern matching: injection phrases detected?
        3. Canary: any canary tokens echoed back?

        Args:
            context: Guardrail context with text to evaluate.

        Returns:
            GuardrailDecision — passed=True if clean, passed=False if injection detected.
        """
        from syrin.enums import Hook

        session = self._session_id(context)
        text = context.text

        # Check rate limit
        with self._lock:
            blocked_until = self._session_blocked_until.get(session, 0.0)
            if time.time() < blocked_until:
                self._emit_hook(context, Hook.INJECTION_RATE_LIMITED, session)
                return GuardrailDecision(
                    passed=False,
                    rule="rate_limited",
                    reason=f"Session rate-limited until {blocked_until:.0f} (too many injection attempts)",
                    metadata={"session_id": session},
                )

        # Pattern matching
        matched_pattern: str | None = None
        for pattern in self._patterns:
            if pattern.search(text):
                matched_pattern = pattern.pattern
                break

        if matched_pattern:
            with self._lock:
                self._session_flags[session] += 1
                flag_count = self._session_flags[session]
                if flag_count >= self._max_flagged_attempts:
                    self._session_blocked_until[session] = time.time() + self._block_duration
                    self._session_flags[session] = 0

            self._emit_hook(context, Hook.INJECTION_DETECTED, session, pattern=matched_pattern)
            return GuardrailDecision(
                passed=False,
                rule="injection_pattern",
                reason=f"Prompt injection pattern detected: {matched_pattern!r}",
                metadata={"session_id": session, "pattern": matched_pattern},
            )

        # Canary token check
        with self._lock:
            canaries_copy = set(self._canaries)
        for canary in canaries_copy:
            if canary in text:
                self._emit_hook(context, Hook.CANARY_TRIGGERED, session, canary=canary)
                return GuardrailDecision(
                    passed=False,
                    rule="canary_triggered",
                    reason=f"Canary token echoed — possible injection: {canary}",
                    metadata={"session_id": session, "canary": canary},
                )

        return GuardrailDecision(passed=True, rule="injection_check")

    def _emit_hook(
        self,
        context: GuardrailContext,
        hook: object,
        session: str,
        **extra: object,
    ) -> None:
        """Emit a hook if the agent has an events system."""
        if context.agent is None or not hasattr(context.agent, "_emit_event"):
            return
        try:
            from syrin.events import EventContext

            ctx = EventContext(session_id=session, guardrail=self.name, **extra)
            context.agent._emit_event(hook, ctx)
        except Exception:
            pass


__all__ = ["PromptInjectionGuardrail"]
