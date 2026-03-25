---
title: Memory
description: Make your agents remember conversations and learn over time
weight: 20
---

## The Problem: Your Agent Has Alzheimer's

Every conversation starts from scratch. Watch:

**Conversation 1:**
> User: Hi, my name is Alice.
> Agent: Hello Alice! Nice to meet you.

**Conversation 2 (5 minutes later):**
> User: What's my name again?
> Agent: I don't know your name. You haven't told me yet.

Sound familiar? This is how most AI agents work. They have **no memory**. Each conversation is a clean slate.

This is frustrating for users. You shouldn't have to repeat yourself.

---

## The Solution: Memory That Actually Works

What if your agent could remember?

- **Your name**, preferences, and habits
- **What you discussed** last time
- **Facts you taught** it
- **How you like things** done

Syrin's memory system makes this possible. It's inspired by how human memory actually works—some things are permanent, some fade over time, and some need reinforcement.

---

## The Human Memory Analogy

Think about how your brain works:

| Human Memory | Syrin Memory | What It Stores |
|-------------|--------------|----------------|
| **Who you are** | **Core** | Your name, identity, important facts |
| **What happened** | **Episodic** | Past conversations, events, experiences |
| **What you learned** | **Semantic** | Facts, knowledge, definitions |
| **How to do things** | **Procedural** | Procedures, processes, skills |

Just like your brain, Syrin:
- **Remembers important things** (high importance)
- **Forgets unimportant things** (decay over time)
- **Reinforces** memories when accessed (access boosts)

---

## Your First Agent With Memory

Here's a simple example:

```python
from syrin import Agent, Model
from syrin.memory import Memory
from syrin.enums import MemoryType

# Create agent with memory
agent = Agent(
    model=Model.Almock(),  # No API key needed
    memory=Memory()  # Enable memory!
)

# Tell the agent something
agent.remember("My name is Alice", memory_type=MemoryType.CORE)

# Later... the agent remembers!
response = agent.run("What do you know about me?")
print(response.content)
# "You told me your name is Alice."
```

**That's it.** Your agent now has persistent memory.

---

## The Four Memory Types

### 1. Core Memory (The Identity)

**What it stores:** Who you are, what matters to you.

**Characteristics:**
- Highest importance (0.9 by default)
- Rarely decays
- Always recalled first

**Examples:**
- "User's name is Alice"
- "User prefers concise answers"
- "User works at Acme Corp"
- "User is a Python developer"

```python
agent.remember("User's name is Alice", memory_type=MemoryType.CORE, importance=1.0)
```

**Best for:** User identity, preferences, key relationships.

---

### 2. Episodic Memory (The History)

**What it stores:** What happened, when, and where.

**Characteristics:**
- Medium importance (0.7 by default)
- Decays over time unless reinforced
- Captures specific events

**Examples:**
- "Yesterday we discussed Python"
- "User asked about pricing on Tuesday"
- "Last week: User wanted to export data"

```python
agent.remember("User asked about cloud pricing today", memory_type=MemoryType.EPISODIC)
```

**Best for:** Conversation history, past events, activities.

---

### 3. Semantic Memory (The Knowledge)

**What it stores:** Facts and learned information.

**Characteristics:**
- High importance (0.8 by default)
- Decays slowly
- Retrieved by meaning, not keywords

**Examples:**
- "User prefers Python over JavaScript"
- "User's company uses AWS"
- "User is building a chatbot"

```python
agent.remember("User prefers Python", memory_type=MemoryType.SEMANTIC)
```

**Best for:** Factual knowledge, preferences, learned information.

---

### 4. Procedural Memory (The Skills)

**What it stores:** How to do things.

**Characteristics:**
- High importance (0.85 by default)
- Decays very slowly
- Stores processes and workflows

**Examples:**
- "When user asks for code, add type hints"
- "User likes markdown formatted responses"
- "How to get user data: check the database"

```python
agent.remember("User wants responses in bullet points", memory_type=MemoryType.PROCEDURAL)
```

**Best for:** Instructions, procedures, learned behaviors.

---

## Basic Operations

### Remember (Store a Memory)

```python
# Simple remember
agent.remember("User likes dark mode")

# With type and importance
agent.remember(
    "User's name is Alice",
    memory_type=MemoryType.CORE,
    importance=1.0  # 1.0 = critical, 0.0 = forget immediately
)
```

### Recall (Get Memories)

```python
# Search by query
memories = agent.recall("preferences")
print([m.content for m in memories])

# Filter by type
core_memories = agent.recall(memory_type=MemoryType.CORE)

# Get all memories
all_memories = agent.recall()
```

### Forget (Delete a Memory)

```python
# Delete by query
agent.forget(query="old preference")

# Delete by type
agent.forget(memory_type=MemoryType.EPISODIC)

# Delete specific memory
agent.forget(memory_id="memory-123")
```

---

## Real Example: Personal Assistant

Here's how memory works in a real assistant:

