---
title: Cost History
description: Track historical run costs with CostStats, FileBudgetStore, RollingBudgetStore, and custom backends to power estimation and anomaly detection.
weight: 20
---

## Overview

Syrin records the actual cost of each agent run and accumulates statistics over time. These statistics power:

- Pre-flight estimation (p50/p95 cost projections)
- Anomaly detection (compare actual vs historical p95)
- Observability (trend tracking, cost audits)

History recording is automatic when `Budget(estimation=True)` is set. You can also query it directly for introspection.

---

## `CostStats`

`agent.cost_stats()` returns a `CostStats` dataclass for the agent's recorded run history:

```python
stats = agent.cost_stats()
print(f"Runs:        {stats.run_count}")
print(f"Mean:        ${stats.mean:.4f}")
print(f"p50:         ${stats.p50_cost:.4f}")
print(f"p95:         ${stats.p95_cost:.4f}")
print(f"p99:         ${stats.p99_cost:.4f}")
print(f"Std dev:     ${stats.stddev:.4f}")
print(f"Weekly trend: {stats.trend_weekly_pct:+.1f}%")
```

`CostStats` has nine fields:

| Field | Type | Description |
|-------|------|-------------|
| `agent_name` | str | The agent class name |
| `run_count` | int | Number of recorded runs |
| `mean` | float | Mean cost per run in USD |
| `p50_cost` | float | Median cost in USD |
| `p95_cost` | float | 95th-percentile cost — equals `max(costs)` when fewer than 20 samples |
| `p99_cost` | float | 99th-percentile cost — same conservative fallback for fewer than 20 samples |
| `stddev` | float | Population standard deviation in USD; `0.0` when `run_count < 2` |
| `total_cost` | float | Sum of all recorded run costs in USD |
| `trend_weekly_pct` | float | % change between mean of last 7 days and prior 7 days; `0.0` if either window is empty |

> With fewer than 20 samples, p95 and p99 equal the maximum observed cost rather than a percentile computation. This is intentional — it is conservative and avoids misleadingly precise estimates from small samples.

---

## How stats are accumulated

When `Budget(estimation=True)` is set, every successful `run()` or `arun()` call automatically records the actual run cost to a shared rolling store (`~/.syrin/budget_stats.json`). No manual calls to `store.record()` are needed.

The auto-store keeps the **100 most recent samples per agent** (configurable via `RollingBudgetStore(max_samples=N)`). Old samples are evicted as new ones arrive, so estimates stay current as your agent evolves.

```python
from syrin import Agent, Budget, Model

class ResearchAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")
    # Use Model.mock() above for testing without an API key
    system_prompt = "Research the given topic."

agent = ResearchAgent(budget=Budget(max_cost=5.00, estimation=True))
await agent.arun("AI market trends")  # cost auto-recorded

stats = agent.cost_stats()
print(f"p95: ${stats.p95_cost:.4f}")
```

---

## `BudgetStoreProtocol`

Any class that implements these three methods satisfies `BudgetStoreProtocol` and can be used as a budget history backend:

```python
from syrin.budget import BudgetStoreProtocol, CostStats

class MyStore:
    def record(self, agent_name: str, cost: float) -> None:
        ...  # write to your backend

    def stats(self, agent_name: str) -> CostStats:
        ...  # read from your backend, return CostStats

    def clear(self, agent_name: str) -> None:
        ...  # delete all records for this agent

store: BudgetStoreProtocol = MyStore()
```

---

## Built-in store backends

### `RollingBudgetStore` (default)

Compact JSON file (`~/.syrin/budget_stats.json`) with bounded rolling window. Used automatically by `Budget(estimation=True)`.

```python
from syrin.budget._history import RollingBudgetStore
from pathlib import Path

store = RollingBudgetStore(
    path=Path("~/.syrin/budget_stats.json").expanduser(),
    max_samples=200,  # keep more history (default: 100)
)

store.record("ResearchAgent", 0.05)
stats = store.stats("ResearchAgent")
print(stats.p50_cost)
```

- Storage is bounded: oldest entries are evicted when the window fills.
- Does not store timestamps, so `trend_weekly_pct` is always `0.0`.

### `FileBudgetStore` (append-only JSONL)

Append-only JSONL file. Every run appends one line. Preserves full history (unbounded). Supports `trend_weekly_pct`.

```python
from syrin.budget._history import FileBudgetStore
from pathlib import Path

store = FileBudgetStore(path=Path("~/.syrin/costs.jsonl").expanduser())
store.record(agent_name="ResearchAgent", cost=0.05)

stats = store.stats(agent_name="ResearchAgent")
print(f"Runs: {stats.run_count}  p95: ${stats.p95_cost:.4f}")
```

Multiple instances pointing to the same file are concurrency-safe (per-path threading locks).

Wire the store into an estimator so estimates use that history:

```python
from syrin import Budget
from syrin.budget import CostEstimator

budget = Budget(
    max_cost=1.00,
    estimation=True,
    estimator=CostEstimator(store=store),
)
```

### `HMACFileBudgetStore` (integrity-protected)

Same as `FileBudgetStore` but with HMAC-SHA256 integrity verification. Raises `IntegrityError` if the backing file is tampered with between writes. Also warns if the file is world-readable.

```python
import os
from syrin.budget._history import HMACFileBudgetStore, IntegrityError
from pathlib import Path

store = HMACFileBudgetStore(
    path=Path("~/.syrin/costs.jsonl").expanduser(),
    key=os.urandom(32),  # keep this key secure
)

try:
    stats = store.stats("ResearchAgent")
except IntegrityError:
    # File modified after last write — treat data as untrusted
    ...
```

See also: [Security](security.md) — SEC-08 covers anomaly masking defenses.

---

## Comparing backends

| Backend | Format | Bounded | Timestamps | HMAC | Best for |
|---------|--------|---------|------------|------|----------|
| `RollingBudgetStore` | Compact JSON | Yes (last 100 samples) | No (`trend_weekly_pct` always `0.0`) | No | Auto-store default |
| `FileBudgetStore` | Append-only JSONL | No | Yes (trend tracking works) | No | Audit logs and trend tracking |
| `HMACFileBudgetStore` | Append-only JSONL | No | Yes | SHA-256 | Production deployments where tamper detection matters |

---

## Querying history directly

```python
from syrin.budget._history import FileBudgetStore
from pathlib import Path

store = FileBudgetStore(path=Path("~/.syrin/costs.jsonl").expanduser())

stats = store.stats("ResearchAgent")
if stats.run_count == 0:
    print("No history yet")
else:
    print(f"Runs: {stats.run_count}")
    print(f"Mean: ${stats.mean:.4f}")
    print(f"p95:  ${stats.p95_cost:.4f}")
    if stats.trend_weekly_pct > 10:
        print(f"Warning: costs up {stats.trend_weekly_pct:.1f}% week-over-week")
```

---

## Clearing history

```python
store.clear("ResearchAgent")   # removes all records for this agent
```

Records for other agents are preserved.
