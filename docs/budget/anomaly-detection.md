---
title: Anomaly Detection
description: Detect unexpected cost spikes using AnomalyConfig and Hook.BUDGET_ANOMALY, which fire when actual cost exceeds a multiple of historical p95.
weight: 70
---

## Overview

Budget anomaly detection fires `Hook.BUDGET_ANOMALY` when the actual cost of a run is significantly higher than expected — specifically, when it exceeds a configurable multiple of the historical p95 cost.

This catches problems that per-run budgets alone cannot: a run that succeeds (stays under `max_cost`) but costs 5× the normal amount is a signal something went wrong — runaway tool calls, prompt injection, or a model behaving differently than expected.

---

## `AnomalyConfig`

```python
from syrin.budget import AnomalyConfig

config = AnomalyConfig(threshold_multiplier=2.0)
```

`AnomalyConfig` has one field: `threshold_multiplier`, a `float` that defaults to `2.0`. It controls when `BUDGET_ANOMALY` fires — specifically, the hook fires when `actual > threshold_multiplier × p95`.

A multiplier of `2.0` means: fire the hook when the actual cost is more than twice the historical p95. The p95 already represents a near-worst-case — 2× p95 is a strong signal of abnormal behaviour.

---

## Enabling anomaly detection on `Budget`

Pass an `AnomalyConfig` to `Budget.anomaly_detection`:

```python
from syrin import Budget
from syrin.budget import AnomalyConfig

budget = Budget(
    max_cost=5.00,
    estimation=True,
    anomaly_detection=AnomalyConfig(threshold_multiplier=2.0),
)
```

When the run completes, syrin automatically compares the actual cost against the historical p95 and fires `Hook.BUDGET_ANOMALY` if the threshold is exceeded.

---

## `Hook.BUDGET_ANOMALY`

Register a handler to receive anomaly alerts:

```python
from syrin.enums import Hook

agent.events.on(Hook.BUDGET_ANOMALY, lambda ctx: print(
    f"Anomaly detected! "
    f"actual=${ctx['actual']:.4f}  "
    f"p95=${ctx['p95']:.4f}  "
    f"threshold=${ctx['threshold']:.4f}  "
    f"multiplier={ctx['threshold_multiplier']}×"
))
```

### Hook payload fields

| Field | Type | Description |
|-------|------|-------------|
| `actual` | float | Actual cost of the run in USD |
| `p95` | float | Historical p95 cost in USD |
| `threshold` | float | Computed threshold: `p95 × threshold_multiplier` in USD |
| `threshold_multiplier` | float | The configured multiplier value |

---

## Using `BudgetGuardrails.check_anomaly()` directly

For custom orchestration code, call the check manually after a run completes:

```python
from syrin.budget import BudgetGuardrails, AnomalyConfig
from syrin.enums import Hook

config = AnomalyConfig(threshold_multiplier=2.0)

def my_hook_fn(hook: Hook, data: dict) -> None:
    if hook == Hook.BUDGET_ANOMALY:
        print(f"Anomaly: actual ${data['actual']:.4f} > threshold ${data['threshold']:.4f}")

# After the run completes:
BudgetGuardrails.check_anomaly(
    actual=result.cost,
    p95=historical_p95,       # from store.stats("AgentName").p95_cost
    config=config,
    fire_fn=my_hook_fn,
)
```

The check is pure: it fires the hook and returns. It does not raise an exception. If you want to take an action (alert, log, abort future runs), do it inside the hook handler.

---

## `BudgetReport.anomaly_detected`

When running a swarm, `SwarmResult.budget_report` includes an `anomaly_detected` flag:

```python
result = await swarm.run()

if result.budget_report.anomaly_detected:
    print("At least one agent had an anomalous cost this run")
    print(f"Total spent: ${result.budget_report.total_spent:.4f}")
```

---

## Choosing the right threshold multiplier

Three multiplier values cover most scenarios. A multiplier of `1.5` gives high sensitivity — the hook fires often, making it suitable for development environments where catching small deviations early matters. The default `2.0` gives moderate sensitivity and is the right choice for production; it catches genuine spikes without excessive alert fatigue. A multiplier of `3.0` gives low sensitivity and fires rarely, which suits noisy workloads with high natural variance.

Start with `2.0`. If you see too many false positives (spikes that are within normal variance), increase to `3.0`. If anomalies are slipping through at `2.0`, decrease to `1.5`.

---

## Complete example

```python
import asyncio
from syrin import Agent, Budget, Model
from syrin.budget import AnomalyConfig
from syrin.enums import Hook
from syrin.response import Response


class ResearchAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")
    # Use Model.mock() above for testing without an API key
    system_prompt = "Research the given topic."
    output_tokens_estimate = (300, 600)

    async def arun(self, input_text: str) -> Response[str]:
        # Simulate a run that costs far more than expected
        return Response(content=f"Findings on {input_text}", cost=0.80)


async def main() -> None:
    budget = Budget(
        max_cost=5.00,
        estimation=True,
        anomaly_detection=AnomalyConfig(threshold_multiplier=2.0),
    )
    agent = ResearchAgent(budget=budget)

    # Register anomaly handler
    agent.events.on(
        Hook.BUDGET_ANOMALY,
        lambda ctx: print(
            f"ANOMALY: ${ctx['actual']:.4f} actual vs ${ctx['p95']:.4f} p95 "
            f"(threshold ${ctx['threshold']:.4f})"
        ),
    )

    # Seed some history to establish a baseline
    # (In production this accumulates automatically over real runs)
    from syrin.budget._history import _get_default_store
    store = _get_default_store()
    for cost in [0.09, 0.11, 0.10, 0.12, 0.08]:
        store.record("ResearchAgent", cost)

    result = await agent.arun("AI market trends")
    print(f"Run cost: ${result.cost:.4f}")


asyncio.run(main())
```

---

## Notes

- Anomaly detection requires history to be meaningful. On the first run (no recorded history), p95 is `0.0` and the check is skipped.
- Anomaly detection does not abort the current run — it fires the hook after the run completes. Use `abort_on_forecast_exceeded` if you need mid-run abort behaviour.
- The hook fires at most once per run.
