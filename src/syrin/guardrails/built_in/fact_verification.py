"""Fact verification guardrail — verifies output claims against grounded facts."""

from __future__ import annotations

import re

from syrin.enums import DecisionAction
from syrin.guardrails.base import Guardrail
from syrin.guardrails.context import GuardrailContext
from syrin.guardrails.decision import GuardrailDecision


class FactVerificationGuardrail(Guardrail):
    """Guardrail that verifies factual claims in output against grounded facts.

    When grounded_facts are available (e.g. from knowledge search with grounding),
    checks that key claims in the output are supported. Use with grounding=True
    on Knowledge for anti-hallucination.

    If no grounded_facts in context.metadata, passes (no-op). Use with agents
    that have grounding-enabled knowledge.

    Example:
        >>> guardrail = FactVerificationGuardrail(
        ...     action=DecisionAction.FLAG,
        ...     min_confidence=0.7,
        ... )
        >>> # Agent populates context.metadata["grounded_facts"] when grounding is used
        >>> result = await guardrail.evaluate(context)
    """

    def __init__(
        self,
        action: DecisionAction = DecisionAction.FLAG,
        min_confidence: float = 0.7,
        name: str | None = None,
    ) -> None:
        """Initialize fact verification guardrail.

        Args:
            action: FLAG to annotate unverified claims without blocking, BLOCK to reject.
            min_confidence: Minimum confidence for a grounded fact to count as support.
            name: Optional custom name.
        """
        super().__init__(name)
        self.action = action
        self.min_confidence = max(0.0, min(1.0, min_confidence))

    async def evaluate(self, context: GuardrailContext) -> GuardrailDecision:
        """Verify factual claims in output against grounded facts.

        Reads grounded_facts from context.metadata["grounded_facts"].
        If absent or empty, passes (no grounding in use).

        Args:
            context: Guardrail context with text (output) and optional metadata.

        Returns:
            GuardrailDecision indicating if claims are verified.
        """
        text = context.text
        facts = context.metadata.get("grounded_facts")
        if not facts:
            return GuardrailDecision(
                passed=True,
                rule="fact_verification",
                reason="No grounded facts in context; skipping verification.",
                metadata={"skipped": True},
            )

        verified_contents = {
            f.content.lower()
            for f in facts  # type: ignore[attr-defined]
            if hasattr(f, "content")
            and hasattr(f, "confidence")
            and getattr(f, "confidence", 0) >= self.min_confidence
            and getattr(f, "verification", None) is not None
            and str(getattr(f, "verification", "")).endswith("VERIFIED")
        }
        if not verified_contents:
            return GuardrailDecision(
                passed=True,
                rule="fact_verification",
                reason="No verified facts above threshold; skipping.",
                metadata={"verified_count": 0},
            )

        sentences = re.split(r"[.!?]\s+", text)
        unverified: list[str] = []
        for s in sentences:
            s = s.strip()
            if len(s) < 20:
                continue
            if not re.search(r"\d|%\$|₹|€|£", s):
                continue
            s_lower = s.lower()
            if any(fc in s_lower or s_lower in fc for fc in verified_contents):
                continue
            unverified.append(s[:80] + ("..." if len(s) > 80 else ""))

        if unverified:
            return GuardrailDecision(
                passed=False,
                rule="unverified_claim",
                reason=f"Output contains claims not found in grounded facts: {unverified[0][:60]}...",
                confidence=0.8,
                action=self.action,
                metadata={"unverified_count": len(unverified), "samples": unverified[:3]},
                alternatives=["Add citations to source documents", "Use only verified facts"],
            )
        return GuardrailDecision(
            passed=True,
            rule="fact_verification",
            metadata={"verified_fact_count": len(verified_contents)},
        )
