---
title: Event-Driven Triggers (agent.watch())
description: Turn any agent into an event-driven worker using built-in webhook, cron, and queue protocols or your own framework integration.
weight: 145
---

# Event-Driven Triggers (agent.watch())

## Overview

`agent.watch()` turns an agent into a persistent, event-driven worker. Instead of calling `agent.run()` manually each time, the agent subscribes to an event source and processes incoming triggers automatically. Each trigger produces a full `AgentResponse` just like a direct `run()` call, including cost tracking, hooks, and structured output.

Three built-in protocols ship with syrin: `WebhookProtocol` (HTTP), `CronProtocol` (scheduled), and `QueueProtocol` (message queue). For frameworks that already own the server layer—FastAPI, Starlette, Django Channels—`agent.watch_handler()` returns a plain callable that you wire in yourself.

## Built-In Protocols

### WebhookProtocol

`WebhookProtocol` starts a lightweight HTTP server and fires the agent whenever a POST request arrives at the configured path. An optional `secret` enforces HMAC-SHA256 request signing so only trusted callers can trigger the agent.

```python
import asyncio
from syrin import Agent, Model
from syrin.watch import WebhookProtocol

agent = Agent(model=Model.Anthropic("claude-sonnet-4-6"))

async def main() -> None:
    await agent.watch(
        protocol=WebhookProtocol(
            path="/trigger",
            port=8080,
            secret="my-secret",   # Optional. Validates X-Syrin-Signature header.
        ),
        on_trigger=lambda evt: print(f"Got: {evt.input}"),
    )

asyncio.run(main())
```

The request body is passed verbatim as `TriggerEvent.input`. Any query parameters and headers are available in `TriggerEvent.metadata`.

### CronProtocol

`CronProtocol` accepts a standard five-field cron expression and fires the agent on that schedule. A static `input` string is delivered to the agent each time; use it to encode the task prompt that should run on the schedule.

```python
from syrin import Agent, Model
from syrin.watch import CronProtocol

agent = Agent(model=Model.Anthropic("claude-sonnet-4-6"))

async def main() -> None:
    await agent.watch(
        protocol=CronProtocol(
            schedule="0 * * * *",          # Every hour, on the hour
            input="Generate hourly report",
        ),
    )
```

`CronProtocol` uses UTC by default. Pass `timezone="America/New_York"` to override.

### QueueProtocol

`QueueProtocol` consumes messages from a message queue. The `source` parameter is a connection URL; the `queue` parameter names the queue or topic to subscribe to. The `concurrency` parameter on `agent.watch()` controls how many messages are processed in parallel.

```python
from syrin import Agent, Model
from syrin.watch import QueueProtocol

agent = Agent(model=Model.Anthropic("claude-sonnet-4-6"))

async def main() -> None:
    await agent.watch(
        protocol=QueueProtocol(
            source="redis://localhost",
            queue="tasks",
        ),
        concurrency=5,   # Process up to 5 messages concurrently
    )
```

Supported backends: Redis (via `redis://`), AMQP/RabbitMQ (via `amqp://`), and any backend that implements `syrin.watch.QueueBackend`.

## TriggerEvent

Every trigger—regardless of protocol—delivers a `TriggerEvent` to the agent. The dataclass has four fields:

| Field | Type | Description |
|---|---|---|
| `input` | `str` | The text payload to send to the agent as its user message. |
| `source` | `str` | The origin of the trigger (`"webhook"`, `"cron"`, `"queue"`, or a custom label). |
| `metadata` | `dict[str, str]` | Arbitrary key/value pairs from the protocol (headers, queue attributes, etc.). |
| `trigger_id` | `str` | A unique ID for this trigger event. Auto-generated if not set. |

```python
from syrin.watch import TriggerEvent

event = TriggerEvent(
    input="Analyze the attached report",
    source="queue",
    metadata={"priority": "high", "tenant": "acme"},
    trigger_id="evt-001",
)
```

## Manual Triggering with agent.trigger()

