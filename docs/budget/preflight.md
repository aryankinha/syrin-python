---
title: Preflight Budget Checks
description: Validate that a configured budget covers historical p95 costs before the first LLM call, using PreflightPolicy to control failure behaviour.
weight: 30
---

## Overview

Preflight is a **pre-run validation** that compares the configured `max_cost` against historical p95 cost for the agent. If the budget looks insufficient, the policy controls whether the run is aborted or a warning is logged.

Preflight is distinct from estimation. Estimation (enabled with `estimation=True`) is triggered when you access `.estimated_cost`, draws on hints, history, and a fallback, and does not raise by default (the default policy is `WARN_ONLY`). Preflight (enabled with `preflight=True`) is triggered automatically before the first LLM call in `run()`, relies on historical p95 data only, and also does not raise by default (`WARN_ONLY`).

---

## Enabling preflight

```python
from syrin import Budget
from syrin.enums import PreflightPolicy

budget = Budget(
    max_cost=0.50,
    preflight=True,
    preflight_fail_on=PreflightPolicy.BELOW_P95,
)
```

When `preflight=True`, syrin checks historical p95 cost from the auto-store immediately before the first LLM call. If `max_cost < p95`, the configured policy is applied.

---

## `PreflightPolicy`

Two policies are available:

- `WARN_ONLY` — Default. Logs a warning and allows the run to continue regardless of the budget check outcome.
- `BELOW_P95` — Raises `InsufficientBudgetError` when `max_cost < p95`, aborting the run before any LLM calls are made.

```python
from syrin.enums import PreflightPolicy

# Default — warning only, run proceeds
budget = Budget(max_cost=0.50, preflight=True)

# Strict — raise if budget looks insufficient
budget = Budget(
    max_cost=0.50,
    preflight=True,
    preflight_fail_on=PreflightPolicy.BELOW_P95,
)
```

---

## `InsufficientBudgetError`

Raised by `BELOW_P95` preflight (and by `EstimationPolicy.RAISE` in the estimation path):

```python
from syrin.budget import InsufficientBudgetError
from syrin.enums import PreflightPolicy

budget = Budget(
    max_cost=0.001,
    preflight=True,
    preflight_fail_on=PreflightPolicy.BELOW_P95,
)
agent = ResearchAgent(budget=budget)

try:
    result = await agent.run("Summarise AI trends")
except InsufficientBudgetError as e:
    print(f"Budget ${e.budget_configured:.4f} insufficient")
    print(f"Historical p50: ${e.total_p50:.4f}")
    print(f"Historical p95: ${e.total_p95:.4f}")
    print(f"Policy: {e.policy}")
```

`InsufficientBudgetError` exposes four attributes:

| Attribute | Type | Description |
|-----------|------|-------------|
| `total_p50` | float | p50 cost estimate in USD |
| `total_p95` | float | p95 cost estimate in USD — the value that exceeded `max_cost` |
| `budget_configured` | float | The `max_cost` you configured |
| `policy` | EstimationPolicy | Which policy triggered the error |

---

## When preflight requires history

Preflight uses historical p95 from the auto-store. On the very first run (no history), p95 is `0.0` — so preflight always passes the first time for a new agent.

After a few runs accumulate, preflight becomes meaningful. To seed history for a new agent, run it once manually or use `store.record()` with representative cost data:

```python
from syrin.budget._history import FileBudgetStore
from pathlib import Path

store = FileBudgetStore(path=Path("~/.syrin/costs.jsonl").expanduser())
store.record("ResearchAgent", 0.12)   # seed with a representative run cost
store.record("ResearchAgent", 0.09)
store.record("ResearchAgent", 0.15)
```

---

## Preflight vs estimation: choosing the right tool

Use **estimation** when:

- You want to check costs at definition time or in CI.
- You want a cost signal before running expensive pipelines.
- You have no or little history (estimation uses token hints as a fallback).

Use **preflight** when:

- Agents have run enough times to accumulate meaningful history (10+ runs).
- You want a last-minute check immediately before the run starts.
- You want to avoid unexpected failures mid-run.

They can be combined:

```python
budget = Budget(
    max_cost=1.00,
    estimation=True,
    estimation_policy=EstimationPolicy.WARN_ONLY,   # soft check at definition time
    preflight=True,
    preflight_fail_on=PreflightPolicy.BELOW_P95,    # hard check before first LLM call
)
```

---

## Complete example

```python
import asyncio
from syrin import Agent, Budget, Model
from syrin.budget import InsufficientBudgetError
from syrin.enums import PreflightPolicy
from syrin.response import Response


class ResearchAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")
    # Use Model.mock() above for testing without an API key
    system_prompt = "Research the given topic."
    output_tokens_estimate = (300, 900)

    async def arun(self, input_text: str) -> Response[str]:
        return Response(content=f"Findings on {input_text}", cost=0.10)


async def main() -> None:
    budget = Budget(
        max_cost=0.05,
        preflight=True,
        preflight_fail_on=PreflightPolicy.BELOW_P95,
    )
    agent = ResearchAgent(budget=budget)

    try:
        result = await agent.arun("AI market trends")
        print(f"Cost: ${result.cost:.4f}")
    except InsufficientBudgetError as e:
        print(f"Aborted: budget ${e.budget_configured:.4f} < p95 ${e.total_p95:.4f}")


asyncio.run(main())
```
