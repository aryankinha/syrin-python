---
title: Budget Guardrails
description: Explicit budget protection checkpoints — dynamic fanout limits, A2A message budgets, retry caps, and tool call storm prevention.
weight: 50
---

## What Are Budget Guardrails?

Budget guardrails are explicit, stateless checks you call at decision points in your orchestration code. They don't run automatically — you invoke them at the boundaries you care about.

Think of them as assertions: "before I spawn 50 agents, check that I'm allowed to." If the check fails, a specific exception tells you exactly what the limit was and what you tried to do.

All guardrails live in `BudgetGuardrails` as static methods.

## Dynamic Fanout Guard

Prevents a dynamic step from spawning an unbounded number of agents — which would make costs completely unpredictable:

```python
from syrin.budget import BudgetGuardrails, DynamicFanoutError

agents_to_spawn = build_agent_list(task)

try:
    BudgetGuardrails.check_fanout(items=agents_to_spawn, max_agents=20)
except DynamicFanoutError as e:
    print(f"Requested {e.requested} agents — limit is {e.max_allowed}")
    # Don't spawn any — avoid partial spawns and partial costs
```

`DynamicFanoutError` has two attributes: `requested` (how many agents your lambda wanted to spawn) and `max_allowed` (your configured limit).

Call `check_fanout()` immediately after your dynamic lambda returns the agent list, before spawning any of them. This prevents partial spawns and the associated partial costs.

## Daily Spend Limit

Raise immediately if you've already exceeded the daily cap:

```python
from syrin.budget import BudgetGuardrails, BudgetLimitError

try:
    BudgetGuardrails.check_daily_limit(spent_today=51.00, daily_limit=50.00)
except BudgetLimitError:
    print("Daily budget exhausted — no more requests today")
```

To fire a warning hook before you hit the limit (at 80% by default):

```python
BudgetGuardrails.check_daily_approaching(
    spent_today=42.00,
    daily_limit=50.00,
    fire_fn=my_hook_fn,     # Fires Hook.DAILY_LIMIT_APPROACHING
    threshold_pct=0.80,     # Default: 0.80
)
```

## Retry Spend Cap

Prevents retries from eating a disproportionate fraction of the run budget. When retries cost more than `max_ratio × max_cost`, the run is aborted:

```python
from syrin.budget import BudgetGuardrails, RetryBudgetExhausted

try:
    BudgetGuardrails.check_retry_budget(
        retry_spent=0.35,
        max_cost=1.00,
        max_ratio=0.30,   # Max 30% of budget on retries
    )
except RetryBudgetExhausted as e:
    print(f"Retry budget exhausted at ${e.retry_spent:.4f} (limit ${e.limit:.4f})")
```

`RetryBudgetExhausted` has two attributes: `retry_spent` (actual retry cost in USD) and `limit` (the computed cap: `max_cost × max_ratio`).

Call `check_retry_budget()` after each retry attempt, before scheduling the next one.

## Anomaly Detection

Catches unexpected cost spikes — when actual spend for a single run is dramatically higher than the historical p95:

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

When `actual > p95 × threshold_multiplier`, the hook fires. It doesn't raise — it signals. What you do with the signal is up to you.

## A2A Message Budget

Control per-message spend and per-sender volume in agent-to-agent routing:

```python
from syrin.swarm import A2AConfig, A2ARouter

router = A2ARouter(config=A2AConfig(
    budget_per_message=0.05,       # Max USD per message
    max_messages_per_sender=50,    # Max messages any single agent can send
))
```

When `max_messages_per_sender` is exceeded, `A2ARouter.send()` raises `A2ABudgetExceededError`.

`A2AConfig` has four budget-relevant fields: `budget_per_message` (per-message cap in USD, default 0 = unlimited), `max_messages_per_sender` (max messages per sender, default 0 = unlimited), `max_message_size` (max serialized message size in bytes, default 0 = unlimited), and `max_queue_depth` (max queued messages per agent inbox, default 0 = unlimited).

The effective per-sender spend cap is: `budget_per_message × max_messages_per_sender`.

## BudgetEnforcer Guardrail

For action-level budget enforcement in agent guardrail chains, use `BudgetEnforcer`:

```python
from syrin.guardrails.built_in.budget import BudgetEnforcer

enforcer = BudgetEnforcer(
    max_amount=0.10,      # Max cost per action
    daily_limit=50.00,    # Optional daily cap
    weekly_limit=200.00,  # Optional weekly cap
    warn_threshold=0.20,  # Warn when < 20% of budget remains
)
```

`BudgetEnforcer` returns a `GuardrailDecision` — it doesn't raise. Attach it to an agent's guardrail list like any other guardrail.

## All Guardrail Methods at a Glance

```python
from syrin.budget import BudgetGuardrails

# Fanout: prevent too many dynamic agents
BudgetGuardrails.check_fanout(items=agent_list, max_agents=20)

# Daily limit: fail if today's spend already exceeds the cap
BudgetGuardrails.check_daily_limit(spent_today=51.00, daily_limit=50.00)

# Approaching: fire a warning hook before the daily cap is hit
BudgetGuardrails.check_daily_approaching(
    spent_today=42.00, daily_limit=50.00, fire_fn=my_hook_fn, threshold_pct=0.80
)

# Retry cap: stop retrying when retries consume too much budget
BudgetGuardrails.check_retry_budget(retry_spent=0.35, max_cost=1.00, max_ratio=0.30)

# Anomaly: fire a hook when actual cost is far above p95
BudgetGuardrails.check_anomaly(
    actual=result.cost, p95=est.p95,
    config=AnomalyConfig(threshold_multiplier=2.0), fire_fn=my_hook_fn
)
```

## Exception Reference

`DynamicFanoutError` from `syrin.budget` — raised by `check_fanout()` when too many agents are requested.

`RetryBudgetExhausted` from `syrin.budget` — raised by `check_retry_budget()` when retries exceed the ratio cap.

`BudgetLimitError` from `syrin.budget` — raised by `check_daily_limit()` when daily spend is exceeded.

`A2ABudgetExceededError` from `syrin.swarm` — raised by `A2ARouter.send()` when the sender message limit is reached.

## What's Next?

- [Budget Estimation](/budget/estimation) — Pre-run cost estimation
- [Budget Forecasting](/budget/forecasting) — Real-time mid-run projection
- [Budget Callbacks](/core/budget-callbacks) — Threshold actions and alerts