`agent.trigger()` fires the agent programmatically from your own code without starting a persistent listener. This is useful for testing, scripted workflows, or integrating watch-style event handling into an existing control loop.

```python
from syrin import Agent, Model
from syrin.watch import TriggerEvent

agent = Agent(model=Model.Anthropic("claude-sonnet-4-6"))

response = await agent.trigger(
    TriggerEvent(input="Hello", source="test")
)
print(response.content)
```

`agent.trigger()` returns the same `AgentResponse` object as `agent.run()`, including `response.cost`, `response.total_tokens`, and any structured output.

## BYO-Framework Integration with agent.watch_handler()

When your application already runs its own HTTP server, message loop, or task scheduler, use `agent.watch_handler()` to get a plain async callable. You control dispatch; syrin handles the agent lifecycle.

```python
from fastapi import FastAPI, Request
from syrin import Agent, Model
from syrin.watch import TriggerEvent

app = FastAPI()
agent = Agent(model=Model.Anthropic("claude-sonnet-4-6"))

handler = agent.watch_handler()

@app.post("/webhook")
async def webhook(request: Request) -> dict:
    body = await request.body()
    event = TriggerEvent(
        input=body.decode(),
        source="fastapi",
        metadata=dict(request.headers),
    )
    response = await handler(event)
    return {"result": response.content}
```

`watch_handler()` accepts an optional `on_trigger` callback, the same as `watch()`, and respects all agent-level settings: budget limits, guardrails, hooks, and memory.

## Concurrency and Backpressure

The `concurrency` parameter on `agent.watch()` sets the maximum number of triggers processed simultaneously. When the limit is reached, new triggers are queued in memory up to `queue_size` (default: 100). Triggers that exceed the queue limit are dropped and a `Hook.TRIGGER_DROPPED` event is emitted.

```python
await agent.watch(
    protocol=QueueProtocol(source="redis://localhost", queue="tasks"),
    concurrency=10,
    queue_size=500,
)
```

## Stopping a Watcher

`agent.watch()` returns an `asyncio.Task`. Cancel it to stop the listener cleanly:

```python
import asyncio
from syrin import Agent, Model
from syrin.watch import CronProtocol

agent = Agent(model=Model.Anthropic("claude-sonnet-4-6"))

watcher = asyncio.create_task(
    agent.watch(
        protocol=CronProtocol(schedule="* * * * *", input="Ping"),
    )
)

# Later...
watcher.cancel()
```

## Complete Example

```python
import asyncio
from syrin import Agent, Model
from syrin.watch import CronProtocol, QueueProtocol, WebhookProtocol, TriggerEvent

agent = Agent(model=Model.Anthropic("claude-sonnet-4-6"))

# Webhook: fire when POST /trigger arrives
await agent.watch(
    protocol=WebhookProtocol(path="/trigger", port=8080, secret="my-secret"),
    on_trigger=lambda evt: print(f"Got: {evt.input}"),
)

# Cron: run every hour
await agent.watch(
    protocol=CronProtocol(schedule="0 * * * *", input="Generate hourly report"),
)

# Queue: consume from Redis queue
await agent.watch(
    protocol=QueueProtocol(source="redis://localhost", queue="tasks"),
    concurrency=5,
)

# Manual trigger
await agent.trigger(TriggerEvent(input="Hello", source="test"))

# BYO-framework handler (FastAPI example)
handler = agent.watch_handler()
# app.post("/webhook")(lambda req: handler(TriggerEvent(input=req.body, source="fastapi")))
```

## See Also

- [Running Agents](/agent-kit/agent/running-agents) - Standard `agent.run()` and `agent.stream()`
- [Hooks & Events](/agent-kit/debugging/hooks) - Subscribe to `Hook.TRIGGER_DROPPED` and other lifecycle events
- [Budget Management](/agent-kit/core/budget) - Enforce cost limits across long-running watchers
- [Serving](/agent-kit/production/serving) - HTTP serving with built-in REST endpoints
