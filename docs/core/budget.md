---
title: Budget Control
description: Give your AI agent a spending limit. Understand what it costs, what happens when it runs over, and how to protect yourself in production.
weight: 40
---

## Why this matters

In 2023, a fintech startup's AI pipeline went into a retry loop overnight. By morning it had made 340,000 API calls. The bill was $47,000. Nobody noticed until the credit card was declined. (The full story is in the [introduction](/agent-kit/introduction).)

That incident is not a freak accident. It is the default outcome when you run an LLM agent without a spending limit. Every token costs money. Loops happen. Prompts grow. A tiny prompt today becomes a 50,000-token monster after six months of feature additions.

Syrin's budget system exists because production AI without spending controls is not production AI — it is a time bomb.

---

## The core idea

You give your agent a budget the same way you give a contractor a project estimate. "You have $1.00. Do your best work within that. If you're about to go over, let me know."

The budget system tracks every dollar the agent spends in real time. Before each LLM call, it estimates the cost. After the call, it records the actual cost. When either number crosses your limit, the budget system fires — and your code decides what to do next.

---

## Your first budget

```python
from syrin import Agent, Budget, Model
from syrin.enums import ExceedPolicy

agent = Agent(
    model=Model.mock(),
    budget=Budget(max_cost=1.00, exceed_policy=ExceedPolicy.WARN),
)

response = agent.run("What is 2 + 2?")
print(f"Cost: ${response.cost:.6f}")
state = agent.budget_state
print(f"BudgetState: {state}")
print(f"  limit:        {state.limit}")
print(f"  remaining:    {state.remaining:.6f}")
print(f"  spent:        {state.spent:.6f}")
print(f"  percent_used: {state.percent_used:.4f}")
```

Output:

```
Cost: $0.000039
BudgetState: BudgetState(limit=1.0, remaining=0.999961, spent=3.9e-05, percent_used=0.0)
  limit:        1.0
  remaining:    0.999961
  spent:        0.000039
  percent_used: 0.0000
```

`Model.mock()` is a mock model — it returns placeholder text and uses a tiny fixed cost, so you can run every example here without an API key.

Two things to notice. First, the `Budget` constructor takes `max_cost` (the dollar cap) and `on_exceeded` (what to do when the cap is hit). Second, after the run, `agent.budget_state` gives you a `BudgetState` object with four fields: how much was the limit, how much is left, how much was spent, and what percentage was used.

---

## The three exceed behaviors

When an agent hits its limit, you have three choices. You express that choice by passing one of three built-in handler functions to `on_exceeded`.

### warn_on_exceeded — log it, keep going

```python
from syrin import Agent, Budget, Model
from syrin.enums import ExceedPolicy

agent = Agent(
    model=Model.mock(),
    budget=Budget(max_cost=0.000001, exceed_policy=ExceedPolicy.WARN),
)
response = agent.run("Say hello")
print(f"Got response despite budget: {response.content[:40]!r}")
```

Output:

```
WARNING:syrin.budget._core:Budget would be exceeded: estimated run cost $0.0015 >= $0.0000 (pre-call estimate)
WARNING:syrin.budget._core:Budget exceeded: run cost $0.0000 >= $0.0000
Got response despite budget: 'Lorem ipsum dolor sit amet, consectetur '
```

The agent ran anyway. The warning went to the Python `logging` system, and the response came back normally. Use this in places where interrupting the user is worse than overspending slightly — for example, when you are still gathering baseline data on real costs before tightening the limit.

### raise_on_exceeded — stop and raise an exception

```python
from syrin import Agent, Budget, Model
from syrin.enums import ExceedPolicy
from syrin.exceptions import BudgetExceededError

agent = Agent(
    model=Model.mock(),
    budget=Budget(max_cost=0.000001, exceed_policy=ExceedPolicy.STOP),
)
try:
    agent.run("Say hello")
except BudgetExceededError as e:
    print(f"BudgetExceededError raised: {e}")
    print(f"  current_cost: {e.current_cost}")
    print(f"  limit:        {e.limit}")
    print(f"  budget_type:  {e.budget_type}")
```

Output:

```
BudgetExceededError raised: Budget would be exceeded: estimated run cost $0.0015 >= $0.0000 (pre-call estimate)
  current_cost: 0.001537
  limit:        1e-06
  budget_type:  run
```

The LLM call never happened. Syrin estimated the cost before sending the request, saw it would exceed the limit, and raised `BudgetExceededError` immediately. Notice `budget_type: run` — this tells you it was the per-run limit that tripped, not a rate limit. Use this in production where you need hard guarantees: if the agent cannot finish within budget, your code wants to know right away and handle it (retry with a cheaper model, return a graceful error to the user, alert on-call).

### stop_on_exceeded — stop and raise a different exception

