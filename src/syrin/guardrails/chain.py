"""Guardrail chain for sequential evaluation."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Iterator
from typing import Any

from syrin.guardrails.base import Guardrail
from syrin.guardrails.context import GuardrailContext
from syrin.guardrails.decision import GuardrailDecision
from syrin.guardrails.engine import EvaluationResult
from syrin.guardrails.legacy import LegacyGuardrailResult


class GuardrailChain:
    """Chain of guardrails evaluated sequentially.

    Unlike parallel evaluation, the chain stops as soon as one
    guardrail fails. This is useful when order matters or when
    early failures should prevent expensive later checks.

    Example:
        >>> chain = GuardrailChain([
        ...     FastCheck(),  # Run first, cheap
        ...     ExpensiveCheck(),  # Only if first passes
        ... ])
        >>> result = await chain.evaluate(context)
    """

    def __init__(self, guardrails: list[Guardrail] | None = None):
        """Initialize guardrail chain.

        Args:
            guardrails: List of guardrails to evaluate in order.
        """
        self._guardrails = guardrails or []

    def add(self, guardrail: Guardrail) -> None:
        """Add a guardrail to the chain.

        Args:
            guardrail: Guardrail to add.
        """
        self._guardrails.append(guardrail)

    async def evaluate(self, context: GuardrailContext) -> EvaluationResult:
        """Evaluate guardrails in sequence.

        Stops at first failure.

        Args:
            context: Context to evaluate against.

        Returns:
            EvaluationResult with results.
        """
        start_time = time.time()
        decisions = []
        total_budget = 0.0

        for guardrail in self._guardrails:
            try:
                decision = await guardrail.evaluate(context)
                decision.latency_ms = 0.0  # Will be set properly
                decisions.append(decision)
                total_budget += decision.budget_consumed

                # Stop on first failure
                if not decision.passed:
                    elapsed = (time.time() - start_time) * 1000
                    return EvaluationResult(
                        passed=False,
                        decisions=decisions,
                        rule=decision.rule,
                        reason=decision.reason,
                        total_latency_ms=elapsed,
                        total_budget_consumed=total_budget,
                    )

            except Exception as e:
                # Exception stops the chain
                error_decision = GuardrailDecision(
                    passed=False,
                    rule="exception",
                    reason=f"Guardrail '{guardrail.name}' raised exception: {str(e)}",
                    metadata={"exception": str(e), "guardrail": guardrail.name},
                )
                decisions.append(error_decision)
                elapsed = (time.time() - start_time) * 1000

                return EvaluationResult(
                    passed=False,
                    decisions=decisions,
                    rule="exception",
                    reason=str(e),
                    total_latency_ms=elapsed,
                    total_budget_consumed=total_budget,
                )

        # All passed
        elapsed = (time.time() - start_time) * 1000
        return EvaluationResult(
            passed=True,
            decisions=decisions,
            total_latency_ms=elapsed,
            total_budget_consumed=total_budget,
        )

    def check(self, text: str, stage: Any = None) -> LegacyGuardrailResult:
        """Legacy check method for backward compatibility.

        Args:
            text: Text to check.
            stage: Guardrail stage (for compatibility).

        Returns:
            LegacyGuardrailResult with passed status.
        """
        from syrin.guardrails.context import GuardrailContext
        from syrin.guardrails.enums import GuardrailStage
        from syrin.guardrails.legacy import LegacyGuardrailResult

        # Create context with proper stage
        if stage is None:
            stage = GuardrailStage.INPUT
        context = GuardrailContext(text=text, stage=stage)

        # Run async evaluate in sync context
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:
            # We're inside a running loop - run in a separate thread
            import concurrent.futures

            def run_in_thread() -> Any:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(self.evaluate(context))
                finally:
                    new_loop.close()

            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(run_in_thread).result()
        else:
            # No running loop - use asyncio.run for clean lifecycle
            result = asyncio.run(self.evaluate(context))

        # Convert EvaluationResult to LegacyGuardrailResult
        first_failure = next((d for d in result.decisions if not d.passed), None)
        if first_failure:
            return LegacyGuardrailResult(
                passed=False,
                reason=first_failure.reason,
                metadata=first_failure.metadata,
            )
        return LegacyGuardrailResult(passed=True)

    def __len__(self) -> int:
        """Return number of guardrails in chain."""
        return len(self._guardrails)

    def __iter__(self) -> Iterator[Guardrail]:
        """Iterate over guardrails."""
        return iter(self._guardrails)
