---
title: Memory Types
description: Deep dive into Core, Episodic, Semantic, and Procedural memory
weight: 21
---

## The Four Pillars of Agent Memory

Syrin gives you four distinct types of memory, each inspired by cognitive science. Understanding when to use each type is the key to building agents that truly remember.

Think of them as four different filing cabinets in your brain's memory system.

---

## Memory Type Overview

| Type | Purpose | Default Importance | Decay | Best For |
|------|---------|-------------------|-------|----------|
| **Core** | Identity & preferences | 0.9 | Rarely | User's name, key facts |
| **Episodic** | Events & experiences | 0.7 | Normal | Conversations, activities |
| **Semantic** | Facts & knowledge | 0.8 | Slow | Learned information |
| **Procedural** | Skills & processes | 0.85 | Very slow | How-to, procedures |

---

## Core Memory: The Identity Cabinet

**Purpose:** Store permanent facts about the user and agent.

Core memories are the most important. They rarely decay and are always recalled first.

### What Goes in Core Memory

- User's name and identity
- Critical preferences that never change
- Key relationships and context
- System identity information

### Examples

```python
from syrin.enums import MemoryType

# User identity
agent.remember("User's name is Alice Johnson", memory_type=MemoryType.CORE, importance=1.0)

# Critical preferences
agent.remember("User is the CEO of Acme Corp", memory_type=MemoryType.CORE, importance=0.95)
agent.remember("User has dietary restriction: vegan", memory_type=MemoryType.CORE, importance=0.9)

# System facts
agent.remember("This is a customer support agent for Acme SaaS", memory_type=MemoryType.CORE)
```

### Characteristics

- **Importance:** 0.9 default (very high)
- **Decay:** Minimal or none
- **Recall priority:** Always recalled first
- **Typical count:** 5-20 memories per user

### When to Use Core

Use Core when the information is:
- A fact about the user
- Something that rarely changes
- Critical for personalization
- A piece of identity

---

## Episodic Memory: The Experience Journal

**Purpose:** Record specific events and experiences.

Episodic memories capture what happened, when, and where. They decay over time unless reinforced—like how you remember what you had for lunch yesterday but forget details from last month.

### What Goes in Episodic Memory

- Past conversations
- User's activities
- Recent events
- Temporal context

### Examples

```python
from syrin.enums import MemoryType

# Conversation summaries
agent.remember(
    "Yesterday: User asked about upgrading their subscription",
    memory_type=MemoryType.EPISODIC
)

# Activity tracking
agent.remember(
    "User viewed the pricing page three times this week",
    memory_type=MemoryType.EPISODIC
)

# Context from past sessions
agent.remember(
    "Last conversation: User wanted to export data but it failed",
    memory_type=MemoryType.EPISODIC
)
```

### Characteristics

- **Importance:** 0.7 default
- **Decay:** Normal (set decay strategy)
- **Recall priority:** By recency and relevance
- **Typical count:** 20-100 memories per user

### When to Use Episodic

Use Episodic when you want to:
- Track conversation history
- Remember what happened when
- Provide continuity across sessions
- Capture temporal patterns

---

## Semantic Memory: The Knowledge Base

**Purpose:** Store facts and learned information.

Semantic memories are factual knowledge—things the user has taught the agent or that have been learned over time. Unlike Episodic (which is about specific events), Semantic is about general knowledge.

### What Goes in Semantic Memory

- User preferences (factual)
- Learned information
- Company/project knowledge
- Definitions and facts

### Examples

```python
from syrin.enums import MemoryType

# User preferences (factual)
agent.remember(
    "User prefers Python over JavaScript",
    memory_type=MemoryType.SEMANTIC
)
agent.remember(
    "User's timezone is US/Pacific",
    memory_type=MemoryType.SEMANTIC
)

# Project knowledge
agent.remember(
    "The project uses React for frontend and Django for backend",
    memory_type=MemoryType.SEMANTIC
)

# Company context
agent.remember(
    "Acme Corp has 50 employees and raised Series B",
    memory_type=MemoryType.SEMANTIC
)
```

### Characteristics

- **Importance:** 0.8 default
- **Decay:** Slow
- **Recall priority:** By relevance
- **Typical count:** 10-50 memories per user

