---
title: Budget Control
description: Overview of Syrin's budget system — cost limits, shared pools, spawn budget carve-outs, rate limits, and exceed policies. Links to sub-topic pages.
weight: 40
---

## What Is a Budget?

A `Budget` is Syrin's first-class spending limit. Attach one to any `Agent`, `Swarm`, `Workflow`, or `AgentRouter` and Syrin enforces it automatically — pre-call estimates, post-call actuals, threshold callbacks, and hard stops.

```python
from syrin import Agent, Budget, Model

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="..."),
    budget=Budget(max_cost=1.00),
)
response = agent.run("Summarise this document")
print(f"Cost: ${response.cost:.6f}")
print(f"Remaining: ${agent.budget_state.remaining:.4f}")
```

---

## Core Parameters

```python
Budget(
    max_cost=1.00,   # Hard cap per run (USD)
    reserve=0.10,    # Hold back for final reply
)
```

Two parameters configure a basic budget. `max_cost` (float or None, default None) sets the maximum USD per single run. `reserve` (float, default 0) holds back an amount for the final reply — the effective limit is `max_cost − reserve`.

---

## Shared Budgets in Swarms

Pass a `Budget` to a `Swarm` and sharing is automatic — all agents draw from the same pool. No extra flags needed.

```python
from syrin import Budget, Swarm

budget = Budget(max_cost=10.00)  # Total pool for all agents

swarm = Swarm(agents=[researcher, analyst, writer], goal="...", budget=budget)
result = await swarm.run()
```

All agents share the `max_cost` pool. When the pool is exhausted, `BudgetExceededError` is raised (or the `exceed_policy` fires). Each agent's individual spend is tracked separately in `result.budget_report.per_agent`.

---

## Spawn Budget Carve-outs

When an agent spawns a child with `self.spawn()`, you can carve out a portion of the remaining parent budget for the child. If the requested amount exceeds what remains, Syrin raises `BudgetAllocationError`.

```python
class OrchestratorAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="...")

    async def arun(self, task: str) -> Response[str]:
        # Carve out $0.50 for the child; raises BudgetAllocationError
        # if parent has less than $0.50 remaining.
        child_result = await self.spawn(ResearchAgent, budget=0.50)
        return Response(content=child_result.content, cost=0.0)
```

`BudgetAllocationError` is raised synchronously before the child agent is created, so you can catch it and fall back gracefully:

```python
from syrin.budget.exceptions import BudgetAllocationError

try:
    result = await self.spawn(ResearchAgent, budget=0.50)
except BudgetAllocationError as e:
    # Not enough budget remaining — use a cheaper agent or skip
    result = await self.spawn(CheapResearchAgent, budget=0.10)
```

---

## Rate Limits

Add time-window caps with `RateLimit` to cap hourly, daily, weekly, or monthly spend across all runs of an agent:

```python
from syrin import Budget, RateLimit

budget = Budget(
    max_cost=0.10,
    rate_limits=RateLimit(
        hour=5.00,
        day=50.00,
        month=500.00,
    ),
)
```

See [docs/core/budget.md](core/budget.md) for the full `RateLimit` reference including rolling vs calendar-month windows.

---

## Exceed Policies and Thresholds

Control what happens when a limit is hit, and get early warnings at percentage thresholds:

```python
from syrin import Budget
from syrin.enums import ExceedPolicy
from syrin.threshold import BudgetThreshold

budget = Budget(
    max_cost=1.00,
    exceed_policy=ExceedPolicy.STOP,     # Raise BudgetExceededError
    thresholds=[
        BudgetThreshold(at=75, action=lambda ctx: alert("75% used")),
        BudgetThreshold(at=90, action=lambda ctx: alert("90% used!")),
    ],
)
```

`ExceedPolicy` values: `STOP` (raises), `WARN` (logs), `SWITCH` (switches model), `IGNORE` (silent).

---

## Sub-topic Pages

The budget system covers several advanced areas — each has its own dedicated page:

Eight sub-topic pages cover the advanced areas of the budget system.

[estimation.md](budget/estimation.md) covers `estimate()`, `EstimationReport`, output token hints, and confidence levels. [history.md](budget/history.md) covers `CostStats`, historical tracking, `BudgetStore` backends, and trend detection. [preflight.md](budget/preflight.md) covers `PreflightPolicy`, `InsufficientBudgetError`, and when to use each policy. [forecasting.md](budget/forecasting.md) covers `Hook.BUDGET_FORECAST`, `BudgetForecast`, and `abort_on_forecast_exceeded`.

[guardrails.md](budget/guardrails.md) covers tool call storm prevention, retry caps, and `max_tool_calls_per_step`. [cross-run-limits.md](budget/cross-run-limits.md) covers `daily_limit`, `Hook.DAILY_LIMIT_APPROACHING`, and `BudgetLimitError`. [anomaly-detection.md](budget/anomaly-detection.md) covers `AnomalyConfig`, `Hook.BUDGET_ANOMALY`, and `BudgetReport.anomaly_detected`. [security.md](budget/security.md) covers budget attack surfaces and defenses.

---

## See Also

- [API Reference — Budget](/api-reference#budget) — all `Budget` parameters in one table
- [Swarm Shared Budget](/multi-agent/swarm#shared-budget-pool) — pool mechanics in multi-agent runs
- [Lifecycle Hooks Reference](/debugging/hooks-reference) — `BUDGET_CHECK`, `BUDGET_EXCEEDED`, `BUDGET_THRESHOLD`