```python
from syrin import Agent, Model
from syrin.memory import Memory
from syrin.enums import MemoryType

class Assistant(Agent):
    model = Model.Almock()
    memory = Memory()
    system_prompt = "You are a helpful personal assistant."

# First conversation
assistant.remember("User's name is Alice", memory_type=MemoryType.CORE)
assistant.remember("Alice prefers morning meetings", memory_type=MemoryType.SEMANTIC)
assistant.remember("Discussed project timeline today", memory_type=MemoryType.EPISODIC)
assistant.remember("Alice likes bullet points", memory_type=MemoryType.PROCEDURAL)

# Second conversation (days later)
response = assistant.run("What do you remember about me?")
# "Your name is Alice, you prefer morning meetings, and you like responses in bullet points."
```

---

## Understanding Importance

Every memory has an importance score (0.0 to 1.0):

| Score | Meaning | Example |
|-------|---------|---------|
| **1.0** | Critical, never forget | User's name |
| **0.8-0.9** | Very important | Strong preferences |
| **0.5-0.7** | Important | Recent events |
| **0.3-0.5** | Somewhat important | Minor details |
| **0.0-0.2** | Forget soon | Temporary info |

```python
# Critical memory (never decays)
agent.remember("User is John Smith", importance=1.0, memory_type=MemoryType.CORE)

# Temporary memory (forget quickly)
agent.remember("User is looking at laptops today", importance=0.3)
```

---

## Decay: How Forgetting Works

Just like human memory, Syrin memories **fade over time** unless reinforced.

### Why Decay?

- Keeps memory from overflowing
- Removes outdated information
- Focuses on what's relevant
- Agents become more accurate over time

### How It Works

```python
from syrin.memory import Decay
from syrin.enums import DecayStrategy

# Enable decay
memory = Memory(
    decay=Decay(
        strategy=DecayStrategy.EXPONENTIAL,
        rate=0.95,  # How fast to forget (higher = slower)
        reinforce_on_access=True,  # Access boosts memory
        min_importance=0.1  # Floor - never forget below this
    )
)
```

### Decay Strategies

| Strategy | How It Works | Best For |
|----------|-------------|----------|
| **EXPONENTIAL** | Fast initial decay, then slower | Typical forgetfulness |
| **LINEAR** | Constant rate | Predictable aging |
| **LOGARITHMIC** | Slow start, faster later | Long-term retention |
| **NONE** | No decay | Critical, permanent memories |

### Half-Life

Set decay by how long memories should last:

```python
# Memory halves in importance every 24 hours
decay = Decay(
    strategy=DecayStrategy.EXPONENTIAL,
    half_life_hours=24,  # Importance halves every 24 hours
)
```

---

## Automatic Memory

Don't want to manually remember everything? Enable auto-store:

```python
memory = Memory(
    auto_store=True  # Automatically stores conversations
)

agent = Agent(model=Model.Almock(), memory=memory)

# Every conversation is automatically remembered
agent.run("I love coffee")
agent.run("My favorite is espresso")
# These are automatically stored as episodic memories
```

---

## Configuration

### Quick Start (Most Use Cases)

```python
memory = Memory()  # Defaults work great!
```

### Common Configurations

```python
# High-memory assistant
memory = Memory(
    top_k=10,  # Recall up to 10 memories
    decay=Decay(strategy=DecayStrategy.EXPONENTIAL, rate=0.99),
)

# Fast, minimal memory
memory = Memory(
    top_k=3,
    types=[MemoryType.CORE],  # Only core memories
)

# Research assistant
memory = Memory(
    top_k=20,
    decay=Decay(half_life_hours=48),
    types=[MemoryType.CORE, MemoryType.SEMANTIC, MemoryType.PROCEDURAL],
)
```

### All Options

```python
from syrin.enums import InjectionStrategy, WriteMode

memory = Memory(
    # Storage
    backend=MemoryBackend.SQLITE,  # or MEMORY, QDRANT, REDIS, etc.
    path="./memory.db",
    
    # What to store
    types=[MemoryType.CORE, MemoryType.EPISODIC, MemoryType.SEMANTIC, MemoryType.PROCEDURAL],
    
    # Retrieval
    top_k=10,  # Max memories to recall
    relevance_threshold=0.7,  # Min relevance (0-1)
    injection_strategy=InjectionStrategy.ATTENTION_OPTIMIZED,
    
    # Behavior
    auto_store=True,  # Auto-save conversations
    decay=Decay(strategy=DecayStrategy.EXPONENTIAL),
    write_mode=WriteMode.ASYNC,  # Don't block on write
)
```

---

## What's Next?

- [Memory Types](/core/memory-types) - Deep dive into each memory type
- [Memory Backends](/core/memory-backends) - SQLite, Redis, PostgreSQL, and more
- [Context](/core/context) - How memory fits into context window

## See Also

- [Prompts](/core/prompts) - Instruct your agent effectively
- [Budget](/core/budget) - Control memory costs
- [Agents](/agent/overview) - Building agents with memory
