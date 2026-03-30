"""Base Guardrail class."""

from __future__ import annotations

from abc import ABC, abstractmethod

from syrin.enums import GuardrailMode
from syrin.guardrails.context import GuardrailContext
from syrin.guardrails.decision import GuardrailDecision


class Guardrail(ABC):
    """Abstract base class for all guardrails.

    All guardrails must inherit from this class and implement the
    `evaluate` method. Guardrails are evaluated asynchronously to
    enable parallel execution.

    Args:
        name: Optional custom name. Defaults to class name.
        mode: ``GuardrailMode.EVALUATE`` (default) runs ``evaluate()`` as a separate
            check. ``GuardrailMode.SYSTEM_PROMPT`` injects ``system_prompt_instruction()``
            into the agent's system prompt and skips ``evaluate()``.

    Example:
        >>> class MyGuardrail(Guardrail):
        ...     async def evaluate(self, context: GuardrailContext) -> GuardrailDecision:
        ...         if "forbidden" in context.text:
        ...             return GuardrailDecision(
        ...                 passed=False,
        ...                 rule="forbidden_word",
        ...                 reason="Contains forbidden word"
        ...             )
        ...         return GuardrailDecision(passed=True)
    """

    def __init__(
        self,
        name: str | None = None,
        mode: GuardrailMode = GuardrailMode.EVALUATE,
    ) -> None:
        """Initialize guardrail.

        Args:
            name: Optional custom name. Defaults to class name.
            mode: Evaluation mode. ``EVALUATE`` (default) runs ``evaluate()``
                as a separate check. ``SYSTEM_PROMPT`` injects the guardrail's
                instruction into the system prompt instead.
        """
        self.name = name or self.__class__.__name__
        self.mode: GuardrailMode = mode
        self.budget_cost: float = 0.0
        """Cost in USD to run this guardrail. Override in subclasses."""

    @property
    def is_system_prompt_mode(self) -> bool:
        """True when this guardrail runs as a system prompt instruction."""
        return self.mode == GuardrailMode.SYSTEM_PROMPT

    def system_prompt_instruction(self) -> str:
        """Return the instruction to inject into the system prompt.

        Override in subclasses when ``mode=GuardrailMode.SYSTEM_PROMPT``.
        The returned string is appended to the agent's system prompt before
        the LLM call, replacing the normal ``evaluate()`` call.

        Returns:
            Instruction text, or "" to inject nothing.
        """
        return ""

    @abstractmethod
    async def evaluate(self, context: GuardrailContext) -> GuardrailDecision:
        """Evaluate the guardrail against the given context.

        This method must be implemented by all concrete guardrail classes.
        It should return a GuardrailDecision indicating whether the check
        passed or failed.

        Args:
            context: The context to evaluate against.

        Returns:
            GuardrailDecision with the evaluation result.
        """
        pass

    def __repr__(self) -> str:
        """String representation of the guardrail."""
        return f"{self.__class__.__name__}(name='{self.name}')"
