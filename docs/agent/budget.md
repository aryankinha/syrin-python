# Budget

> **BudgetStore & use case:** For BudgetStore, cost utilities, and the full use-case guide, see [Budget Control](../budget-control.md).

Control and track agent spending via budgets.

## Basic Usage

```python
from syrin import Agent, Budget

agent = Agent(
    model=model,
    budget=Budget(run=1.0),
)

response = agent.response("Hello")
print(agent.budget_summary)
print(response.budget_remaining)
```

## Budget Parameters

```python
Budget(
    run=1.0,                    # Per-run limit (USD)
    per=RateLimit(hour=10),     # Per-period limits
    on_exceeded=OnExceeded.ERROR,
    thresholds=[...],
    shared=False,
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `run` | `float \| None` | Max USD per run |
| `per` | `RateLimit \| None` | Per-period limits |
| `on_exceeded` | `OnExceeded` | Behavior when exceeded |
| `thresholds` | `list[Threshold]` | Switch/warn/stop at % |
| `shared` | `bool` | Share with child agents |

## OnExceeded

| Value | Behavior |
|-------|----------|
| `ERROR` | Raise `BudgetExceededError` |
| `STOP` | Stop gracefully |
| `WARN` | Log and continue |

## Budget Store

Persist budget across runs:

```python
from syrin.budget_store import FileBudgetStore

agent = Agent(
    model=model,
    budget=Budget(run=1.0),
    budget_store=FileBudgetStore("/tmp/budget.json"),
    budget_store_key="user_123",
)
```

## Response Fields

- `response.budget_remaining` — Remaining run budget
- `response.budget_used` — Used this run
- `response.budget` — `BudgetStatus` object

## See Also

- [Budget Control](../budget-control.md) — BudgetStore, cost utilities, full use-case guide
