---
title: Checkpointing
description: Save and restore agent state for resilience, debugging, and resumable conversations
weight: 130
---

## Why Checkpointing?

It's 3 AM. Your agent was halfway through analyzing a complex request when the server restarted. The entire conversation history is gone. The user has to start over.

Checkpointing saves agent state periodically — conversation history, memory contents, budget tracking, and iteration count. When something goes wrong, you restore from the last checkpoint and continue exactly where you left off.

## Basic Setup

```python
from syrin import Agent, Model
from syrin.checkpoint import CheckpointConfig, CheckpointTrigger

agent = Agent(
    model=Model.mock(),
    system_prompt="You are a helpful assistant.",
    checkpoint=CheckpointConfig(
        storage="sqlite",
        path="/tmp/checkpoints.db",
        trigger=CheckpointTrigger.STEP,
    ),
)
```

After each LLM response, the agent's full state is saved to the SQLite database. If the server crashes, restore from the last checkpoint and the user picks up right where they left off.

## What Gets Saved

A checkpoint captures everything needed to resume: conversation history (all messages), memory contents, budget state (spent/limit), and the iteration count. Restore it and the agent continues as if the interruption never happened.

## Trigger Options

Five trigger modes control when automatic checkpoints are saved.

`CheckpointTrigger.STEP` — Save after each LLM response. Maximum resilience. Use this for production.

`CheckpointTrigger.TOOL` — Save after each tool call. More granular for debugging.

`CheckpointTrigger.ERROR` — Only save when an error occurs. Good for capturing failure state.

`CheckpointTrigger.BUDGET` — Save when a budget threshold is hit.

`CheckpointTrigger.MANUAL` — Never save automatically. You control every save explicitly.

## Storage Backends

**Memory** — In-process only, no disk I/O. State is lost when the process restarts. Good for testing:

```python
checkpoint=CheckpointConfig(storage="memory")
```

**SQLite** — Persistent, no server required. Good for single-server deployments:

```python
checkpoint=CheckpointConfig(storage="sqlite", path="/var/lib/syrin/checkpoints.db")
```

**Filesystem** — Each checkpoint is a JSON file. Good when you want to inspect checkpoints manually:

```python
checkpoint=CheckpointConfig(storage="filesystem", path="/var/lib/syrin/checkpoints/")
```

## Manual Checkpointing

Save checkpoints explicitly for precise control:

```python
from syrin import Agent, Model
from syrin.checkpoint import CheckpointConfig

agent = Agent(model=Model.mock(), checkpoint=CheckpointConfig(storage="memory"))

# Save before a risky operation
checkpoint_id = agent.save_checkpoint(reason="before_analysis")

try:
    result = agent.run("Analyze this 10,000 page document")
except Exception as e:
    print(f"Analysis failed: {e}")
    agent.load_checkpoint(checkpoint_id)  # Restore to safe state
    print("Restored to before the analysis")
```

## Named Checkpoints

Group checkpoints at key stages and restore by name:

```python
agent.save_checkpoint(name="after_classification")
agent.save_checkpoint(name="after_research")
agent.save_checkpoint(name="after_draft")

# Find all checkpoints with a specific name
ids = agent.list_checkpoints(name="after_research")
print(ids)  # ['assistant_5', 'assistant_8']

# Restore the most recent one
if ids:
    agent.load_checkpoint(ids[-1])
```

## Managing Checkpoints

```python
# List all checkpoints for this agent
all_checkpoints = agent.list_checkpoints()
print(all_checkpoints)  # ['assistant_1', 'assistant_2', 'assistant_3']

# Get the most recent checkpoint
latest = agent.checkpointer.get_latest(agent.name)
print(f"Latest: {latest.checkpoint_id} at {latest.created_at}")

# Delete old checkpoints to save space
for checkpoint_id in all_checkpoints[:-5]:  # Keep last 5
    agent.checkpointer.delete(checkpoint_id)
```

## Configuration Reference

```python
from syrin.checkpoint import CheckpointConfig, CheckpointTrigger

config = CheckpointConfig(
    enabled=True,                        # Enable checkpointing
    storage="sqlite",                    # Backend: memory, sqlite, filesystem
    path="/tmp/checkpoints.db",          # Path for sqlite/filesystem
    trigger=CheckpointTrigger.STEP,      # When to auto-save
    max_checkpoints=10,                  # Keep last N checkpoints per agent
    compress=False,                       # Compress stored state
)
```

## Hooks

```python
from syrin.enums import Hook

agent.events.on(Hook.CHECKPOINT_SAVE, lambda ctx: print(
    f"Saved checkpoint {ctx['checkpoint_id']} (reason: {ctx['checkpoint_reason']})"
))

agent.events.on(Hook.CHECKPOINT_LOAD, lambda ctx: print(
    f"Loaded checkpoint {ctx['checkpoint_id']}"
))
```

## Tracking Checkpoint Usage

```python
report = agent.get_checkpoint_report()
print(f"Total saves: {report.checkpoints.saves}")
print(f"Total loads: {report.checkpoints.loads}")
```

## Patterns

### Resumable Long Conversations

```python
from syrin.checkpoint import CheckpointConfig, CheckpointTrigger

agent = Agent(
    model=Model.mock(),
    checkpoint=CheckpointConfig(
        storage="sqlite",
        path="/var/data/agent_checkpoints.db",
        trigger=CheckpointTrigger.STEP,
        max_checkpoints=50,
    ),
)

# User starts
checkpoint_id = agent.save_checkpoint(name="session_start")

# Hours later, user returns
checkpoints = agent.list_checkpoints(name="session_start")
if checkpoints:
    agent.load_checkpoint(checkpoints[-1])
    print("Resumed your session")
```

### A/B Testing Different Continuations

```python
agent = Agent(model=Model.mock(), checkpoint=CheckpointConfig(storage="memory"))

# Run the setup phase
agent.run("First message in the conversation")
checkpoint_id = agent.save_checkpoint()

# Try approach A
result_a = agent.run("Approach A")

# Restore and try approach B
agent.load_checkpoint(checkpoint_id)
result_b = agent.run("Approach B")

# Compare results
print(f"A: {result_a.content[:50]}")
print(f"B: {result_b.content[:50]}")
```

## Custom Backend

Implement `CheckpointBackendProtocol` to store checkpoints in your own system:

```python
from syrin.checkpoint import CheckpointBackendProtocol
```

The package also exports `FilesystemCheckpointBackend`, `MemoryCheckpointBackend`, and `SQLiteCheckpointBackend` for reference implementations.

## See Also

- [Lifecycle Controls](/multi-agent/lifecycle) — Pause/resume for workflows
- [Error Handling](/agent/error-handling) — Handle failures gracefully
- [Budget](/core/budget) — Budget configuration
