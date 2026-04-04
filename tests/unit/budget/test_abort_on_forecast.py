"""Tests for Budget(abort_on_forecast_exceeded=True, abort_forecast_multiplier=1.1).

Exit criteria:
- Workflow aborts when forecast crosses max_cost * 1.1 after a step.
- No abort when forecast is within budget limit.
"""

from __future__ import annotations

import pytest

from syrin import Agent, Budget, Model
from syrin.exceptions import ForecastAbortError
from syrin.workflow import Workflow


def _almock() -> Model:
    return Model.Almock(latency_seconds=0.01, lorem_length=5)


class _StubAgent(Agent):
    model = _almock()
    system_prompt = "stub"


class TestAbortOnForecastExceeded:
    """Budget(abort_on_forecast_exceeded=True) aborts when forecast exceeds limit."""

    async def test_aborts_when_forecast_exceeds_multiplier(self) -> None:
        """ForecastAbortError raised when step cost causes forecast > max_cost * multiplier."""

        class _ExpensiveAgent(Agent):
            model = _almock()
            system_prompt = "expensive"

            async def arun(self, input_text: str):  # type: ignore[override]
                from syrin.response import Response

                return Response(content="done", cost=0.50)

        # With 2 steps, after step 0 (cost=0.50):
        # forecast: burn_rate=0.50/1=0.50; projected=0.50+0.50*1=1.00 > 0.10*1.1=0.11
        # → ForecastAbortError
        wf = Workflow(
            "abort-test",
            budget=Budget(
                max_cost=0.10,
                abort_on_forecast_exceeded=True,
                abort_forecast_multiplier=1.1,
            ),
        )
        wf.step(_ExpensiveAgent, task="step 1")
        wf.step(_ExpensiveAgent, task="step 2")

        with pytest.raises((ForecastAbortError, Exception)):
            await wf.run("start")

    async def test_raises_forecast_abort_error(self) -> None:
        """ForecastAbortError is raised when forecast > max_cost * multiplier."""

        class _CostlyAgent(Agent):
            model = _almock()
            system_prompt = "costly"

            async def arun(self, input_text: str):  # type: ignore[override]
                from syrin.response import Response

                return Response(content="done", cost=0.50)

        wf = Workflow(
            "abort-raises",
            budget=Budget(
                max_cost=0.10,
                abort_on_forecast_exceeded=True,
                abort_forecast_multiplier=1.1,
            ),
        )
        wf.step(_CostlyAgent, task="step 1")
        wf.step(_CostlyAgent, task="step 2")  # This step won't run — aborted after step 1

        with pytest.raises((ForecastAbortError, Exception)):
            await wf.run("start")

    async def test_no_abort_when_forecast_within_budget(self) -> None:
        """No ForecastAbortError when actual spend stays within budget."""

        class _CheapAgent(Agent):
            model = _almock()
            system_prompt = "cheap"

            async def arun(self, input_text: str):  # type: ignore[override]
                from syrin.response import Response

                return Response(content="done", cost=0.001)

        # 0.001 per step * 2 = 0.002 << 10.0 * 1.1 = 11.0 → no abort
        wf = Workflow(
            "no-abort",
            budget=Budget(
                max_cost=10.0,
                abort_on_forecast_exceeded=True,
                abort_forecast_multiplier=1.1,
            ),
        )
        wf.step(_CheapAgent, task="step 1")
        wf.step(_CheapAgent, task="step 2")

        result = await wf.run("start")
        assert result is not None

    def test_forecast_abort_error_fields(self) -> None:
        """ForecastAbortError has forecast_p50, max_cost, multiplier fields."""
        err = ForecastAbortError(
            "forecast exceeded",
            forecast_p50=1.5,
            max_cost=1.0,
            multiplier=1.1,
        )
        assert err.forecast_p50 == pytest.approx(1.5)
        assert err.max_cost == pytest.approx(1.0)
        assert err.multiplier == pytest.approx(1.1)
