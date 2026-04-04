---
title: Budget Estimation
description: Estimate run costs before any LLM call is made. Catch budget problems at definition time.
weight: 42
---

## Know Before You Spend

Normally you find out your budget is too small when the agent hits it mid-run. At that point, you've spent money and gotten a partial result.

Budget estimation flips this around. You ask "will my budget cover this?" before the run starts. Syrin answers with a p50 (typical cost) and p95 (worst-case cost) estimate. No LLM calls, no spending, no surprises.

## How Estimation Works

Enable estimation on your budget:

```python
from syrin import Budget

budget = Budget(max_cost=5.00, estimation=True)
```

Then access `agent.estimated_cost` — that's when estimation actually runs:

```python
from syrin import Agent, Budget, Model

class ResearchAgent(Agent):
    model = Model.mock()
    output_tokens_estimate = (300, 900)  # (typical, worst-case tokens)

agent = ResearchAgent(budget=Budget(max_cost=5.00, estimation=True))

est = agent.estimated_cost
print(f"p50: ${est.p50:.4f}")         # Typical cost
print(f"p95: ${est.p95:.4f}")         # Worst-case cost
print(f"Sufficient: {est.sufficient}") # Is the budget enough?
```

Estimation is **lazy and explicit** — it runs when you access the property, not at construction time, not before `agent.run()`. Every access recomputes the estimate.

## Understanding p50 and p95

**p50 is your typical cost.** If you ran the agent 100 times, roughly half of those runs would cost less than p50 and half would cost more. It tells you what a normal run looks like.

**p95 is your budget number.** 95 out of 100 runs stay under p95. Only 1 in 20 would exceed it. When you set `Budget.max_cost`, set it to your p95 estimate — not p50. A budget at p50 gets exceeded half the time.

**The rule of thumb: size your budget to p95, not p50.**

## Declaring Token Estimates

Add `output_tokens_estimate` to your agent class. Syrin multiplies this by the model's price to derive the cost estimate:

```python
from syrin import Agent, Model

class SummaryAgent(Agent):
    model = Model.mock()
    # Single int — use when output length is predictable
    output_tokens_estimate = 150

class ResearchAgent(Agent):
    model = Model.mock()
    # Tuple — use when output length varies significantly
    output_tokens_estimate = (300, 900)  # (p50_tokens, p95_tokens)
```

To pick good values, run your agent on a few representative inputs and note the token counts. Set p50 to what you see on normal inputs, p95 to what you see on long or complex ones. When in doubt, be generous with p95.

## CostEstimate Fields

`agent.estimated_cost` returns a `CostEstimate` with four fields:

`p50` — Median expected cost in USD.

`p95` — 95th-percentile expected cost in USD.

`sufficient` — `True` when `budget.max_cost >= p95`. Your budget covers the worst-case estimate.

`low_confidence` — `True` when Syrin used the built-in fallback (500 tokens at $3/M) because you haven't declared `output_tokens_estimate` and have no recorded cost history. Treat low-confidence estimates as order-of-magnitude signals, not precise projections.

`estimated_cost` returns `None` when `estimation=False` or when no budget is set.

## Estimation Resolution Order

For each agent class, Syrin picks its cost source in this priority order:

First, it looks for `output_tokens_estimate` on the agent class — the most explicit and highest-confidence source.

Second, it looks at historical p50/p95 from the auto-store. When `estimation=True`, Syrin automatically records every run cost to `~/.syrin/budget_stats.json`. After one real run, future estimates draw from this history.

Third, it looks at a custom `FileBudgetStore` if you've configured one.

Finally, if none of the above are available, it falls back to 500 tokens at $3/M — a rough guess. This gives `low_confidence=True`.

## How History Improves Estimates

The first time you run an agent with `estimation=True`, the estimate is low-confidence (no history yet). After the first successful run, Syrin auto-records the actual cost. On the next access, the estimate uses real data and `low_confidence` becomes `False`:

```python
from syrin import Agent, Budget, Model

class ResearchAgent(Agent):
    model = Model.mock()

agent = ResearchAgent(budget=Budget(max_cost=5.00, estimation=True))

est = agent.estimated_cost
print(f"low_confidence: {est.low_confidence}")  # True — no history yet

agent.run("Summarise AI trends")  # Cost auto-recorded internally

est = agent.estimated_cost
print(f"low_confidence: {est.low_confidence}")  # False — using real history
```

## Estimation Policies

Control what happens when `sufficient=False`:

```python
from syrin import Budget
from syrin.enums import EstimationPolicy

# WARN_ONLY (default) — logs a warning, returns the estimate, never raises
budget = Budget(max_cost=0.50, estimation=True, estimation_policy=EstimationPolicy.WARN_ONLY)

# RAISE — raises InsufficientBudgetError before the run starts
budget = Budget(max_cost=0.50, estimation=True, estimation_policy=EstimationPolicy.RAISE)

# DISABLED — compute the estimate but skip all policy checks
budget = Budget(max_cost=0.50, estimation=True, estimation_policy=EstimationPolicy.DISABLED)
```

`WARN_ONLY` is the gentlest option — you get the estimate and a log warning, but the run is never blocked. `RAISE` raises `InsufficientBudgetError` inside `.estimated_cost` itself, so `agent.run()` is never reached. `DISABLED` computes nothing.

Catching the error:

```python
from syrin.budget import InsufficientBudgetError

try:
    est = agent.estimated_cost  # Raises here, not in agent.run()
    result = await agent.run("Summarise AI trends")
except InsufficientBudgetError as e:
    print(f"p95 ${e.total_p95:.4f} exceeds budget ${e.budget_configured:.4f}")
    # e.total_p50 — median estimate
    # e.total_p95 — 95th-percentile estimate
    # e.budget_configured — your max_cost
```

