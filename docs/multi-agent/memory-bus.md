---
title: MemoryBus
description: A shared memory whiteboard for cross-agent knowledge sharing in swarms
weight: 121
---

## The Problem A2A Can't Solve

A2A messaging is point-to-point: one agent sends a message to another agent. But what if you want to share a research finding with *any* agent that cares about it, including ones that haven't been spawned yet?

`MemoryBus` is a shared whiteboard. Agents publish memory entries to it. Other agents read from it by querying for relevant content. It's not "send this to Bob" — it's "put this on the board and let whoever needs it pick it up."

## Basic Usage

```python
import asyncio
from syrin.swarm._memory_bus import MemoryBus
from syrin.memory.config import MemoryEntry
from syrin.enums import MemoryType
from datetime import datetime

async def main():
    bus = MemoryBus(allow_types=[MemoryType.SEMANTIC])

    # Researcher agent publishes a finding
    entry = MemoryEntry(
        id="mem-001",
        content="AI safety research: 73% of models show alignment drift under distribution shift",
        type=MemoryType.SEMANTIC,
        importance=0.9,
        keywords=["safety", "alignment"],
        created_at=datetime.now(),
    )

    stored = await bus.publish(entry, agent_id="researcher")
    print(f"Published: {stored}")  # True

    # Writer agent queries for relevant content
    results = await bus.read(query="safety", agent_id="writer")
    print(f"Found: {len(results)} entries")
    print(f"Content: {results[0].content[:50]}")

asyncio.run(main())
```

Output:

```
Published: True
Found: 1 entries
Content: AI safety research: 73% of models show alignment d
```

## MemoryEntry Fields

Each entry on the bus is a `MemoryEntry` with:

- `id` — unique identifier for this memory
- `content` — the text content of the memory
- `type` — `MemoryType.CORE`, `EPISODIC`, `SEMANTIC`, or `PROCEDURAL`
- `importance` — float from 0.0 to 1.0 (higher = more important)
- `keywords` — list of strings for filtering and search
- `created_at` — when this memory was created
- `valid_until` — optional expiry time
- `metadata` — arbitrary additional data

## Filtering What Goes on the Bus

### By Memory Type

Restrict which memory types are allowed:

```python
# Only semantic memories (facts and knowledge) allowed
bus = MemoryBus(allow_types=[MemoryType.SEMANTIC])

# Multiple types
bus = MemoryBus(allow_types=[MemoryType.SEMANTIC, MemoryType.PROCEDURAL])

# No restriction — all types accepted
bus = MemoryBus()
```

Entries that fail the type filter are silently rejected. `publish()` returns `False` and `Hook.MEMORY_BUS_FILTERED` fires.

### Custom Predicate

Use a `filter` function for fine-grained control:

```python
# Only publish entries marked as non-private
bus = MemoryBus(filter=lambda entry: "private" not in entry.keywords)

# Only high-importance entries
bus = MemoryBus(filter=lambda entry: entry.importance >= 0.7)
```

Type filtering and custom filtering are applied together. Both must pass for an entry to be published.

## Time-to-Live

Set a default expiry for all entries on the bus:

```python
bus = MemoryBus(ttl=3600)  # All entries expire after 1 hour
```

Expired entries are automatically excluded from `read()` results and fire `Hook.MEMORY_BUS_EXPIRED`.

Individual entries can also have their own expiry via `valid_until`:

```python
from datetime import datetime, timedelta

entry = MemoryEntry(
    id="breaking-news",
    content="System is under maintenance",
    type=MemoryType.CORE,
    importance=1.0,
    keywords=["maintenance"],
    created_at=datetime.now(),
    valid_until=datetime.now() + timedelta(hours=2),  # Expires in 2 hours
)
```

## Using the Bus in a Swarm

In a real multi-agent system, you create one `MemoryBus` and share it between agents. Agents publish findings, and others read them:

```python
import asyncio
from syrin import Agent, Model
from syrin.swarm._memory_bus import MemoryBus
from syrin.memory.config import MemoryEntry
from syrin.enums import MemoryType
from datetime import datetime

bus = MemoryBus(allow_types=[MemoryType.SEMANTIC])

async def researcher_task():
    # Simulate a researcher agent finding something
    finding = MemoryEntry(
        id="finding-1",
        content="Large language models perform better with chain-of-thought prompting",
        type=MemoryType.SEMANTIC,
        importance=0.85,
        keywords=["LLM", "prompting", "chain-of-thought"],
        created_at=datetime.now(),
    )
    published = await bus.publish(finding, agent_id="researcher")
    print(f"Researcher published: {published}")

async def writer_task():
    # Simulate a writer agent looking for relevant content
    relevant = await bus.read(query="prompting strategies", agent_id="writer")
    print(f"Writer found {len(relevant)} relevant entries")
    for entry in relevant:
        print(f"  - {entry.content[:60]}")

async def main():
    await researcher_task()
    await writer_task()

asyncio.run(main())
```

Output:

```
Researcher published: True
Writer found 1 relevant entries
  - Large language models perform better with chain-of-thought pr
```

## Hooks

MemoryBus fires hooks you can subscribe to for observability:

- `Hook.MEMORY_BUS_PUBLISHED` — entry was accepted and stored
- `Hook.MEMORY_BUS_READ` — an agent read from the bus
- `Hook.MEMORY_BUS_FILTERED` — entry was rejected by the filter
- `Hook.MEMORY_BUS_EXPIRED` — entry expired and was removed

## A2A vs. MemoryBus

These two primitives solve different problems:

**A2A** is for explicit, targeted communication. You know who you're talking to. "Worker, here is your task assignment." It's like sending an email.

**MemoryBus** is for shared knowledge that any agent can discover. You don't know who will read it. "Here's a research finding — anyone who needs it, take it." It's like a bulletin board.

Use A2A for coordination and commands. Use MemoryBus for knowledge sharing and context propagation across the swarm.

## What's Next

- [A2A Messaging](/agent-kit/multi-agent/a2a) — Direct, typed agent-to-agent messages
- [Swarm](/agent-kit/multi-agent/swarm) — High-level multi-agent topologies
- [Memory](/agent-kit/core/memory) — Single-agent persistent memory
