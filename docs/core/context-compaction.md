---
title: Context Compaction
description: Strategies for reducing context size when it gets too full
weight: 31
---

## Why Compaction Exists

You have 80,000 tokens of context space. Your conversation just hit 81,000.

**What do you do?**

- ❌ Refuse to add more messages (breaks the conversation)
- ❌ Kick out the oldest messages (loses important context)
- ❌ Stop everything (frustrates the user)

**The answer: Compaction.**

Compaction intelligently reduces context size while preserving what matters most. It's like summarizing a 10-page document into 1 page—keeping the important parts.

---

## The Compaction Problem

### What Gets Compacted?

Your context has multiple parts:

1. **System Prompt** (fixed) — Never removed
2. **Memory** (important) — Keep high-priority memories
3. **Older Messages** (can be summarized) — May be compacted
4. **Recent Messages** (important) — Keep recent context
5. **Current Message** (the question) — Never removed

### The Challenge

- **What to keep?** Recent messages matter more than old ones
- **What to summarize?** Long conversations have important patterns
- **How to not lose meaning?** Summarization must preserve key facts

**Syrin handles this automatically.**

---

## Compaction Strategies

### 1. Middle-Out Truncation

Keeps the **beginning** (system, early context) and **end** (recent messages) of the conversation, removing the middle.

```
Before:
[System] → [Old msg] → [Old msg] → [Old msg] → [Recent] → [Recent] → [Current]

After (Middle-Out):
[System] → [Summary: 3 old messages were about X] → [Recent] → [Recent] → [Current]
```

**Best for:** When you're slightly over budget (< 1.5x over).

---

### 2. Summarization

Compresses older messages into a summary, keeping key facts.

```
Before:
[System] → [User asked about Python] → [Explained Python basics] → 
[Discussed frameworks] → [User asked more] → [Answered]

After (Summarized):
[System] → [Summary: User interested in Python. Covered basics and frameworks. Open questions remain.] → [User asked more] → [Answered]
```

**Best for:** When you're heavily over budget (≥ 1.5x over).

---

## How Compaction Works in Syrin

### Automatic Compaction

Set a threshold and compaction runs automatically:

```python
from syrin import Context
from syrin.threshold import ContextThreshold, compact_if_available

context = Context(
    max_tokens=80000,
    thresholds=[
        ContextThreshold(at=75, action=compact_if_available),
    ],
)
```

**The flow:**
```
1. Agent receives message
2. Context builds message list
3. Token count calculated
4. Utilization checked: 78% (> 75%)
5. Threshold triggers compact_if_available
6. Compaction runs → context shrinks
7. Agent continues with compacted context
```

---

### Manual Compaction

Trigger compaction manually:

```python
# From a threshold action
ContextThreshold(at=75, action=lambda ctx: ctx.compact())

# Or from the agent
agent.context.compact()
```

**Note:** `compact()` only works during prepare (e.g., from a threshold action).

---

## Compaction Methods

### CompactionMethod Enum

Syrin uses these methods automatically:

| Method | When | What It Does |
|--------|------|--------------|
| `none` | Context fits | No compaction needed |
| `middle_out_truncate` | < 1.5x over budget | Keep start/end, drop middle |
| `summarize` | ≥ 1.5x over budget | Summarize older messages |

**Syrin automatically chooses the best method.**

---

## Proactive vs Reactive Compaction

### Reactive (Threshold-Based)

Compacts when you hit a threshold.

```python
context = Context(
    max_tokens=80000,
    thresholds=[
        ContextThreshold(at=75, action=compact_if_available),
    ],
)
```

**Pros:**
- Simple to set up
- Only compacts when needed

**Cons:**
- Might compact multiple times in a long session

---

### Proactive (auto_compact_at)

Compacts early to prevent context rot.

```python
context = Context(
    max_tokens=80000,
    auto_compact_at=0.6,  # Compact at 60%
)
```

**Pros:**
- Keeps context "fresh"
- Prevents quality degradation
- No threshold setup needed

**Cons:**
- May compact more often

**Which to use?** Research suggests keeping utilization under 60-70% maintains better conversation quality. Use `auto_compact_at=0.6` for proactive management.

---

## Compaction with Summarization

### Custom Summarization Model

Use a specific model for summarization:

```python
from syrin import Context, Model

context = Context(
    max_tokens=80000,
    compaction_model=Model.OpenAI("gpt-4o-mini", api_key="your-key"),
    compaction_system_prompt="You are a concise summarizer. Keep key facts.",
    compaction_prompt="Summarize this conversation: {messages}",
)
```

### Without LLM (Placeholder)

When no model is specified, Syrin uses a placeholder:

- Keeps system prompt
- Keeps last 4 messages
- Adds a one-line summary

```python
context = Context(
    max_tokens=80000,
    # No compaction_model = placeholder summarization
)
```

