"""Length guardrail - enforces min/max text length."""

from __future__ import annotations

from syrin.guardrails.base import Guardrail
from syrin.guardrails.context import GuardrailContext
from syrin.guardrails.decision import GuardrailDecision


class LengthGuardrail(Guardrail):
    """Guardrail that enforces min/max text length.

    Fails if text is too short or too long. Use for input/output size limits.

    Args:
        min_length: Minimum allowed length (default 0).
        max_length: Maximum allowed length (default 10000).
        name: Optional custom name.

    Example:
        >>> guardrail = LengthGuardrail(min_length=5, max_length=100)
        >>> result = await guardrail.evaluate(context)
    """

    def __init__(
        self,
        min_length: int = 0,
        max_length: int = 10000,
        name: str | None = None,
    ) -> None:
        super().__init__(name)
        self._min_length = min_length
        self._max_length = max_length

    async def evaluate(self, context: GuardrailContext) -> GuardrailDecision:
        length = len(context.text)

        if length < self._min_length:
            return GuardrailDecision(
                passed=False,
                rule="too_short",
                reason=f"Text too short: {length} < {self._min_length}",
                metadata={"length": length, "min": self._min_length},
            )

        if length > self._max_length:
            return GuardrailDecision(
                passed=False,
                rule="too_long",
                reason=f"Text too long: {length} > {self._max_length}",
                metadata={"length": length, "max": self._max_length},
            )

        return GuardrailDecision(
            passed=True,
            rule="length_ok",
            metadata={"guardrail": self.name, "length": length},
        )