```python
from syrin import Agent, Budget, Model
from syrin.enums import ExceedPolicy
from syrin.exceptions import BudgetExceededError

agent = Agent(
    model=Model.mock(),
    budget=Budget(max_cost=0.000001, exceed_policy=ExceedPolicy.STOP),
)
try:
    agent.run("Say hello")
except BudgetExceededError as e:
    print(f"BudgetExceededError raised: {e}")
```

Output:

```
BudgetExceededError raised: Budget would be exceeded: estimated run cost $0.0015 >= $0.0000 (pre-call estimate)
```

`stop_on_exceeded` raises `BudgetThresholdError` (a subclass of `BudgetExceededError`), which you can catch via `BudgetExceededError`. It signals "the agent stopped intentionally because it hit a limit" — which can be useful when you want to distinguish a budget stop from other errors. In practice, most teams choose between `warn_on_exceeded` (during development) and `raise_on_exceeded` (in production).

---

## Rate limits: caps over time

A per-run limit protects you from one expensive call. Rate limits protect you from many cheap calls that add up over hours or days.

```python
from syrin import Agent, Budget, Model
from syrin import RateLimit

agent = Agent(
    model=Model.mock(),
    budget=Budget(
        max_cost=1.00,
        exceed_policy=ExceedPolicy.WARN,
        rate_limits=RateLimit(
            hour=5.00,
            day=20.00,
            week=50.00,
            month=200.00,
        ),
    ),
)
response = agent.run("What is 2 + 2?")
print(f"Cost: ${response.cost:.6f}")
print("Rate limits configured correctly")
print(f"RateLimit(hour=5.00, day=20.00, week=50.00, month=200.00)")

rl = RateLimit(hour=5.00, day=20.00)
print(f"RateLimit object: {rl}")
print(f"  hour: {rl.hour}")
print(f"  day:  {rl.day}")
print(f"  week: {rl.week}")
```

Output:

```
Rate limits (hour/day/week/month) are in-memory only; pass budget_store (e.g. FileBudgetStore) to persist across restarts.
Cost: $0.000039
Rate limits configured correctly
RateLimit(hour=5.00, day=20.00, week=50.00, month=200.00)
RateLimit object: hour=5.0 day=20.0 week=None month=None month_days=30 calendar_month=False
  hour: 5.0
  day:  20.0
  week: None
```

`RateLimit` takes any combination of `hour`, `day`, `week`, and `month`. Each is optional — you can set only `day=20.00` if that is all you need. All values are in USD.

One thing to pay attention to: rate limit tracking is in-memory by default. If your process restarts, the counter resets. For production use where you need the limits to survive restarts, pass a persistent store. See the [budget store documentation](/agent-kit/core/budget-store) for details.

`RateLimit` also accepts `month_days` (default 30) for the rolling window length, and `calendar_month=True` if you want the month window to reset at the start of each calendar month rather than roll continuously.

---

## Thresholds: fire callbacks at percentage milestones

A limit tells you when you have run out. A threshold tells you when you are getting close, so you can act before you run out.

```python
from syrin import Agent, Budget, Model
from syrin import BudgetThreshold

fired = []

def on_75_percent(ctx):
    fired.append(f"75% threshold: {ctx.percentage}% used, ${ctx.current_value:.6f} spent")

agent = Agent(
    model=Model.mock(),
    budget=Budget(
        max_cost=0.00005,
        exceed_policy=ExceedPolicy.WARN,
        thresholds=[
            BudgetThreshold(at=75, action=on_75_percent),
        ],
    ),
)

response = agent.run("Say hello")
print(f"Cost: ${response.cost:.6f}")
state = agent.budget_state
print(f"Percent used: {state.percent_used:.1f}%")
for msg in fired:
    print(f"Threshold fired: {msg}")
```

Output:

```
Budget would be exceeded: estimated run cost $0.0015 >= $0.0001 (pre-call estimate)
Cost: $0.000039
Percent used: 78.0%
Threshold fired: 75% threshold: 77% used, $0.000039 spent
```

`BudgetThreshold(at=75, action=on_75_percent)` means: when the agent has used 75% or more of its budget, call `on_75_percent`. The `at` value is a percentage from 0 to 100.

The `action` function receives a `ThresholdContext` — an event object with these fields:

- `percentage` — what percentage triggered the threshold (e.g. `77`)
- `current_value` — how much has been spent in USD so far
- `limit_value` — what the full budget limit is
- `metric` — what is being measured (usually `"cost"`)
- `parent` — the `Agent` instance, so you can reach back into the agent from inside the callback

You can use this to switch models when money runs low. The most common pattern is to check `ctx.percentage` and swap to a cheaper model via `ctx.parent`:

