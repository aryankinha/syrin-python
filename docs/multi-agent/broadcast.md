---
title: Broadcast (Pub-Sub)
description: Topic-based publish-subscribe messaging for in-swarm agent communication — broadcast(), subscribe(), wildcard patterns, and BroadcastConfig
weight: 75
---

## Broadcast vs A2A

`BroadcastBus` and `A2ARouter` are both ways for agents to communicate, but they work differently.

A2A is point-to-point: you name the recipient. One sender, one receiver. Broadcast is pub-sub: you publish to a topic. One sender, any number of receivers. If ten agents have subscribed to `"research.*"`, all ten receive the message when you broadcast to `"research.complete"`.

Use broadcast when you want to notify all interested agents at once without knowing who they are. Use A2A when you're sending a typed message to a specific agent.

## Quickstart

```python
import asyncio
from syrin import Agent, Model
from syrin.response import Response
from syrin.swarm import Swarm
from syrin.swarm._broadcast import BroadcastBus, BroadcastConfig, BroadcastEvent

bus = BroadcastBus(config=BroadcastConfig(max_payload_bytes=4096))

class ResearchAgent(Agent):
    model = Model.mock()
    system_prompt = "Research the topic and broadcast findings."

    async def arun(self, input_text: str) -> Response[str]:
        findings = f"Findings on {input_text}: significant growth observed"
        await bus.broadcast(
            sender_id="research",
            topic="research.complete",
            payload={"summary": findings, "confidence": 0.9},
        )
        return Response(content=findings, cost=0.01)

class WriterAgent(Agent):
    model = Model.mock()
    system_prompt = "Write a report based on research findings."

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        bus.subscribe("writer", "research.*", self._on_research_event)

    def _on_research_event(self, event: BroadcastEvent) -> None:
        print(f"Writer received: topic={event.topic}, from={event.sender_id}")
        print(f"  payload={event.payload}")

    async def arun(self, input_text: str) -> Response[str]:
        return Response(content="Report based on findings", cost=0.01)

async def main():
    swarm = Swarm(
        agents=[ResearchAgent(), WriterAgent()],
        goal="Research AI trends and write a report",
    )
    result = await swarm.run()
    print(result.content)

asyncio.run(main())
```

## Publishing

```python
count = await bus.broadcast(
    sender_id="research-agent",
    topic="research.complete",
    payload={"summary": "...", "sources": ["arxiv.org/..."]},
)
print(f"Delivered to {count} subscribers")
```

`broadcast()` returns the number of subscribers that received the message. It raises `BroadcastPayloadTooLarge` if `max_payload_bytes` is set and the serialised payload exceeds it.

## Subscribing

```python
def on_research(event: BroadcastEvent) -> None:
    print(event.sender_id, event.topic, event.payload)

bus.subscribe("writer-agent", "research.*", on_research)
```

`agent_id` identifies the subscriber in observability hooks. `topic` is an exact string or glob pattern. `handler` is a callable invoked synchronously with a `BroadcastEvent` when a matching message arrives.

Subscribe before any matching broadcast is sent — subscriptions are permanent for the lifetime of the bus.

## Wildcard Patterns

Topics use `fnmatch` glob patterns. The most common patterns:

`"research.complete"` — matches exactly `"research.complete"`. Nothing else.

`"research.*"` — matches `"research.complete"`, `"research.error"`, `"research.retry"`, and any other `research.X`. Does not match `"analysis.complete"`.

`"*.complete"` — matches `"research.complete"`, `"analysis.complete"`, and any other `X.complete`.

`"*"` — matches every topic. Use this for monitors that need to see all messages.

`"research.?"` — matches topics where the second part is exactly one character. Matches `"research.a"` but not `"research.complete"`.

## BroadcastEvent Fields

Every handler receives a `BroadcastEvent` with three fields:

`sender_id` — The agent ID that sent the broadcast.

`topic` — The exact topic string the message was published on.

`payload` — The arbitrary dict payload from the sender.

## Configuration

```python
from syrin.swarm._broadcast import BroadcastBus, BroadcastConfig

bus = BroadcastBus(config=BroadcastConfig(
    max_payload_bytes=1024,    # 0 = unlimited (default)
    max_pending_per_agent=50,  # 0 = unlimited (default)
))
```

`max_payload_bytes` — Maximum serialised payload size. Raises `BroadcastPayloadTooLarge` on violation. Default is 0 (unlimited).

`max_pending_per_agent` — Maximum queued messages per subscriber. When the queue overflows, the oldest message is dropped (FIFO). Default is 0 (unlimited).

## Delivery Guarantees

Each handler is invoked exactly once per matching message (at-most-once delivery). Broadcast is in-memory only — messages don't persist across process restarts. Handlers are called synchronously inside `broadcast()`, so keep them fast. For heavy work inside a handler, spawn a background task. There's no ordering guarantee across different topics, but within a single `broadcast()` call, handlers are invoked in subscription registration order.

## Research → Writer Pipeline Example

```python
import asyncio
from syrin import Agent, Model
from syrin.response import Response
from syrin.swarm._broadcast import BroadcastBus, BroadcastEvent

shared_bus = BroadcastBus()

class ResearchAgent(Agent):
    model = Model.mock()

    async def arun(self, topic: str) -> Response[str]:
        summary = f"Research complete for: {topic}"
        await shared_bus.broadcast(
            sender_id="ResearchAgent",
            topic="research.complete",
            payload={"topic": topic, "summary": summary},
        )
        return Response(content=summary, cost=0.02)

class WriterAgent(Agent):
    model = Model.mock()
    _received: list[BroadcastEvent] = []

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        shared_bus.subscribe("WriterAgent", "research.*", self._received.append)

    async def arun(self, _: str) -> Response[str]:
        context = "\n".join(str(e.payload) for e in self._received)
        return Response(content=f"Report based on:\n{context}", cost=0.01)
```

## Hook

`Hook.AGENT_BROADCAST` fires after every successful `broadcast()` call. Hook context includes `sender_id`, `topic`, `payload_size`, and `subscriber_count`.

## See Also

- [Swarm](/multi-agent/swarm) — Parallel, consensus, and reflection topologies
- [A2A Messaging](/multi-agent/a2a) — Direct typed agent-to-agent messages
- [MonitorLoop](/multi-agent/monitor-loop) — Async supervisor loop
