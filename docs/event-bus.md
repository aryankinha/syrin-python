# Event Bus — Typed Domain Events

The **event bus** (`EventBus`) lets you subscribe to **typed domain events** such as `BudgetThresholdReached` and `ContextCompacted`. Use it when you need structured, type-safe event handling for metrics, observability, or custom pipelines.

## When to Use the Event Bus

| Scenario | Event bus | Hooks (`agent.events`) |
|----------|-----------|------------------------|
| **Quick logging** | Optional | ✅ Use Hooks |
| **Type-safe handlers** | ✅ Use bus | Hooks use dicts |
| **Metrics / dashboards** | ✅ Use bus | Possible but manual |
| **Observability pipelines** | ✅ Use bus | Possible but manual |
| **IDE autocomplete** | ✅ Typed events | Dict access only |
| **Multiple subscribers** | ✅ Subscribe per type | One handler per hook |
| **With default hooks** | Add-on | Default API |

**Use the event bus when:**
- You need typed event payloads (e.g. `e.percentage`, `e.tokens_before`) instead of dict keys
- You're building metrics, tracing, or analytics pipelines
- You want multiple handlers for the same event type
- You prefer structured events over generic `EventContext` dicts

**Use Hooks when:**
- You're doing simple logging or debugging
- You don't need typed payloads
- You want the default, zero-config API

## How It Works

1. Create an `EventBus`.
2. Subscribe handlers to specific event types.
3. Pass the bus to the agent via `bus=bus`.
4. The agent emits typed events when they occur; your handlers are called.

```
Agent runs → budget threshold crossed → emits BudgetThresholdReached
                                        ↓
                              bus.emit(event)
                                        ↓
                              Subscribed handlers run
                                        ↓
                              e.g. metrics.increment(...)
```

## Quick Start

```python
from syrin import Agent, Budget, Model
from syrin.domain_events import EventBus, BudgetThresholdReached, ContextCompacted

bus = EventBus()

# Subscribe to budget threshold events
bus.subscribe(BudgetThresholdReached, lambda e: print(f"Budget at {e.percentage}%"))

# Subscribe to context compaction events
bus.subscribe(ContextCompacted, lambda e: print(f"Compacted: {e.method}"))

agent = Agent(
    # model=Model("openai/gpt-4o-mini"),
    model=Model.Almock(),  # No API Key needed
    budget=Budget(run=0.50),
    bus=bus,
)

agent.response("Hello")
# Handlers run when events occur
```

## Using the Builder

```python
agent = (
    Agent.builder(Model("openai/gpt-4o-mini"))
    .with_budget(Budget(run=0.5))
    .with_bus(bus)
    .build()
)
```

## Event Types

### BudgetThresholdReached

Emitted when a budget threshold is crossed (e.g. 80% of run budget).

| Field | Type | Description |
|-------|------|-------------|
| `percentage` | int | Utilization (0–100) that triggered the threshold |
| `current_value` | float | Current cost or token count |
| `limit_value` | float | Limit or cap |
| `metric` | str | `"cost"` or `"tokens"` |
| `action_taken` | str \| None | Action from threshold (e.g. `"warn"`, `"switch_model"`) |

```python
bus.subscribe(BudgetThresholdReached, lambda e: log(f"Budget at {e.percentage}%: ${e.current_value:.2f}"))
```

### ContextCompacted

Emitted when the context window is compacted (truncation or summarization).

| Field | Type | Description |
|-------|------|-------------|
| `method` | str | Compaction method (e.g. `"middle_out"`, `"truncate"`) |
| `tokens_before` | int | Token count before compaction |
| `tokens_after` | int | Token count after compaction |
| `messages_before` | int | Messages before compaction |
| `messages_after` | int | Messages after compaction |

```python
bus.subscribe(ContextCompacted, lambda e: metrics.histogram("context.tokens_saved", e.tokens_before - e.tokens_after))
```

## Scenarios

### Metrics and Dashboards

Track budget utilization and context compaction in your monitoring system:

```python
import prometheus_client

budget_usage = prometheus_client.Gauge("syrin_budget_percent", "Budget utilization %")
tokens_saved = prometheus_client.Histogram("syrin_context_tokens_saved", "Tokens saved by compaction")

bus = EventBus()
bus.subscribe(BudgetThresholdReached, lambda e: budget_usage.set(e.percentage))
bus.subscribe(ContextCompacted, lambda e: tokens_saved.observe(e.tokens_before - e.tokens_after))

agent = Agent(model=..., budget=..., bus=bus)
```

### Observability Pipelines

Forward events to your observability backend:

```python
bus = EventBus()

def forward_to_otel(event):
    # OpenTelemetry, Datadog, etc.
    tracer.span("syrin.event", attributes={
        "event.type": type(event).__name__,
        **event.__dict__,
    })

bus.subscribe(BudgetThresholdReached, forward_to_otel)
bus.subscribe(ContextCompacted, forward_to_otel)

agent = Agent(model=..., bus=bus)
```

### Alerts and Notifications

Notify when budgets or context hit thresholds:

```python
bus = EventBus()

def alert_on_high_budget(e: BudgetThresholdReached):
    if e.percentage >= 90:
        slack.send(f"⚠️ Budget at {e.percentage}% (${e.current_value:.2f})")

bus.subscribe(BudgetThresholdReached, alert_on_high_budget)
agent = Agent(model=..., budget=..., bus=bus)
```

### Subscribing to Base Types

You can subscribe to `DomainEvent` to receive all domain events:

```python
bus.subscribe(DomainEvent, lambda e: print(type(e).__name__, e))
```

## Relationship to Hooks

- **Hooks** (`agent.events`) are the default API. They use string event names and `EventContext` dicts.
- **Event bus** is optional. It uses typed dataclasses and `bus.subscribe(event_type, handler)`.

Both can be used together. When you pass `bus=bus`, the agent emits to the bus **in addition to** running hook handlers. Hooks remain for simple use cases and per-agent handlers.

## See Also

- [Events & Hooks](agent/events-hooks.md) — Default event API
- [Budget Control](budget-control.md) — Budget and thresholds
- [Context](context.md) — Context window and compaction