```python
from syrin import Agent, Budget, Model
from syrin import BudgetThreshold

cheap_model = Model.mock()  # In production: Model.OpenAI("gpt-4o-mini")

def downgrade_model(ctx):
    print(f"At {ctx.percentage}% — switching to cheaper model")
    ctx.parent.model = cheap_model

agent = Agent(
    model=Model.mock(),
    budget=Budget(
        max_cost=0.00005,
        exceed_policy=ExceedPolicy.WARN,
        thresholds=[
            BudgetThreshold(at=80, action=downgrade_model),
        ],
    ),
)
```

When multiple thresholds are defined, the default behavior (`threshold_fallthrough=False`) runs only the highest threshold that was crossed. Set `threshold_fallthrough=True` if you want every crossed threshold to fire.

---

## Shared budgets in Swarms

When you pass a `Budget` to a `Swarm`, sharing is automatic — all agents draw from the same pool. No extra parameters needed.

```python
from syrin import Agent, Budget, Model
from syrin.enums import ExceedPolicy

swarm_budget = Budget(
    max_cost=2.00,
    exceed_policy=ExceedPolicy.WARN,
)

agent = Agent(
    model=Model.mock(),
    budget=swarm_budget,
)
response = agent.run("Hello")
print(f"Cost: ${response.cost:.6f}")
state = agent.budget_state
print(f"remaining: ${state.remaining:.6f}")
print(f"spent: ${state.spent:.6f}")
```

Output:

```
Cost: $0.000038
remaining: $1.999962
spent: $0.000038
```

Shared budgets are the building block for multi-agent cost control. Pass the same `Budget` instance to a `Swarm` and all agents draw from the shared `max_cost` pool. The full picture — including how sub-agents borrow from a parent pool and what happens when the pool is exhausted — is covered in the [budget delegation guide](/agent-kit/multi-agent/budget-delegation).

---

## Reading BudgetState

After any `agent.run()` call, `agent.budget_state` returns a `BudgetState` object. It is a frozen dataclass — all four fields are read-only.

```python
from syrin import Agent, Budget, Model
from syrin.enums import ExceedPolicy

agent = Agent(
    model=Model.mock(),
    budget=Budget(max_cost=1.00, exceed_policy=ExceedPolicy.WARN),
)

response = agent.run("What is the sky?")
state = agent.budget_state

print(f"type: {type(state).__name__}")
print(f"state.limit:        {state.limit}")
print(f"state.remaining:    {state.remaining:.6f}")
print(f"state.spent:        {state.spent:.6f}")
print(f"state.percent_used: {state.percent_used:.4f}")
print()
print(f"to_dict(): {state.to_dict()}")
```

Output:

```
type: BudgetState
state.limit:        1.0
state.remaining:    0.999960
state.spent:        0.000040
state.percent_used: 0.0000

to_dict(): {'limit': 1.0, 'remaining': 0.99996, 'spent': 4e-05, 'percent_used': 0.0}
```

- `limit` — the effective spending cap for this run (in USD). If you set `reserve`, the limit is `max_cost - reserve`.
- `remaining` — how much budget is left. Never goes below zero.
- `spent` — how much has been spent in this run so far.
- `percent_used` — `spent / limit * 100`, capped at 100. Useful for display and alerting.
- `to_dict()` — serialises the state to a plain dict, ready for logging or sending to a monitoring system.

If no budget is configured, `agent.budget_state` returns `None`. Always guard with `if state:` before reading fields when writing reusable code.

---

## The reserve parameter

There is one more parameter worth knowing: `reserve`. It holds back a slice of your budget specifically for the final reply.

```python
from syrin import Budget
from syrin.enums import ExceedPolicy

b = Budget(max_cost=1.00, reserve=0.20, exceed_policy=ExceedPolicy.WARN)
print(f"max_cost: {b.max_cost}")
print(f"reserve:  {b.reserve}")
print(f"Effective run limit = max_cost - reserve = {b.max_cost - b.reserve:.2f}")
```

Output:

```
max_cost: 1.0
reserve:  0.2
Effective run limit = max_cost - reserve = 0.80
```

Without `reserve`, an agent can spend 99 cents on tool calls and then try to generate a reply with only 1 cent left. The response ends up truncated — or the model refuses to answer at all. Setting `reserve=0.20` means the agent's effective processing budget is $0.80, and the remaining $0.20 is always available for the reply. A good rule of thumb is 10–20% of `max_cost`.

---

## What's next

- **[Budget Delegation](/agent-kit/multi-agent/budget-delegation)** — shared pools across orchestrators and sub-agents, per-agent caps, and mid-run reallocation
- **[Concepts](/agent-kit/concepts)** — how budget integrates with the rest of the agent lifecycle
- **[Troubleshooting](/agent-kit/troubleshooting)** — common budget errors and how to fix them
