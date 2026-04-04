---
title: Cross-Run Limits
description: Enforce daily and weekly spending caps that persist across multiple agent runs using BudgetGuardrails and Hook.DAILY_LIMIT_APPROACHING.
weight: 60
---

## Overview

`Budget.max_cost` limits spend within a single run. Cross-run limits control cumulative spend across multiple runs — over a day or a week — preventing runaway costs from many small jobs.

Syrin provides two mechanisms:

1. **`BudgetGuardrails.check_daily_limit()`** — a stateless check you call before each run using your own spend tracker.
2. **`BudgetEnforcer`** guardrail — an action-level guardrail that accepts `daily_limit` and `weekly_limit` for integration into guardrail chains.

---

## Daily limit with `BudgetGuardrails`

```python
from syrin.budget import BudgetGuardrails, BudgetLimitError

# Retrieve today's cumulative spend from your own store or DB
spent_today = your_store.get_spent_today()

try:
    BudgetGuardrails.check_daily_limit(spent_today=spent_today, daily_limit=50.00)
except BudgetLimitError as e:
    print(f"Daily limit ${e.limit:.2f} exceeded — spent ${e.spent:.2f} today")
    # Do not proceed with the run
```

`BudgetLimitError` exposes three attributes:

| Attribute | Type | Description |
|-----------|------|-------------|
| `spent` | float | Actual cumulative spend in USD |
| `limit` | float | Configured limit in USD |
| `limit_type` | str | Either `"daily"` or `"weekly"` — which kind of limit was exceeded |

---

## Weekly limit

The same `check_daily_limit()` method handles weekly limits — pass your weekly spend and the weekly cap:

```python
spent_this_week = your_store.get_spent_this_week()

try:
    BudgetGuardrails.check_daily_limit(
        spent_today=spent_this_week,
        daily_limit=200.00,        # weekly cap, same call signature
    )
except BudgetLimitError as e:
    print(f"Weekly cap exceeded: ${e.spent:.2f} / ${e.limit:.2f}")
```

Alternatively, use `BudgetEnforcer` which has dedicated `daily_limit` and `weekly_limit` fields:

```python
from syrin.guardrails.built_in.budget import BudgetEnforcer

enforcer = BudgetEnforcer(
    max_amount=10.00,       # per-action limit
    daily_limit=50.00,      # daily cap
    weekly_limit=200.00,    # weekly cap
)
```

---

## `Hook.DAILY_LIMIT_APPROACHING`

This hook fires when cumulative daily spend reaches 80% (configurable) of the daily cap — giving you time to alert or throttle before hitting the hard limit:

```python
from syrin.budget import BudgetGuardrails
from syrin.enums import Hook

def on_approaching(hook: Hook, data: dict) -> None:
    print(
        f"Daily budget {data['pct_used']:.1f}% used — "
        f"${data['spent_today']:.2f} of ${data['daily_limit']:.2f}"
    )

# Fire hook at 80% threshold (default)
BudgetGuardrails.check_daily_approaching(
    spent_today=42.00,
    daily_limit=50.00,
    fire_fn=on_approaching,
)

# Custom threshold — fire at 90%
BudgetGuardrails.check_daily_approaching(
    spent_today=46.00,
    daily_limit=50.00,
    fire_fn=on_approaching,
    threshold_pct=0.90,
)
```

### Hook payload fields

The `Hook.DAILY_LIMIT_APPROACHING` payload contains four fields:

| Field | Type | Description |
|-------|------|-------------|
| `spent_today` | float | Cumulative spend so far today in USD |
| `daily_limit` | float | Configured daily cap in USD |
| `pct_used` | float | Percentage of the daily limit already used (0–100) |
| `threshold_pct` | float | The percentage threshold that triggered the hook |

The hook fires once per call to `check_daily_approaching()` whenever the condition is met. To avoid repeated alerts, add your own deduplication (e.g. a flag per run or a cooldown timer).

---

## Cross-run spend tracking

Syrin does not maintain a cross-run spend counter itself — that is your application's responsibility. Common approaches:

**Redis counter (atomic, multi-process safe):**

```python
import redis

r = redis.Redis()

def get_spent_today() -> float:
    key = f"syrin:spend:{date.today().isoformat()}"
    val = r.get(key)
    return float(val) if val else 0.0

def record_run_cost(cost: float) -> None:
    key = f"syrin:spend:{date.today().isoformat()}"
    r.incrbyfloat(key, cost)
    r.expire(key, 86400 * 2)  # auto-expire after 2 days
```

**SQLite / Postgres:** Query `SUM(cost) WHERE timestamp > today_start`.

**FileBudgetStore:** Read `stats.total_cost` (note: this is all-time, not just today).

---

## Complete example: daily cap with early warning

```python
import asyncio
from datetime import date
from syrin import Agent, Budget, Model
from syrin.budget import BudgetGuardrails, BudgetLimitError
from syrin.enums import Hook
from syrin.response import Response


class ResearchAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")
    # Use Model.mock() above for testing without an API key
    system_prompt = "Research the given topic."

    async def arun(self, input_text: str) -> Response[str]:
        return Response(content=f"Findings on {input_text}", cost=0.08)


# Simple in-memory spend tracker for the example
_spend_today: float = 43.00  # simulated: already spent $43 today


async def run_agent_with_daily_cap(topic: str) -> None:
    daily_cap = 50.00

    # Fire warning hook if approaching limit
    BudgetGuardrails.check_daily_approaching(
        spent_today=_spend_today,
        daily_limit=daily_cap,
        fire_fn=lambda hook, data: print(
            f"Warning: {data['pct_used']:.1f}% of daily budget used"
        ),
    )

    # Hard check — abort if already over
    try:
        BudgetGuardrails.check_daily_limit(
            spent_today=_spend_today,
            daily_limit=daily_cap,
        )
    except BudgetLimitError as e:
        print(f"Skipping run — daily limit ${e.limit:.2f} already reached")
        return

    # Run the agent
    agent = ResearchAgent(budget=Budget(max_cost=1.00))
    result = await agent.arun(topic)
    print(f"Done. Cost this run: ${result.cost:.4f}")


asyncio.run(run_agent_with_daily_cap("AI market trends"))
```

---

## Persistence across restarts

Neither `Budget` nor `BudgetGuardrails` persist cross-run spend to disk. You must persist and load the spend counter yourself. The `FileBudgetStore` can serve as a historical record, but it stores per-run costs — aggregating them across a calendar day is your code's job.

For a simple single-process setup, a JSON file or SQLite database keyed by date is sufficient. For multi-process or distributed environments, use Redis with an atomic `INCRBYFLOAT` counter.
