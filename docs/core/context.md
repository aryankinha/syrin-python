---
title: Context
description: Manage the token context window — limits, compaction, and utilization tracking
weight: 30
---

## The Problem You Will Eventually Hit

You build an agent. It works great for the first few turns. Then someone has a long conversation with it, and suddenly it errors out or starts giving weird answers. You look at the logs. Context window exceeded.

Every AI model has a limit on how much text it can hold in memory at once. The system prompt takes tokens. Each message in the conversation takes tokens. Tools take tokens. Once you fill the window, the model either crashes or starts dropping older messages without telling you.

This is the context problem, and it hits everyone eventually. Syrin's `Context` class gives you visibility and control over it.

## What Goes Into Context

Before each LLM call, Syrin assembles the context — everything the model will see:

- The system prompt
- Tool definitions (TOON or JSON schemas)
- Memories recalled for this turn
- The conversation history
- The current user message
- Any injected data (from RAG, etc.)

All of these compete for the same limited space. A 128k token context window sounds huge until you realize your system prompt is 2k tokens, you have 10 tools at 500 tokens each, you've been chatting for 200 turns, and now you're at 125k tokens with no room for a response.

## Basic Setup

```python
from syrin import Agent, Model, Context

class LongConversationAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")
    # Use Model.mock() above for testing without an API key
    system_prompt = "You are a helpful assistant."
    context = Context(max_tokens=80000)  # Leave room for responses

agent = LongConversationAgent()
response = agent.run("Hello!")

# Check how much context was used
stats = agent.context_stats
print(f"Tokens used: {stats.total_tokens}")
print(f"Max tokens: {stats.max_tokens}")
print(f"Utilization: {stats.utilization:.1%}")
```

Output:

```
Tokens used: 14
Max tokens: 80000
Utilization: 0.0%
```

## ContextStats

After any `run()`, inspect `agent.context_stats` to see what happened:

```python
from syrin import Agent, Model, Context

class MyAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")
    # Use Model.mock() above for testing without an API key
    system_prompt = "You are helpful."
    context = Context(max_tokens=80000)

agent = MyAgent()
agent.run("Hello!")

stats = agent.context_stats
print(f"total_tokens: {stats.total_tokens}")
print(f"max_tokens: {stats.max_tokens}")
print(f"utilization: {stats.utilization:.4f}")
print(f"compacted: {stats.compacted}")
print(f"compact_count: {stats.compact_count}")
print(f"thresholds_triggered: {stats.thresholds_triggered}")

breakdown = stats.breakdown
print(f"\nBreakdown:")
print(f"  system_tokens: {breakdown.system_tokens}")
print(f"  tools_tokens: {breakdown.tools_tokens}")
print(f"  memory_tokens: {breakdown.memory_tokens}")
print(f"  messages_tokens: {breakdown.messages_tokens}")
print(f"  injected_tokens: {breakdown.injected_tokens}")
```

Output:

```
total_tokens: 14
max_tokens: 80000
utilization: 0.0002
compacted: False
compact_count: 0
thresholds_triggered: []

Breakdown:
  system_tokens: 8
  tools_tokens: 0
  memory_tokens: 0
  messages_tokens: 6
  injected_tokens: 0
```

`utilization` is a float from 0.0 to 1.0 (0.75 means 75% of max_tokens is in use). The `breakdown` shows you exactly where the tokens came from, so you know what's eating your context budget.

## Automatic Compaction

The most common request: "compact the context automatically when it gets full."

Use `auto_compact_at` to set a fraction at which compaction kicks in automatically:

```python
from syrin import Agent, Model, Context

class AutoCompactAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")
    # Use Model.mock() above for testing without an API key
    system_prompt = "You are a long-conversation assistant."
    context = Context(
        max_tokens=80000,
        auto_compact_at=0.75,  # Compact when 75% full
    )

agent = AutoCompactAgent()
response = agent.run("Start a long conversation with me.")
print(response.content[:50])
```

When utilization hits 75%, Syrin summarizes the older conversation into a compact representation before the next LLM call. The conversation continues without hitting the wall.

## Thresholds: React at Specific Levels

For more control, register callback functions that fire when utilization crosses a threshold:

```python
from syrin import Agent, Model, Context
from syrin.threshold import ContextThreshold

events_log = []

class MonitoredAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")
    # Use Model.mock() above for testing without an API key
    system_prompt = "You are helpful."
    context = Context(
        max_tokens=80000,
        thresholds=[
            ContextThreshold(
                at=50,
                action=lambda ctx: events_log.append(f"50% hit")
            ),
            ContextThreshold(
                at=75,
                action=lambda ctx: events_log.append(f"75% hit — compacting!")
            ),
        ]
    )

agent = MonitoredAgent()
agent.run("Hello!")
print(f"Events triggered: {events_log}")
```

With a real conversation long enough to hit those thresholds, the callbacks fire automatically. With the mock model and a short message, they won't fire (utilization stays near 0%).

The `action` callback receives a context object with `.percentage` and other state. You can log, alert, or trigger compaction programmatically.

## Key Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_tokens` | `int` or `None` | Model's window | Maximum tokens in the context window. Set lower to control costs or enforce a tighter window. |
| `reserve` | `int` | `2000` | Tokens reserved for the model's response. Effective input space is `max_tokens - reserve`. Increase if your responses are often long. |
| `auto_compact_at` | `float` or `None` | `None` | Fraction (0.0–1.0) at which to compact automatically before the next LLM call. `0.75` means "compact at 75%". |
| `thresholds` | `list[ContextThreshold]` | `[]` | Callbacks that fire when utilization crosses a percentage mark. Each `ContextThreshold(at=int, action=callable)` fires the first time its `at` value (0–100) is crossed. |
| `context_mode` | `ContextMode` | `FULL` | `FULL` includes all history. `FOCUSED` keeps only the last N turns (controlled by `focused_keep`). |
| `formation_mode` | `FormationMode` | `PUSH` | `PUSH` includes all recent history. `PULL` retrieves only semantically relevant segments. |

## Context Modes

For very long conversations where old turns are irrelevant, switch to FOCUSED mode:

```python
from syrin import Agent, Model, Context
from syrin.enums import ContextMode

class FocusedAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")
    # Use Model.mock() above for testing without an API key
    system_prompt = "You are helpful."
    context = Context(
        max_tokens=80000,
        context_mode=ContextMode.FOCUSED,
        focused_keep=10,  # Keep the last 10 turns only
    )

agent = FocusedAgent()
response = agent.run("Hello!")
print(response.content[:50])
```

FULL mode is correct for most use cases. Switch to FOCUSED when you have multi-turn conversations that go on for hundreds of messages and old context stops being useful.

## What's Next

- [Context Compaction](/agent-kit/core/context-compaction) — Deep dive on compaction strategies and customization
- [Memory](/agent-kit/core/memory) — How memories integrate with context
- [Budget](/agent-kit/core/budget) — Spending limits (separate from token limits)