---

## Custom Compactors

Create your own compaction strategy:

```python
from syrin.context import Compactor, CompactionResult

class MyCompactor(Compactor):
    def compact(self, messages: list[dict], budget: int) -> CompactionResult:
        # Your logic here
        compacted_messages = ...  # Reduce messages to fit budget
        
        return CompactionResult(
            messages=compacted_messages,
            method="my_custom_method",
            tokens_before=len(messages),
            tokens_after=len(compacted_messages),
        )

context = Context(
    max_tokens=80000,
    compactor=MyCompactor(),
)
```

---

## Configuration Reference

| Field | What It Does | Example |
|-------|--------------|---------|
| `compactor` | Custom compaction logic | `MyCompactor()` |
| `compaction_model` | Model for summarization | `Model.OpenAI("gpt-4o-mini")` |
| `compaction_prompt` | User template for summarization | `"Summarize: {messages}"` |
| `compaction_system_prompt` | System prompt for summarizer | `"Be concise."` |
| `auto_compact_at` | Proactive compaction threshold | `0.6` (60%) |

---

## Compaction Events

Subscribe to compaction events:

```python
# When compaction runs
agent.events.on("context.compact", lambda e: print(
    f"Compacted using {e['method']}: "
    f"{e['tokens_before']} → {e['tokens_after']} tokens"
))

# When thresholds trigger
agent.events.on("context.threshold", lambda e: print(
    f"Threshold at {e['percent']}%"
))
```

---

## Example: Full Compaction Setup

```python
from syrin import Agent, Context, Model
from syrin.threshold import ContextThreshold, compact_if_available

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    context=Context(
        max_tokens=80000,
        reserve=2000,
        thresholds=[
            # Warn at 50%
            ContextThreshold(
                at=50,
                action=lambda ctx: print(f"Getting full: {ctx.percentage}%")
            ),
            # Compact at 75%
            ContextThreshold(
                at=75,
                action=compact_if_available,
            ),
            # Stop at 100%
            ContextThreshold(
                at=100,
                action=lambda ctx: raise ValueError("Context full!")
            ),
        ],
        # Proactive compaction at 60%
        auto_compact_at=0.6,
    ),
)

# Subscribe to events
agent.events.on("context.compact", lambda e: print(f"Compacted: {e['method']}"))

# Use normally
result = agent.run("Let's continue our conversation...")

# Check stats
print(f"Tokens: {agent.context_stats.total_tokens}")
print(f"Compacted: {agent.context_stats.compacted}")
print(f"Method: {agent.context_stats.compact_method}")
```

---

## Best Practices

### 1. Set Reserve Appropriately

```python
# Short responses expected
context = Context(max_tokens=80000, reserve=1000)

# Long/verbose responses
context = Context(max_tokens=80000, reserve=4000)
```

### 2. Use Proactive Compaction

```python
# Keep context fresh
context = Context(
    max_tokens=80000,
    auto_compact_at=0.6,  # Compact at 60%
)
```

### 3. Monitor Context Rot Risk

```python
snapshot = agent.context.snapshot()
print(f"Rot risk: {snapshot.context_rot_risk}")
# low: < 60%, medium: 60-70%, high: > 70%
```

### 4. Set Reasonable Limits

```python
# Don't let context grow unbounded
context = Context(
    max_tokens=80000,
    thresholds=[
        ContextThreshold(at=80, action=compact_if_available),
    ],
)
```

---

## Troubleshooting

### Compaction Not Running

**Check:** Is `compact_if_available` or `ctx.compact()` in your threshold action?

```python
# Wrong: no compaction
ContextThreshold(at=75, action=lambda ctx: print("75%"))

# Correct: compaction
ContextThreshold(at=75, action=compact_if_available)
```

### Compact Only During Prepare

**Note:** `ctx.compact()` only works during prepare (from threshold actions).

```python
# This won't work (outside prepare)
agent.context.compact()  # No-op!

# This works (inside threshold)
ContextThreshold(at=75, action=lambda ctx: ctx.compact())
```

### Tools Consuming Budget

If tools are large, there may be no room for message compaction.

```python
# Many large tools → limited message space
context = Context(
    max_tokens=4000,
    thresholds=[
        ContextThreshold(at=100, action=lambda ctx: raise ValueError("Can't compact with large tools!")),
    ],
)
```

**Solution:** Use fewer/smaller tools or increase `max_tokens`.

---

## What's Next?

- [Context Overview](/agent-kit/core/context) - Back to context basics
- [Memory](/agent-kit/core/memory) - How memory integrates
- [Budget](/agent-kit/core/budget) - Cost control

## See Also

- [Agents](/agent-kit/agent/overview) - Building agents
- [Prompts](/agent-kit/core/prompts) - Writing effective prompts
