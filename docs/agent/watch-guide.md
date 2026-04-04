---
title: Event-Driven Triggers (agent.watch())
description: Turn any agent into an event-driven worker using built-in webhook, cron, and queue protocols or your own framework integration.
weight: 145
---

# Event-Driven Triggers (agent.watch())

## Overview

`agent.watch()` turns an agent into a persistent, event-driven worker. Instead of calling `agent.run()` manually each time, the agent subscribes to an event source and processes incoming triggers automatically. Each trigger produces a full `AgentResponse` just like a direct `run()` call, including cost tracking, hooks, and structured output.

Three built-in protocols ship with syrin: `WebhookProtocol` (HTTP), `CronProtocol` (scheduled), and `QueueProtocol` (message queue). For frameworks that already own the server layer—FastAPI, Starlette, Django Channels—`agent.watch_handler()` returns a plain callable that you wire in yourself.

## Start Here

Use the existing example set as the practical entry point:

- `examples/22_watch/cron_trigger.py` for scheduled execution
- `examples/22_watch/webhook_trigger.py` for inbound HTTP triggers
- `examples/22_watch/queue_trigger.py` for queue consumers
- `examples/22_watch/pipeline_watch.py` for event-driven pipelines
- `examples/22_watch/multi_protocol.py` for combining trigger sources

The mental model is simple:

1. A protocol receives or creates an event.
2. It turns that into a `TriggerEvent`.
3. Syrin runs the agent using that trigger as input.
4. You optionally observe `on_trigger`, `on_result`, `on_error`, and hook events around that lifecycle.

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

This exact flow is demonstrated in `examples/22_watch/webhook_trigger.py`.

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

This flow is demonstrated in `examples/22_watch/cron_trigger.py`.

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

This flow is demonstrated in `examples/22_watch/queue_trigger.py`.

## TriggerEvent

Every trigger—regardless of protocol—delivers a `TriggerEvent` to the agent. The dataclass has four fields. `input` is a `str` containing the text payload sent to the agent as its user message. `source` is a `str` identifying the origin of the trigger (for example `"webhook"`, `"cron"`, `"queue"`, or a custom label). `metadata` is a `dict[str, str]` holding arbitrary key/value pairs from the protocol such as headers or queue attributes. `trigger_id` is a `str` providing a unique ID for the trigger event, auto-generated if not explicitly set.

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

Use `agent.trigger()` when you want watch semantics in tests or from your own scheduler without starting a long-running listener.

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

This is the preferred integration style when FastAPI, Starlette, or another framework already owns the HTTP server.

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

For graceful shutdown in real services:

1. keep a reference to the task returned by `agent.watch()`
2. stop the underlying protocol if it exposes shutdown hooks
3. cancel the task during application shutdown

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

## Which Watch Pattern Should You Use?

The right pattern depends on what triggers the agent. Use `CronProtocol` when you need to run a report or task on a fixed schedule such as every hour. Use `WebhookProtocol` when the agent should respond to inbound HTTP calls from external systems. Use `QueueProtocol` when consuming jobs from a message queue like Redis or RabbitMQ. Use `watch_handler()` when your application already runs its own web framework such as FastAPI and you want to wire the agent into an existing server. Use `agent.trigger()` when you want to fire the same watch-style logic from your own code or tests without starting a persistent listener. Use the `multi_protocol.py` example as a starting point when you need to coordinate multiple trigger sources simultaneously.

## Protocol Interfaces

The watch package also exports `WatchProtocol` and `Watchable` for framework authors who want to plug custom trigger sources or reusable watch-capable components into the same event-driven runtime.

## See Also

- [Running Agents](/agent-kit/agent/running-agents) - Standard `agent.run()` and `agent.stream()`
- [Hooks & Events](/agent-kit/debugging/hooks) - Subscribe to `Hook.TRIGGER_DROPPED` and other lifecycle events
- [Budget Management](/agent-kit/core/budget) - Enforce cost limits across long-running watchers
- [Serving](/agent-kit/production/serving) - HTTP serving with built-in REST endpoints
