---
title: Real-Time Budget Forecasting
description: Monitor spend mid-run with Hook.BUDGET_FORECAST and abort automatically when projected costs will exceed budget.
weight: 40
---

## Forecasting vs Estimation

Pre-run estimation (see [Cost Estimation](/budget/estimation)) uses historical data to guess what a run will cost before it starts. Forecasting is different — it watches actual spending during the run and projects where you'll end up.

After each step, Syrin updates a linear burn-rate model and fires `Hook.BUDGET_FORECAST` with the projected total cost. If the projection looks bad, you can abort before spending more.

## How the Projection Works

The forecaster uses a simple linear model:

```
projected = actual_spent + (actual_spent / steps_completed) × steps_remaining
```

After step 0 (the first step), the estimate is coarse — it's based on one data point. After step 3 or more, it reflects the true burn rate of your run. The projection improves with every step.

## Subscribing to Forecasts

Enable estimation and subscribe to `Hook.BUDGET_FORECAST`:

```python
from syrin import Agent, Budget, Model
from syrin.enums import Hook

class ResearchAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")
    # Use Model.mock() above for testing without an API key
    system_prompt = "Research the given topic."
    output_tokens_estimate = (300, 900)

agent = ResearchAgent(budget=Budget(max_cost=2.00, estimation=True))

agent.events.on(Hook.BUDGET_FORECAST, lambda ctx: print(
    f"p50=${ctx['forecast_p50']:.4f}  "
    f"p95=${ctx['forecast_p95']:.4f}  "
    f"status={ctx['forecast_status']}"
))
```

The hook context has seven fields:

| Field | Type | Description |
|-------|------|-------------|
| `forecast_p50` | float | Projected total cost at the p50 burn rate (USD) |
| `forecast_p95` | float | Projected total cost at the p95 burn rate (USD) |
| `forecast_status` | str | One of `"on_track"`, `"at_risk"`, or `"likely_exceeded"` |
| `actual_spent` | float | Cumulative actual spend so far (USD) |
| `steps_remaining` | int | Number of steps left in the workflow |
| `total_p50` | float | Reference p50 from the pre-run historical estimate (USD) |
| `total_p95` | float | Reference p95 from the pre-run historical estimate (USD) |

## Forecast Status Values

`"on_track"` means the projected cost is at or below the p50 estimate. The run is looking cheaper than expected.

`"at_risk"` means projected cost exceeds p50 but is still within p95. Normal variance — nothing to panic about, but worth watching.

`"likely_exceeded"` means the projected cost exceeds p95. At the current burn rate, the budget will be exceeded. Time to act.

## Automatic Abort on Bad Forecast

Set `abort_on_forecast_exceeded=True` to abort automatically when the forecast predicts the budget will be exceeded:

```python
from syrin import Budget

budget = Budget(
    max_cost=2.00,
    estimation=True,
    abort_on_forecast_exceeded=True,
)
```

When the projected cost exceeds `max_cost`, Syrin raises `ForecastAbortError` before the next step executes.

### Adding a Tolerance Margin

`abort_forecast_multiplier` adds wiggle room before aborting. The default is `1.0` — abort exactly at the budget limit:

```python
budget = Budget(
    max_cost=2.00,
    estimation=True,
    abort_on_forecast_exceeded=True,
    abort_forecast_multiplier=1.1,  # Allow up to 10% over before aborting
)
```

A multiplier of `1.1` aborts when the projection exceeds `max_cost × 1.1`. A multiplier of `1.5` gives 50% headroom. Use a small tolerance (1.05–1.1) in production to prevent false aborts from noisy early-run projections.

## Handling ForecastAbortError

```python
import asyncio
from syrin import Agent, Budget, Model
from syrin.exceptions import ForecastAbortError

class ResearchAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")
    # Use Model.mock() above for testing without an API key
    system_prompt = "Research the given topic."
    output_tokens_estimate = (300, 900)

async def main():
    budget = Budget(
        max_cost=1.00,
        estimation=True,
        abort_on_forecast_exceeded=True,
        abort_forecast_multiplier=1.1,
    )
    agent = ResearchAgent(budget=budget)

    try:
        result = await agent.arun("AI market trends")
    except ForecastAbortError as e:
        print(f"Run aborted: forecast ${e.forecast_p50:.4f} > budget ${e.max_cost:.2f}")
        print(f"Multiplier applied: {e.multiplier}x")

asyncio.run(main())
```

`ForecastAbortError` has three attributes:

- `forecast_p50` — Projected cost at time of abort (USD)
- `max_cost` — Your configured budget limit (USD)
- `multiplier` — The `abort_forecast_multiplier` that was applied

## Using BudgetForecaster Directly

For custom orchestration code, use `BudgetForecaster` directly:

```python
from syrin.budget._forecast import BudgetForecaster

forecaster = BudgetForecaster(total_p50=1.00, total_p95=2.00)

# After the first step completes
forecaster.update(step_index=0, actual_spent=0.30)
result = forecaster.forecast(steps_remaining=3)

print(result.status)       # BudgetForecastStatus.AT_RISK
print(result.forecast_p50) # Projected cost at p50 burn rate

# Optionally fire the hook manually
forecaster.fire_hook(
    hook_fn=lambda hook, data: print(data),
    spent=0.30,
    steps_remaining=3,
)
```

## Recommended Production Configuration

```python
from syrin import Agent, Budget
from syrin.enums import Hook

budget = Budget(
    max_cost=5.00,
    estimation=True,                   # Enable history recording + pre-run checks
    abort_on_forecast_exceeded=True,   # Abort if trajectory looks bad
    abort_forecast_multiplier=1.05,    # 5% tolerance before aborting
)

agent = ResearchAgent(budget=budget)

agent.events.on(Hook.BUDGET_FORECAST, lambda ctx: (
    print(f"Forecast: {ctx['forecast_status']} — p95=${ctx['forecast_p95']:.4f} / ${budget.max_cost:.2f}")
    if ctx["forecast_status"] != "on_track" else None
))
```

## What's Next?

- [Cost Estimation](/budget/estimation) — Pre-run cost estimation
- [Budget Callbacks](/core/budget-callbacks) — Threshold actions and alerts
- [Budget Overview](/core/budget) — Budget basics and configuration
