---
title: Context
description: Manage token limits and optimize context window usage
weight: 30
---

## The Invisible Problem: Your Agent is Drowning

Imagine trying to read a book where the text keeps getting longer—but the page size stays the same. Eventually, you can't fit any more words.

**That's the context window problem.**

AI models have a limited "brain space" for each conversation. Once it's full, you can't add more. The model forgets, gets confused, or just stops working.

---

## What Is Context?

Context is everything the AI considers when answering your question:

| Component | What It Is | Example |
|-----------|-----------|---------|
| **System prompt** | The instructions | "You are a helpful assistant." |
| **Memory** | What the agent remembers | "User's name is Alice" |
| **Conversation history** | Past messages | "User: Hi\nAssistant: Hello" |
| **Current message** | What you're asking now | "What's the weather?" |
| **Tools** | Available functions | calculator, search, etc. |

**All of this competes for the same limited space.**

---

## The Problem: Context Overflow

Here's what happens in a long conversation:

```
Turn 1:  "Hello"                          → 10 tokens
Turn 2:  "How are you?"                   → 15 tokens
Turn 10: "Remember my name?"               → 50 tokens
Turn 50: (long conversation)                → 10,000 tokens
Turn 100: (even longer)                     → 50,000 tokens
Turn 200: "Answer this question"           → ???

Total: 128,000+ tokens  ←  CONTEXT WINDOW FULL!
```

**The model can't accept more input.** Your conversation is stuck.

---

## The Solution: Context Management

Syrin's context system gives you **control** over this chaos:

1. **Set limits** — Define your max context size
2. **Track usage** — Know exactly how many tokens you're using
3. **Automate compaction** — When context gets too full, compact it automatically
4. **Inject context** — Add RAG results or dynamic data at prepare time

---

## Quick Example

```python
from syrin import Agent, Context, Model
from syrin.threshold import ContextThreshold

# Create agent with context limits
agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    context=Context(
        max_tokens=80000,  # Leave room for response
        reserve=2000,       # Reserve 2000 tokens for the reply
    ),
)

# After many conversations...
result = agent.run("Answer this")

# Check how full the context was
print(f"Tokens used: {agent.context_stats.total_tokens}")
print(f"Utilization: {agent.context_stats.utilization:.1%}")
```

---

## Why Context Matters

| Without Context | With Context |
|----------------|--------------|
| Conversations hit walls | Conversations flow smoothly |
| No visibility into usage | Full token tracking |
| Manual management | Automatic optimization |
| Unexpected failures | Predictable behavior |

---

## Context Window Basics

### The Math

```
Available Tokens = max_tokens - reserve

Example:
  max_tokens = 80,000
  reserve = 2,000
  Available = 78,000 tokens for input
```

**The reserve ensures the model always has room to respond.**

### Model Context Windows

| Model | Context Window |
|-------|---------------|
| GPT-4o | 128,000 tokens |
| GPT-4o-mini | 128,000 tokens |
| Claude 3.5 | 200,000 tokens |
| Gemini 1.5 | 1,000,000 tokens |

**Syrin uses the model's default if you don't specify.**

---

## Core Context Settings

### max_tokens

The maximum tokens in your context window.

```python
context=Context(
    max_tokens=80000,  # 80k tokens (leaves room for response)
)

# Or let Syrin auto-detect from the model
context=Context(
    max_tokens=None,  # Uses model's default (e.g., 128k for GPT-4o)
)
```

**When to set it:**
- When you want to limit costs
- When the model's window is too large for your needs
- When you need predictable token usage

### reserve

Tokens reserved for the model's response.

```python
context=Context(
    max_tokens=80000,
    reserve=2000,  # Always keep 2000 tokens for the reply
)

# For longer responses, increase reserve
context=Context(
    max_tokens=80000,
    reserve=5000,  # More room for verbose responses
)
```

**Default: 2000 tokens**

---

## Understanding Utilization

**Utilization** = How full your context is (as a percentage).

```python
result = agent.run("Hello!")

# Check utilization after the call
print(f"Used: {agent.context_stats.total_tokens} tokens")
print(f"Window: {agent.context_stats.max_tokens} tokens")
print(f"Fullness: {agent.context_stats.utilization:.1%}")
```

**Output:**
```
Used: 1,234 tokens
Window: 80,000 tokens
Fullness: 1.5%
```

### Utilization Levels

| Level | What It Means | Action |
|-------|---------------|--------|
| 0-50% | Plenty of room | None needed |
| 50-75% | Getting full | Consider compacting soon |
| 75-90% | Almost full | Compact now |
| 90%+ | Critical | Compact or fail |

---

## Thresholds: React Before It Breaks

Thresholds let you **act automatically** when context hits certain levels.

```python
from syrin.threshold import ContextThreshold, compact_if_available

context=Context(
    max_tokens=80000,
    thresholds=[
        # At 50%: just log it
        ContextThreshold(
            at=50,
            action=lambda ctx: print(f"Warning: {ctx.percentage}% full")
        ),
        # At 75%: compact automatically
        ContextThreshold(
            at=75,
            action=compact_if_available,  # Built-in helper
        ),
        # At 100%: stop with error
        ContextThreshold(
            at=100,
            action=lambda ctx: raise ValueError("Context full!"),
        ),
    ],
)
```

