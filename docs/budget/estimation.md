---
title: Cost Estimation
description: Estimate agent run costs before any LLM calls are made using output_tokens_estimate, historical stats, or a custom estimator.
weight: 10
---

## Estimate Before You Spend

Syrin can estimate what a run will cost before making a single LLM call. Enable it with one field on `Budget`, then access `.estimated_cost` before calling `.run()`:

```python
from syrin import Agent, Budget, Model

class ResearchAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")
    # Use Model.mock() above for testing without an API key
    output_tokens_estimate = (300, 900)  # (typical, worst-case tokens)

agent = ResearchAgent(budget=Budget(max_cost=2.00, estimation=True))

est = agent.estimated_cost
print(f"p50=${est.p50:.4f}  p95=${est.p95:.4f}  ok={est.sufficient}")
```

Estimation is lazy — it runs when you access `.estimated_cost`, not at construction time, not before `agent.run()`. Every access recomputes from scratch.

## How the Estimate Is Computed

For each agent class, Syrin picks its cost source in priority order.

First: `output_tokens_estimate` on the agent class. Multiply by the model's per-token price. This gives a high-confidence estimate.

Second: Historical p50/p95 from the auto-store at `~/.syrin/budget_stats.json`. When `estimation=True`, Syrin auto-records every run cost. After one real run, future estimates use this data.

Third: Historical p50/p95 from a custom `FileBudgetStore` if you've configured one.

Finally: The built-in fallback — 500 tokens at $3/M. This gives `low_confidence=True`. It's a rough signal, not a precise projection.

No LLM calls are made at any stage.

## Declaring output_tokens_estimate

This class attribute is the fastest way to eliminate low-confidence estimates:

```python
from syrin import Agent, Model

class SummaryAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")
    # Use Model.mock() above for testing without an API key
    # Single int — use when output length is consistent
    output_tokens_estimate = 150

class ResearchAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")
    # Use Model.mock() above for testing without an API key
    # Tuple — use when output varies by input complexity
    output_tokens_estimate = (300, 900)  # (p50_tokens, p95_tokens)
```

To pick good values: run your agent on a few representative inputs, note the token counts, set p50 to what you see on normal inputs, and set p95 to what you see on long or complex ones. Be generous with p95. A higher p95 leads to a safer budget recommendation.

## CostEstimate Fields

`.estimated_cost` returns a `CostEstimate` with four fields, or `None` if `estimation=False`.

| Field | Type | Description |
|-------|------|-------------|
| `p50` | float | Median expected cost in USD. Half of runs typically cost less than this. |
| `p95` | float | 95th-percentile expected cost. Size your `max_cost` to this value — a budget at p50 gets exceeded ~half the time. |
| `sufficient` | bool | `True` when `budget.max_cost >= p95`. Your budget covers the worst-case estimate. |
| `low_confidence` | bool | `True` when the fallback was used. Add `output_tokens_estimate` or record real runs to eliminate it. |

## Estimation Policies

Control what happens when `sufficient=False`:

```python
from syrin import Budget
from syrin.enums import EstimationPolicy

# WARN_ONLY (default): logs a warning, returns the estimate, never raises
budget = Budget(max_cost=0.50, estimation=True, estimation_policy=EstimationPolicy.WARN_ONLY)

# RAISE: raises InsufficientBudgetError inside .estimated_cost — agent.run() is never reached
budget = Budget(max_cost=0.50, estimation=True, estimation_policy=EstimationPolicy.RAISE)

# DISABLED: skip all estimation checks
budget = Budget(max_cost=0.50, estimation=True, estimation_policy=EstimationPolicy.DISABLED)
```

Catching the error:

```python
from syrin.budget import InsufficientBudgetError

budget = Budget(max_cost=0.001, estimation=True, estimation_policy=EstimationPolicy.RAISE)
agent = ResearchAgent(budget=budget)

try:
    est = agent.estimated_cost  # Raises here if p95 > max_cost
    result = await agent.run("Summarise AI trends")
except InsufficientBudgetError as e:
    print(f"p95 ${e.total_p95:.4f} exceeds budget ${e.budget_configured:.4f}")
    # e.total_p50 — median estimate
    # e.policy — the EstimationPolicy value
```

## Automatic Cost History

When `estimation=True`, Syrin auto-records every run cost to `~/.syrin/budget_stats.json` after successful runs. After the first real run, estimates switch from the fallback to real historical data:

```python
agent = ResearchAgent(budget=Budget(max_cost=5.00, estimation=True))

est = agent.estimated_cost
print(f"low_confidence: {est.low_confidence}")  # True — no history yet

await agent.arun("Summarise AI trends")  # Cost auto-recorded

est = agent.estimated_cost
print(f"low_confidence: {est.low_confidence}")  # False — real data
print(f"p50: ${est.p50:.4f}   p95: ${est.p95:.4f}")
```

The auto-store keeps the 100 most recent samples per agent. Old samples are evicted as new ones arrive.

## Workflow Estimation

`wf.estimate()` aggregates across all workflow steps:

```python
from syrin.workflow import Workflow

report = wf.estimate("Summarise AI trends")
print(f"p50=${report.total_p50:.4f}  p95=${report.total_p95:.4f}")
print(f"Budget OK: {report.budget_sufficient}")

for i, step in enumerate(report.per_step):
    print(f"  Step {i}: p95=${step.p95:.4f}  low_conf={step.low_confidence}")
```

`EstimationReport` fields:

| Field | Description |
|-------|-------------|
| `total_p50` | Sum of p50 across all steps |
| `total_p95` | Sum of p95 across all steps |
| `budget_sufficient` | `True` if `total_p95 <= budget.max_cost` |
| `per_step` | List of `CostEstimate` in step order |
| `low_confidence` | `True` if any step used the fallback estimator |

## Swarm Estimation

`.estimated_cost` on a swarm sums across all agents:

```python
from syrin import Budget, Model
from syrin.swarm import Swarm

swarm = Swarm(
    agents=[ResearchAgent(), WriterAgent()],
    goal="Analyse AI trends",
    budget=Budget(max_cost=2.00, estimation=True),
)

est = swarm.estimated_cost
print(f"Combined p50: ${est.p50:.4f}")
print(f"Combined p95: ${est.p95:.4f}")
print(f"Sufficient: {est.sufficient}")
```

## Custom Estimator

Override `estimate_agent()` for internal pricing sheets or team-specific benchmarks:

```python
from syrin.budget import CostEstimator, CostEstimate

class TieredEstimator(CostEstimator):
    _TIERS = {
        "ResearchAgent": (0.05, 0.12),
        "WriterAgent":   (0.02, 0.04),
    }

    def estimate_agent(self, agent_class: type) -> CostEstimate:
        p50, p95 = self._TIERS.get(agent_class.__name__, (0.01, 0.03))
        return CostEstimate(p50=p50, p95=p95, sufficient=True, low_confidence=False)

budget = Budget(max_cost=5.00, estimation=True, estimator=TieredEstimator())
agent = ResearchAgent(budget=budget)
est = agent.estimated_cost
```

`estimate_agent()` receives the agent class, not an instance. Return `sufficient=True` — the aggregation layer sets the final `sufficient` value based on the actual budget.

## What's Next?

- [Forecasting](/budget/forecasting) — Real-time mid-run budget projection
- [Budget Callbacks](/core/budget-callbacks) — Threshold actions and alerts
- [Budget Overview](/core/budget) — Budget basics
