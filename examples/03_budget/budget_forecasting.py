"""Budget forecasting — Hook.BUDGET_FORECAST handler, mid-run abort.

After each workflow step, syrin computes a forward-looking cost projection
based on the actual burn rate so far. This lets you detect overruns before
they happen and abort mid-run.

Key concepts:
  - Hook.BUDGET_FORECAST — fires after each step with forecast data
  - EventContext: forecast_p50, forecast_p95, forecast_status, actual_spent
  - Budget(abort_on_forecast_exceeded=True, abort_forecast_multiplier=1.1)
  - ForecastAbortError — raised when forecast exceeds the threshold
  - BudgetForecastStatus.ON_TRACK, AT_RISK, LIKELY_EXCEEDED

Run:
    uv run python examples/budget_forecasting.py
"""

from __future__ import annotations

import asyncio

from syrin import Agent, Budget, Model
from syrin.enums import BudgetForecastStatus, Hook
from syrin.response import Response
from syrin.workflow import Workflow

# ── Agent definitions ─────────────────────────────────────────────────────────


class Step1Agent(Agent):
    """First pipeline step — modest cost."""

    model = Model.mock(latency_seconds=0.05, lorem_length=8)
    system_prompt = "First step in the pipeline."
    output_tokens_estimate = 200

    async def arun(self, input_text: str) -> Response[str]:
        return Response(content=f"Step 1 done: {input_text[:40]}", cost=0.005)


class Step2Agent(Agent):
    """Second pipeline step — heavier cost (triggers forecast warning)."""

    model = Model.mock(latency_seconds=0.05, lorem_length=8)
    system_prompt = "Second step — more thorough analysis."
    output_tokens_estimate = 500

    async def arun(self, input_text: str) -> Response[str]:
        return Response(content="Step 2 done: detailed analysis complete.", cost=0.012)


class Step3Agent(Agent):
    """Third pipeline step — summary."""

    model = Model.mock(latency_seconds=0.05, lorem_length=8)
    system_prompt = "Final step — produce output."
    output_tokens_estimate = 150

    async def arun(self, input_text: str) -> Response[str]:
        return Response(content="Step 3 done: final output ready.", cost=0.004)


class ExpensiveStep4Agent(Agent):
    """An expensive fourth step used to demonstrate abort."""

    model = Model.mock(latency_seconds=0.05, lorem_length=8)
    system_prompt = "Expensive deep analysis."
    output_tokens_estimate = (800, 2000)

    async def arun(self, input_text: str) -> Response[str]:
        return Response(content="Expensive analysis complete.", cost=0.08)


# ── Example 1: Observe forecast events ───────────────────────────────────────
#
# Register a handler for Hook.BUDGET_FORECAST on the workflow.
# The hook fires after each step with projection data.


async def example_forecast_observer() -> None:
    print("\n── Example 1: Observe Hook.BUDGET_FORECAST ──────────────────────")

    forecast_log: list[dict[str, object]] = []

    def on_forecast(ctx: object) -> None:
        entry = {
            "forecast_p50": ctx.get("forecast_p50"),  # type: ignore[union-attr]
            "forecast_p95": ctx.get("forecast_p95"),  # type: ignore[union-attr]
            "forecast_status": ctx.get("forecast_status"),  # type: ignore[union-attr]
            "actual_spent": ctx.get("actual_spent"),  # type: ignore[union-attr]
            "steps_remaining": ctx.get("steps_remaining"),  # type: ignore[union-attr]
        }
        forecast_log.append(entry)
        status = entry["forecast_status"] or "unknown"
        print(
            f"  [FORECAST] step_done  "
            f"actual=${entry['actual_spent'] or 0:.4f}  "
            f"p50=${entry['forecast_p50'] or 0:.4f}  "
            f"p95=${entry['forecast_p95'] or 0:.4f}  "
            f"status={status}"
        )

    wf = (
        Workflow(
            "forecast-demo",
            budget=Budget(max_cost=0.10),
        )
        .step(Step1Agent)
        .step(Step2Agent)
        .step(Step3Agent)
    )

    wf.events.on(Hook.BUDGET_FORECAST, on_forecast)

    result = await wf.run("Analyse AI adoption trends")
    print(f"\n  Run completed. Total cost: ${result.cost:.4f}")
    print(f"  Forecast events received: {len(forecast_log)}")


# ── Example 2: Abort when forecast exceeds budget ────────────────────────────
#
# Budget(abort_on_forecast_exceeded=True, abort_forecast_multiplier=1.1) means:
# abort when the projected cost > max_cost * 1.1 (10% over budget).


async def example_forecast_abort() -> None:
    print("\n── Example 2: Abort on forecast exceeded ────────────────────────")

    from syrin.exceptions import ForecastAbortError

    wf = (
        Workflow(
            "forecast-abort-demo",
            budget=Budget(
                max_cost=0.005,  # very tight — ExpensiveStep4Agent will trigger abort
                abort_on_forecast_exceeded=True,
                abort_forecast_multiplier=1.1,
            ),
        )
        .step(Step1Agent)
        .step(ExpensiveStep4Agent)  # this step's forecast will exceed 0.005 * 1.1
        .step(Step3Agent)
    )

    forecast_events: list[str] = []
    wf.events.on(
        Hook.BUDGET_FORECAST,
        lambda ctx: forecast_events.append(str(ctx.get("forecast_status"))),
    )

    try:
        result = await wf.run("Long research task")
        print(f"  Completed (no abort). Cost: ${result.cost:.4f}")
    except ForecastAbortError as e:
        print("  ForecastAbortError raised!")
        print(f"  forecast_p50: ${e.forecast_p50:.4f}")
        print(f"  max_cost:     ${e.max_cost:.4f}")
        print(f"  multiplier:   {e.multiplier}x")
    except Exception as e:
        # Budget may also raise BudgetExceededError depending on run timing
        print(f"  {type(e).__name__}: {e}")

    print(f"  Forecast statuses seen: {forecast_events}")


# ── Example 3: Forecast status values ────────────────────────────────────────


async def example_forecast_statuses() -> None:
    print("\n── Example 3: BudgetForecastStatus values ───────────────────────")

    statuses = [
        (BudgetForecastStatus.ON_TRACK, "Projected cost < p50 — on track"),
        (BudgetForecastStatus.AT_RISK, "Projected cost > p50 but < p95 — watch closely"),
        (BudgetForecastStatus.LIKELY_EXCEEDED, "Projected cost > p95 — overspend likely"),
    ]

    print("  BudgetForecastStatus values:")
    for status, description in statuses:
        print(f"    {status!s:<25}  {description}")

    print("\n  Typical handler pattern:")
    print("    wf.events.on(Hook.BUDGET_FORECAST, lambda ctx: (")
    print(
        "        alert_team(ctx) if ctx['forecast_status'] == BudgetForecastStatus.LIKELY_EXCEEDED"
    )
    print("        else None")
    print("    ))")


# ── Main ──────────────────────────────────────────────────────────────────────


async def main() -> None:
    await example_forecast_observer()
    await example_forecast_abort()
    await example_forecast_statuses()
    print("\nAll budget forecasting examples completed.")


if __name__ == "__main__":
    asyncio.run(main())