### How Thresholds Work

```
Context fills up...
       ↓
At 50%: "Warning: 50% full"
       ↓
More messages added...
       ↓
At 75%: Compact runs automatically!
       ↓
Context is now smaller, utilization drops
       ↓
Conversation continues smoothly
```

---

## Configuration Options

### Quick Setup (Most Use Cases)

```python
from syrin import Context

# Simple: just set max tokens
context = Context(max_tokens=80000)

# With auto-compaction
from syrin.threshold import compact_if_available
context = Context(
    max_tokens=80000,
    auto_compact_at=0.6,  # Compact at 60% utilization
)
```

### Common Configurations

```python
# Low-memory agent (tight limits)
context = Context(
    max_tokens=16000,
    reserve=1000,
)

# High-capacity agent (large conversations)
context = Context(
    max_tokens=128000,
    reserve=4000,
)

# Cost-sensitive (aggressive compaction)
context = Context(
    max_tokens=80000,
    auto_compact_at=0.5,  # Compact early
)
```

---

## Field Reference

All Context configuration options:

| Field | Default | What It Does |
|-------|---------|--------------|
| `max_tokens` | Model default | Maximum context window size |
| `reserve` | 2000 | Tokens reserved for response |
| `thresholds` | [] | Actions at utilization levels |
| `auto_compact_at` | None | Auto-compact at this fraction (0.0-1.0) |
| `token_limits` | None | Caps on total tokens (run/per period) |
| `context_mode` | FULL | How to select history: FULL, FOCUSED |
| `focused_keep` | 10 | Turns to keep in FOCUSED mode |
| `formation_mode` | PUSH | How history feeds context: PUSH, PULL |
| `runtime_inject` | None | Function to inject context at prepare time |
| `inject_placement` | BEFORE_CURRENT_TURN | Where injected context goes |

---

## Context Modes

### FULL (Default)

Uses the entire conversation history.

```python
context = Context(context_mode=ContextMode.FULL)
```

**Best for:** Linear conversations, Q&A, short chats.

### FOCUSED

Keeps only the last N turns, dropping older messages.

```python
from syrin.context import ContextMode

context = Context(
    context_mode=ContextMode.FOCUSED,
    focused_keep=5,  # Keep last 5 exchanges
)
```

**Best for:** Long conversations with topic shifts.

---

## Formation Modes

### PUSH (Default)

All conversation history is pushed into context.

```python
context = Context(formation_mode=FormationMode.PUSH)
```

**Best for:** Short to medium conversations.

### PULL

Only relevant segments are pulled from memory.

```python
from syrin.context import FormationMode

context = Context(
    formation_mode=FormationMode.PULL,
    pull_top_k=10,        # Max segments to retrieve
    pull_threshold=0.3,   # Minimum relevance score
)
```

**Best for:** Long conversations where older turns are less relevant.

---

## Token Limits (Separate from Budget)

**Budget** controls **cost** (USD). **TokenLimits** controls **usage** (tokens).

```python
from syrin import Context, TokenLimits, TokenRateLimit
from syrin.budget import raise_on_exceeded

context = Context(
    max_tokens=80000,
    token_limits=TokenLimits(
        max_tokens=50000,  # Max 50k tokens per request
        rate_limits=TokenRateLimit(hour=200000),  # 200k tokens per hour
        on_exceeded=raise_on_exceeded,
    ),
)
```

**When to use:**
- Rate limiting without cost tracking
- API providers with token quotas
- Enforcing usage patterns

---

## Snapshot: See What Actually Went In

Get a full picture of what the model saw:

```python
result = agent.run("Hello!")
snapshot = agent.context.snapshot()

print(f"Total tokens: {snapshot.total_tokens}")
print(f"Utilization: {snapshot.utilization_pct}%")
print(f"Rot risk: {snapshot.context_rot_risk}")  # low/medium/high

# What's in there?
for msg in snapshot.message_preview:
    print(f"{msg.role}: {msg.content_snippet[:50]}...")

# Why was each thing included?
for reason in snapshot.why_included:
    print(f"  → {reason}")
```

**Output:**
```
Total tokens: 2456
Utilization: 3.1%
Rot risk: low
user: Hello!
assistant: Hi! How can I help you today?
  → current user message
  → conversation history
  → system prompt
```

---

## Proactive Compaction

Set it and forget it—compaction runs automatically.

```python
context = Context(
    max_tokens=80000,
    auto_compact_at=0.6,  # Compact when 60% full
)
```

**When it runs:** Before each LLM call, if utilization ≥ 60%.

**Why 60%?** Research suggests keeping context under 60-70% helps maintain quality.

---

## What's Next?

- [Context Compaction](/core/context-compaction) - Deep dive into compaction strategies
- [Memory](/core/memory) - How memory integrates with context
- [Budget](/core/budget) - Cost control (separate from tokens)

## See Also

- [Agents](/agent/overview) - Building agents with context
- [Prompts](/core/prompts) - Writing effective prompts