## Swarm and Pipeline Estimation

`.estimated_cost` on a swarm aggregates across all agents — the p50 and p95 are sums:

```python
from syrin import Budget, Model
from syrin.swarm import Swarm

class ResearchAgent(Agent):
    model = Model.mock()
    output_tokens_estimate = (300, 900)

class WriterAgent(Agent):
    model = Model.mock()
    output_tokens_estimate = 400

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

## Budget Guardrails

Guardrails are explicit checks you call at decision points in your orchestration code. They don't run automatically.

**Fanout guard** — limit how many agents you spawn at once:

```python
from syrin.budget import BudgetGuardrails, DynamicFanoutError

agents_to_spawn = build_agent_list(task)
try:
    BudgetGuardrails.check_fanout(items=agents_to_spawn, max_agents=10)
except DynamicFanoutError as e:
    print(f"Requested {e.requested} agents but max is {e.max_allowed}")
```

**Daily spend limit** — raise if already over the daily cap:

```python
BudgetGuardrails.check_daily_limit(spent_today=51.00, daily_limit=50.00)
```

**Approaching daily limit** — fire a hook when getting close:

```python
BudgetGuardrails.check_daily_approaching(
    spent_today=42.00,
    daily_limit=50.00,
    fire_fn=my_hook_fn,  # Fires Hook.DAILY_LIMIT_APPROACHING at 80%
)
```

**Retry budget** — stop retrying when retries consume too much of the budget:

```python
from syrin.budget import BudgetGuardrails, RetryBudgetExhausted

try:
    BudgetGuardrails.check_retry_budget(
        retry_spent=0.35,
        max_cost=1.00,
        max_ratio=0.30,  # Max 30% of budget on retries
    )
except RetryBudgetExhausted as e:
    print(f"Retry budget exhausted at ${e.retry_spent:.4f}")
```

**Anomaly detection** — catch unexpected cost spikes:

```python
from syrin.budget import BudgetGuardrails, AnomalyConfig

config = AnomalyConfig(threshold_multiplier=2.0)

# Fires Hook.BUDGET_ANOMALY when actual > 2 × p95
BudgetGuardrails.check_anomaly(
    actual=result.cost,
    p95=est.p95,
    config=config,
    fire_fn=my_hook_fn,
)
```

## Custom Estimator

Override `estimate_agent()` to use your own cost model — internal pricing sheets, provider quotes, or team benchmarks:

```python
from syrin.budget import CostEstimator, CostEstimate

class TieredEstimator(CostEstimator):
    _TIERS = {
        "ResearchAgent": (0.05, 0.12),
        "WriterAgent":   (0.02, 0.04),
        "HeavyAgent":    (0.50, 2.00),
    }

    def estimate_agent(self, agent_class: type) -> CostEstimate:
        p50, p95 = self._TIERS.get(agent_class.__name__, (0.01, 0.03))
        return CostEstimate(p50=p50, p95=p95, sufficient=True, low_confidence=False)

budget = Budget(
    max_cost=5.00,
    estimation=True,
    estimator=TieredEstimator(),
)
```

`estimate_agent()` receives the agent class (not an instance). Return `sufficient=True` — the aggregation layer sets the final `sufficient` value based on the actual budget.

## Hooks

Three hooks fire for estimation events:

`Hook.ESTIMATION_COMPLETE` — fires when `estimated_cost` is accessed and `estimation=True`. Context includes `p50`, `p95`, `sufficient`, `low_confidence`.

`Hook.BUDGET_ANOMALY` — fires from `check_anomaly()` when actual cost exceeds `threshold_multiplier × p95`.

`Hook.DAILY_LIMIT_APPROACHING` — fires from `check_daily_approaching()` when daily spend crosses the threshold.

```python
from syrin.enums import Hook

agent.events.on(Hook.ESTIMATION_COMPLETE, lambda ctx: print(
    f"Estimate: p50=${ctx['p50']:.4f}  p95=${ctx['p95']:.4f}  sufficient={ctx['sufficient']}"
))
```

## Complete Example

```python
import asyncio
from pathlib import Path
from syrin import Agent, Budget, Model
from syrin.budget import CostEstimator, FileBudgetStore, InsufficientBudgetError
from syrin.enums import EstimationPolicy

class ResearchAgent(Agent):
    model = Model.mock()
    output_tokens_estimate = (300, 900)

store = FileBudgetStore(path=Path("~/.syrin/costs.jsonl"))

budget = Budget(
    max_cost=2.00,
    estimation=True,
    estimation_policy=EstimationPolicy.RAISE,
    estimator=CostEstimator(store=store),
)

agent = ResearchAgent(budget=budget)

try:
    est = agent.estimated_cost  # Raises InsufficientBudgetError if p95 > $2.00
except InsufficientBudgetError as e:
    print(f"Budget too small: p95 ${e.total_p95:.4f} > ${e.budget_configured:.2f}")
    raise SystemExit(1)

assert est is not None
print(f"Expected cost: ${est.p50:.4f}–${est.p95:.4f}")
print(f"Confidence: {'high' if not est.low_confidence else 'low'}")

async def main():
    result = await agent.arun("Summarise the latest AI research trends")
    print(f"Actual cost: ${result.cost:.6f}")
    store.record(agent_name="ResearchAgent", cost=result.cost)

asyncio.run(main())
```

## What's Next?

- [Budget Callbacks](/core/budget-callbacks) — React to budget events with thresholds
- [Budget Overview](/core/budget) — Budget basics and rate limits
- [Model Routing](/core/models-routing) — Budget-aware model selection
