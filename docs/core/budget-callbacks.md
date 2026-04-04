---
title: Budget Actions & Thresholds
description: Control what happens when budget limits are hit — ExceedPolicy, thresholds, and custom callbacks.
weight: 41
---

## A Budget Without an Action Is Useless

You set `Budget(max_cost=1.00)`. Now what? If you don't tell Syrin what to do when that limit is hit, nothing happens — the agent keeps running. A limit without an action is a suggestion.

Use `exceed_policy` to declare the action. Use `thresholds` to act *before* the limit is hit.

## ExceedPolicy — What Happens When the Budget Is Exceeded

`exceed_policy` is the canonical way to control budget exceed behavior. Pass it to `Budget`:

```python
from syrin import Agent, Budget, Model
from syrin.enums import ExceedPolicy

# Stop the run and raise BudgetExceededError (recommended for production)
agent = Agent(
    model=Model.mock(),
    budget=Budget(max_cost=0.50, exceed_policy=ExceedPolicy.STOP),
)

# Log a warning and continue (useful during development)
agent = Agent(
    model=Model.mock(),
    budget=Budget(max_cost=0.50, exceed_policy=ExceedPolicy.WARN),
)

# Silently continue (useful when budget is advisory only)
agent = Agent(
    model=Model.mock(),
    budget=Budget(max_cost=0.50, exceed_policy=ExceedPolicy.IGNORE),
)
```

| Policy | Behaviour | When to use |
|--------|-----------|-------------|
| `ExceedPolicy.STOP` | Raises `BudgetExceededError` — run stops immediately | Production. Hard cost ceiling. |
| `ExceedPolicy.WARN` | Logs a warning, run continues | Development. Non-critical apps. |
| `ExceedPolicy.IGNORE` | Silent — run continues | When budget is advisory/monitoring only. |

`ExceedPolicy.STOP` is the recommended default for production. It fires **before** the LLM call that would exceed the budget — the call is blocked, not made.

### Catching BudgetExceededError

```python
from syrin import Agent, Budget, Model
from syrin.enums import ExceedPolicy
from syrin.exceptions import BudgetExceededError

class MyAgent(Agent):
    model = Model.mock()
    budget = Budget(max_cost=0.50, exceed_policy=ExceedPolicy.STOP)

try:
    response = MyAgent().run("Long complex task")
except BudgetExceededError as e:
    print(f"Budget exceeded: spent=${e.current_cost:.4f}, limit=${e.limit:.4f}")
```

## Custom Callbacks (Advanced)

For custom integrations (Slack alerts, audit trails, database logging), pass an `on_exceeded=` callable. This is the escape hatch for cases where `ExceedPolicy` doesn't cover your use case:

```python
from syrin import Budget
from syrin.budget import BudgetExceededContext

def alert_to_slack(ctx: BudgetExceededContext) -> None:
    import httpx
    httpx.post(
        "https://hooks.slack.com/services/YOUR/WEBHOOK",
        json={
            "text": f"Budget exceeded: ${ctx.current_cost:.4f} of ${ctx.limit:.4f} ({ctx.budget_type.value})"
        },
    )

budget = Budget(max_cost=1.00, on_exceeded=alert_to_slack)
```

`BudgetExceededContext` has four fields: `current_cost`, `limit`, `budget_type` (a `BudgetLimitType` enum), and `message` (human-readable).

> **Note:** `on_exceeded=` is deprecated in favour of `exceed_policy=`. It still works and will be removed in a future major version. For custom integrations, use `on_exceeded=` only when `ExceedPolicy` is insufficient.

## Thresholds: React Before You Hit the Limit

`exceed_policy` is reactive — it fires after the limit is reached. Thresholds are proactive — they fire when you're getting close.

A threshold fires when budget usage crosses a percentage:

```python
from syrin import Agent, Budget, Model
from syrin.budget import BudgetThreshold
from syrin.enums import ExceedPolicy

class MyAgent(Agent):
    model = Model.mock()
    budget = Budget(
        max_cost=1.00,
        exceed_policy=ExceedPolicy.STOP,
        thresholds=[
            BudgetThreshold(at=50, action=lambda ctx: print("Halfway there!")),
            BudgetThreshold(at=80, action=lambda ctx: print("Getting expensive...")),
            BudgetThreshold(at=95, action=lambda ctx: print("Almost out!")),
        ],
    )
```

By default, only the highest crossed threshold fires. If you're at 85%, the 80% threshold fires — not 50%. To run all crossed thresholds, set `threshold_fallthrough=True`.

## The ThresholdContext Object

When a threshold fires, it receives a `ThresholdContext`:

```python
from syrin.budget import BudgetThreshold

def my_action(ctx) -> None:
    print(f"Percentage: {ctx.percentage}%")       # 0–100
    print(f"Metric: {ctx.metric}")                # ThresholdMetric.COST or TOKENS
    print(f"Current: {ctx.current_value}")        # USD spent or tokens used
    print(f"Limit: {ctx.limit_value}")            # The budget cap
    print(f"Parent: {type(ctx.parent).__name__}") # The Budget or Agent object
```

## Threshold Windows

Thresholds can monitor different time windows, not just the current run:

```python
from syrin import Budget, RateLimit
from syrin.budget import BudgetThreshold
from syrin.enums import ThresholdWindow

budget = Budget(
    max_cost=1.00,
    rate_limits=RateLimit(day=10.00),
    thresholds=[
        BudgetThreshold(at=80, action=alert_request),
        BudgetThreshold(at=90, action=alert_daily, window=ThresholdWindow.DAY),
        BudgetThreshold(at=75, action=alert_hourly, window=ThresholdWindow.HOUR),
    ],
)
```

## Switch to a Cheaper Model at 80%

```python
from syrin import Agent, Budget, Model
from syrin.budget import BudgetThreshold
from syrin.enums import ExceedPolicy

cheap = Model.OpenAI("gpt-4o-mini", api_key="your-key")
expensive = Model.OpenAI("gpt-4o", api_key="your-key")

def switch_to_cheap(ctx) -> None:
    if hasattr(ctx.parent, "switch_model"):
        ctx.parent.switch_model(cheap)
        print("Switched to gpt-4o-mini to conserve budget")

class MyAgent(Agent):
    model = expensive
    budget = Budget(
        max_cost=1.00,
        exceed_policy=ExceedPolicy.STOP,
        thresholds=[BudgetThreshold(at=80, action=switch_to_cheap)],
    )
```

## Event Hooks

Subscribe to budget events via `Hook`:

```python
from syrin.enums import Hook

agent.events.on(Hook.BUDGET_THRESHOLD, lambda ctx: print(f"Budget {ctx.get('percentage')}%"))
agent.events.on(Hook.BUDGET_EXCEEDED, lambda ctx: print(f"Exceeded: {ctx}"))
```

## Troubleshooting

**`exceed_policy` isn't stopping the run:** Make sure you passed `exceed_policy=ExceedPolicy.STOP`, not just `ExceedPolicy.STOP` alone. Also confirm the agent has a `budget=` set.

**Threshold isn't firing:** Check that usage actually crossed the percentage. With `threshold_fallthrough=False` (default), only the highest crossed threshold fires. Verify the `window` matches what you're monitoring.

**Exceeded fires after the call, not before:** `exceed_policy=ExceedPolicy.STOP` fires *before* the LLM call — the call is blocked. If you're seeing charges anyway, you may have set `exceed_policy=ExceedPolicy.WARN` or not set a policy.

## What's Next?

- [Budget Overview](/core/budget) — Budget basics and configuration
- [Models Routing](/core/models-routing) — Budget-aware model selection
