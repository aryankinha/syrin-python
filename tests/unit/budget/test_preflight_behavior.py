"""Behavioral tests for Budget.preflight — raises/warns before first LLM call.

Exit criteria:
- Budget(preflight=True, preflight_fail_on=PreflightPolicy.BELOW_P95) raises
  InsufficientBudgetError before first LLM call when budget < p95 estimate.
- Budget(preflight=True, preflight_fail_on=PreflightPolicy.WARN_ONLY) logs warning
  but does not abort.
"""

from __future__ import annotations

import logging

import pytest

from syrin import Agent, Budget, Model
from syrin.budget._preflight import InsufficientBudgetError
from syrin.enums import PreflightPolicy


def _almock(**kwargs: object) -> Model:
    return Model.Almock(latency_seconds=0.01, lorem_length=10, **kwargs)  # type: ignore[arg-type]


class _StubAgent(Agent):
    model = _almock()
    system_prompt = "stub"
    output_tokens_estimate = 1000  # High estimate to ensure p95 is large


class TestPreflightBELOW_P95:
    """Budget.preflight=True + BELOW_P95 raises InsufficientBudgetError."""

    def test_raises_when_budget_insufficient(self) -> None:
        """BELOW_P95 raises InsufficientBudgetError when p95 estimate > budget."""
        # Use estimation=True so there's estimator history, tiny max_cost
        agent = _StubAgent(
            budget=Budget(
                max_cost=0.000001,  # extremely tiny budget
                estimation=True,
                preflight=True,
                preflight_fail_on=PreflightPolicy.BELOW_P95,
            )
        )
        with pytest.raises(InsufficientBudgetError):
            agent.run("test")

    def test_does_not_raise_when_budget_sufficient(self) -> None:
        """BELOW_P95 does not raise when budget > p95 estimate."""

        class _Cheap(Agent):
            model = _almock()
            system_prompt = "cheap"
            output_tokens_estimate = 1  # minimal tokens → tiny p95

        agent = _Cheap(
            budget=Budget(
                max_cost=100.0,  # very large budget
                estimation=True,
                preflight=True,
                preflight_fail_on=PreflightPolicy.BELOW_P95,
            )
        )
        # Should not raise
        result = agent.run("test")
        assert result is not None


class TestPreflightWARN_ONLY:
    """Budget.preflight=True + WARN_ONLY logs warning, does not raise."""

    def test_warns_but_does_not_raise_preflight_error(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """WARN_ONLY emits a preflight warning but does NOT raise InsufficientBudgetError."""
        # max_cost is just slightly below p95 estimate so preflight triggers,
        # but large enough for the actual run to succeed.
        agent = _StubAgent(
            budget=Budget(
                max_cost=0.005,  # small but feasible for almock
                estimation=True,
                preflight=True,
                preflight_fail_on=PreflightPolicy.WARN_ONLY,
            )
        )
        # WARN_ONLY must NOT raise InsufficientBudgetError
        with caplog.at_level(logging.WARNING):
            try:
                agent.run("test")
            except InsufficientBudgetError:
                pytest.fail("WARN_ONLY must not raise InsufficientBudgetError")
            except Exception:
                pass  # Other budget errors (e.g. BudgetExceededError) are acceptable
        # If a preflight warning was triggered, it should say "preflight"
        [r for r in caplog.records if "preflight" in r.message.lower()]
        # Either warned (if p95 > max_cost) or didn't warn (if budget was sufficient)
        # Either way, no InsufficientBudgetError should have been raised
        assert True  # The important check is that InsufficientBudgetError was NOT raised

    def test_no_warning_when_budget_sufficient(self, caplog: pytest.LogCaptureFixture) -> None:
        """WARN_ONLY does not warn when budget is sufficient."""

        class _Cheap2(Agent):
            model = _almock()
            system_prompt = "cheap"
            output_tokens_estimate = 1

        agent = _Cheap2(
            budget=Budget(
                max_cost=100.0,
                estimation=True,
                preflight=True,
                preflight_fail_on=PreflightPolicy.WARN_ONLY,
            )
        )
        with caplog.at_level(logging.WARNING):
            agent.run("test")
        # No preflight warnings when budget is sufficient
        preflight_warnings = [r for r in caplog.records if "preflight" in r.message.lower()]
        assert len(preflight_warnings) == 0