### Semantic vs Episodic

| Situation | Use Episodic | Use Semantic |
|-----------|--------------|--------------|
| "Yesterday we discussed X" | ✅ | ❌ |
| "User prefers X" (fact) | ❌ | ✅ |
| "Last meeting was about X" | ✅ | ❌ |
| "X is true about user" | ❌ | ✅ |

---

## Procedural Memory: The Skills Handbook

**Purpose:** Store how to do things.

Procedural memories are skills and processes—how to accomplish tasks, what workflows exist, and what procedures to follow. Think of it as the agent's muscle memory.

### What Goes in Procedural Memory

- How to do something
- Workflows and processes
- User's preferred methods
- Best practices for this user

### Examples

```python
from syrin.enums import MemoryType

# User's preferred output style
agent.remember(
    "User likes responses formatted as markdown with headers",
    memory_type=MemoryType.PROCEDURAL
)

# How to accomplish tasks
agent.remember(
    "To generate reports: 1) Query database 2) Format with Jinja 3) Send via email",
    memory_type=MemoryType.PROCEDURAL
)

# User's communication style
agent.remember(
    "Be direct and concise with this user - they don't like fluff",
    memory_type=MemoryType.PROCEDURAL
)

# System procedures
agent.remember(
    "Before deploying: run tests, get approval from lead, deploy to staging first",
    memory_type=MemoryType.PROCEDURAL
)
```

### Characteristics

- **Importance:** 0.85 default
- **Decay:** Very slow
- **Recall priority:** When relevant to current task
- **Typical count:** 5-30 memories per user

---

## Quick Reference: Which Type to Use?

### User Identity & Preferences

```python
# Core for permanent facts
agent.remember("User's name is Alice", memory_type=MemoryType.CORE)
```

### Conversation History

```python
# Episodic for past events
agent.remember("User asked about billing yesterday", memory_type=MemoryType.EPISODIC)
```

### Learned Facts

```python
# Semantic for factual knowledge
agent.remember("User works in the marketing department", memory_type=MemoryType.SEMANTIC)
```

### How-To & Processes

```python
# Procedural for skills
agent.remember("User wants summaries at the top of emails", memory_type=MemoryType.PROCEDURAL)
```

---

## Using Type-Specific Classes

For fine-grained control, use the specific memory classes:

```python
from syrin.memory import CoreMemory, EpisodicMemory, SemanticMemory, ProceduralMemory

# Core with custom importance
core = CoreMemory(
    id="user-name",
    content="User's name is Alice Johnson",
    importance=1.0  # Maximum importance
)

# Semantic with metadata
semantic = SemanticMemory(
    id="preference-python",
    content="User prefers Python for data tasks",
    importance=0.9,
    keywords=["python", "data", "preference"]
)

# Procedural with expiration
procedural = ProceduralMemory(
    id="workflow-approval",
    content="Submit to manager for approval",
    importance=0.85,
    valid_until=datetime(2025, 12, 31)  # Expires at end of year
)
```

---

## Factory Function

Create memories by type with smart defaults:

```python
from syrin.memory import create_memory
from syrin.enums import MemoryType

# Creates CoreMemory with default importance 0.9
mem = create_memory(
    memory_type=MemoryType.CORE,
    id="my-memory",
    content="The memory content"
)
```

---

## Filtering by Type

Retrieve memories of specific types:

```python
# All core memories
core = agent.recall(memory_type=MemoryType.CORE)

# All episodic memories
episodic = agent.recall(memory_type=MemoryType.EPISODIC)

# Search within a specific type
python_prefs = agent.recall("Python", memory_type=MemoryType.SEMANTIC)
```

---

## Deleting by Type

Remove all memories of a type:

```python
# Clear all episodic memories
agent.forget(memory_type=MemoryType.EPISODIC)

# Keep core, semantic, procedural but clear history
agent.forget(memory_type=MemoryType.EPISODIC)
```

---

## What's Next?

- [Memory Backends](/agent-kit/core/memory-backends) - Choose where memories are stored
- [Memory Overview](/agent-kit/core/memory) - Back to memory basics

## See Also

- [Agents](/agent-kit/agent/overview) - Building agents with memory
- [Budget](/agent-kit/core/budget) - Control memory costs
