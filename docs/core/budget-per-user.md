---
title: Per-User Budget Isolation
description: Track and enforce spending limits independently for each user in a multi-tenant agent deployment
weight: 95
---

## Shared Agents, Separate Bills

A single `Agent` instance often serves many users. Without isolation, their spending is pooled: a power user who sends a thousand requests burns through the daily rate limit for everyone else.

The solution is `budget_store_key`. Every agent call that carries a distinct key is tracked in its own accounting ledger. Users never share counts, never interfere with each other, and never see each other's history.

---

## The Pattern

Instantiate the agent once. Pass a per-user key at request time.

```python
import syrin
from syrin import Agent, Model
from syrin.budget import Budget
from syrin.budget_store import BudgetStore, FileBudgetStore

# Create a per-user budget store
def get_user_agent(user_id: str) -> Agent:
    store = FileBudgetStore(path=f"budgets/{user_id}.json")
    return Agent(
        model=Model.Anthropic("claude-sonnet-4-6"),
        budget=Budget(max_cost=1.00),
        budget_store=store,
    )
```

`FileBudgetStore` writes each user's accumulated spend to its own JSON file. The `Budget(max_cost=1.00)` is the per-request cap; the store persists rate-limit windows across restarts.

**Why one file per user?** It avoids write contention when many users are active simultaneously. Each file is locked independently. For higher scale, swap `FileBudgetStore` for a database-backed store.

---

## Tracking Spend Across Sessions

Budget windows (hour, day, month) survive process restarts when a persistent store is used. A user who spent $0.80 today and restarts the server still has only $0.20 remaining in their daily window.

```python
from syrin import Agent, Model
from syrin.budget import Budget, RateLimit
from syrin.budget_store import FileBudgetStore

FREE_TIER_BUDGET = Budget(
    max_cost=0.05,                          # $0.05 per request
    reserve=0.005,                          # Reserve for reply
    rate_limits=RateLimit(
        day=1.00,                           # $1.00 per day
        month=5.00,                         # $5.00 per month
    ),
)

def get_agent_for_user(user_id: str) -> Agent:
    return Agent(
        model=Model.Anthropic("claude-sonnet-4-6"),
        budget=FREE_TIER_BUDGET,
        budget_store=FileBudgetStore(path=f"/var/data/budgets/{user_id}.json"),
    )
```

The same pattern works for organization-level budgets: use `org_id` as the key and point all agents in that organization at the same store file.

---

## Tier-Based Budgets

Different users get different limits. Build a lookup at startup, not per-request:

```python
from syrin import Agent, Model
from syrin.budget import Budget, RateLimit
from syrin.budget_store import FileBudgetStore

TIER_BUDGETS: dict[str, Budget] = {
    "free": Budget(
        max_cost=0.05,
        rate_limits=RateLimit(day=1.00, month=5.00),
    ),
    "pro": Budget(
        max_cost=0.25,
        rate_limits=RateLimit(day=10.00, month=50.00),
    ),
    "enterprise": Budget(
        max_cost=2.00,
        rate_limits=RateLimit(day=200.00, month=2000.00),
    ),
}


def get_agent(user_id: str, tier: str) -> Agent:
    budget = TIER_BUDGETS.get(tier, TIER_BUDGETS["free"])
    store = FileBudgetStore(path=f"/var/data/budgets/{user_id}.json")
    return Agent(
        model=Model.Anthropic("claude-sonnet-4-6"),
        budget=budget,
        budget_store=store,
    )
```

---

## Inspecting a User's Budget State

After each request, inspect what was spent and what remains:

```python
agent = get_agent_for_user("user-42")
response = await agent.run("Summarize this document.")

print(f"This request cost: ${response.cost:.6f}")
print(f"Budget remaining:  ${response.budget_remaining:.4f}")
print(f"Budget used:       ${response.budget_used:.4f}")
```

For full window breakdowns (hourly, daily, monthly):

```python
tracker = agent.get_budget_tracker()

if tracker:
    summary = tracker.get_summary()
    print(f"Hourly spend:  ${summary.hourly_cost:.4f}")
    print(f"Daily spend:   ${summary.daily_cost:.4f}")
    print(f"Monthly spend: ${summary.monthly_cost:.4f}")
```

---

## Resetting a User's Budget

To reset a user's accumulated spend—after a billing cycle rolls over, or to grant a refill:

```python
from syrin.budget_store import FileBudgetStore

store = FileBudgetStore(path=f"/var/data/budgets/user-42.json")
store.reset("user-42")  # Clears all window accumulators for this key
```

`reset()` zeroes the rate-limit windows but does not change the budget limits themselves. The next request starts from zero spend.

To inspect the raw stored state before resetting:

```python
tracker = store.load("user-42")
if tracker:
    print(tracker.get_summary())
```

---

## Thread Safety

`FileBudgetStore` uses a per-file `threading.Lock`. Concurrent requests for the same user serialize their writes. Requests for different users (different files) run in parallel without contention.

For async workloads, the lock is acquired and released within a thread-pool executor so it does not block the event loop.

**At high concurrency**, replace `FileBudgetStore` with a database-backed store:

```python
from syrin.budget_store import BudgetStore, BudgetTracker


class PostgresBudgetStore(BudgetStore):
    def load(self, key: str) -> BudgetTracker | None:
        row = db.query("SELECT data FROM budgets WHERE key = %s", [key])
        return BudgetTracker.deserialize(row["data"]) if row else None

    def save(self, key: str, tracker: BudgetTracker) -> None:
        db.execute(
            """
            INSERT INTO budgets (key, data) VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET data = EXCLUDED.data
            """,
            [key, tracker.serialize()],
        )
```

Use `SELECT ... FOR UPDATE` or optimistic locking in your `save()` implementation to prevent race conditions when two requests for the same user complete at the same moment.

---

## What's Next?

- [Budget Control](/agent-kit/core/budget) — Full budget API: limits, reserves, rate windows
- [Budget Callbacks](/agent-kit/core/budget-callbacks) — React to threshold and exceeded events
- [Dependency Injection](/agent-kit/advanced/dependency-injection) — Inject per-request context including user identity

## See Also

- [Budget Control](/agent-kit/core/budget) — Budget configuration reference
- [Rate Limiting](/agent-kit/production/rate-limiting) — System-level rate limiting alongside per-user budgets
- [Deployment](/agent-kit/production/deployment) — Persisting budget stores in production environments
