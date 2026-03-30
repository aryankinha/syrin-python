---
title: Checkpointing
description: Save and restore agent state for resilience, debugging, and resumable conversations
weight: 130
---

## The Day the Server Crashed

It's 3 AM. Your agent was halfway through analyzing a complex user request when—power outage. The entire conversation is gone. The user has to start over. You have no idea where the agent left off.

This happens. Servers crash. Networks drop. Users abandon sessions. Without checkpointing, every interruption means starting from scratch.

Checkpointing solves this by periodically saving agent state: conversation history, memory contents, budget tracking, and iteration count. When something goes wrong, you restore from the last checkpoint and continue.

## The Problem

Production AI systems face real-world failures:
- **Server crashes** during long-running conversations
- **Network timeouts** mid-request
- **Budget exhaustion** in complex multi-turn dialogues
- **Debugging sessions** where you want to replay specific states
- **A/B testing** different continuation strategies

Without state persistence, you lose:
- All conversation context
- Memory contents (what the agent learned)
- Budget state (what's been spent)
- Iteration progress (where the agent left off)

## The Solution

Syrin's checkpoint system saves agent state automatically or on-demand:

```python
from syrin import Agent, Model, CheckpointConfig, CheckpointTrigger

model = Model.OpenAI("gpt-4o", api_key="your-api-key")

agent = Agent(
    model=model,
    system_prompt="You are a helpful assistant.",
    checkpoint=CheckpointConfig(
        storage="sqlite",
        path="/tmp/checkpoints.db",
        trigger=CheckpointTrigger.STEP,
    ),
)
```

**What just happened**: The agent is now configured to save its state after each step (LLM response). If the server crashes, you can restore from the last checkpoint.

## What Gets Saved

A checkpoint captures everything needed to resume:

```python
# CheckpointState contains:
state = {
    "agent_name": "assistant",
    "checkpoint_id": "assistant_1",
    "created_at": "2024-01-15T03:00:00",
    "messages": [...],           # Conversation history
    "memory_data": {...},        # Memory contents
    "budget_state": {...},       # Budget tracking
    "iteration": 3,              # Where we were in the loop
    "metadata": {
        "checkpoint_reason": "step"
    }
}
```

This means you can restore to exactly where you left off.

## Automatic Checkpointing

Configure when checkpoints are saved automatically:

```python
from syrin import CheckpointConfig, CheckpointTrigger

# After each LLM response (default)
checkpoint=CheckpointConfig(trigger=CheckpointTrigger.STEP)

# After each tool call
checkpoint=CheckpointConfig(trigger=CheckpointTrigger.TOOL)

# Only when errors occur
checkpoint=CheckpointConfig(trigger=CheckpointTrigger.ERROR)

# Only when budget is exceeded
checkpoint=CheckpointConfig(trigger=CheckpointTrigger.BUDGET)

# Manual only (no auto-save)
checkpoint=CheckpointConfig(trigger=CheckpointTrigger.MANUAL)
```

### Trigger Reference

| Trigger | When It Saves | Use Case |
|---------|--------------|----------|
| `STEP` | After each LLM response | Maximum resilience |
| `TOOL` | After each tool call | Detailed debugging |
| `ERROR` | When errors occur | Debug production issues |
| `BUDGET` | When budget exceeded | Cost tracking |
| `MANUAL` | Never automatically | You control everything |

## Storage Backends

### Memory (Ephemeral)

For testing and short-lived sessions:

```python
checkpoint=CheckpointConfig(storage="memory")
```

State is lost when the process restarts. Fast, no disk I/O.

### SQLite (Persistent)

For single-server deployments:

```python
checkpoint=CheckpointConfig(
    storage="sqlite",
    path="/var/lib/syrin/checkpoints.db",
)
```

SQLite provides persistent storage with automatic cleanup.

### Filesystem

For those who prefer JSON files:

```python
checkpoint=CheckpointConfig(
    storage="filesystem",
    path="/var/lib/syrin/checkpoints/",
)
```

Each checkpoint becomes a `.json` file.

## Manual Checkpointing

Save checkpoints explicitly when you need precise control:

```python
# Save before an expensive operation
checkpoint_id = agent.save_checkpoint(reason="before_analysis")

try:
    result = agent.run("Analyze this 10,000 page document")
except Exception as e:
    print(f"Analysis failed: {e}")
    agent.load_checkpoint(checkpoint_id)
    print("Restored to safe state")
```

**What just happened**: You saved state before a risky operation. If it fails, you restore and try a different approach.

## Named Checkpoints

Group checkpoints by name for easier management:

```python
# Save at key decision points
agent.save_checkpoint(name="after_classification")
agent.save_checkpoint(name="after_research")
agent.save_checkpoint(name="after_draft")

# List checkpoints by name
ids = agent.list_checkpoints(name="after_research")
print(ids)  # ['assistant_5', 'assistant_8']

# Restore specific checkpoint
if ids:
    agent.load_checkpoint(ids[-1])
```

## Listing and Managing Checkpoints

```python
# List all checkpoints for this agent
all_checkpoints = agent.list_checkpoints()
print(all_checkpoints)  # ['assistant_1', 'assistant_2', 'assistant_3']

# Get the most recent checkpoint
latest = agent.checkpointer.get_latest(agent.name)
print(f"Latest: {latest.checkpoint_id} at {latest.created_at}")

# Delete old checkpoints
for checkpoint_id in all_checkpoints[:-5]:
    agent.checkpointer.delete(checkpoint_id)
```

## Configuration Reference

```python
from syrin import CheckpointConfig

config = CheckpointConfig(
    enabled=True,                    # Enable checkpointing
    storage="sqlite",                # Backend: memory, sqlite, filesystem
    path="/tmp/checkpoints.db",       # Path for sqlite/filesystem
    trigger=CheckpointTrigger.STEP,   # When to auto-save
    max_checkpoints=10,              # Keep last N checkpoints
    compress=False,                   # Compress stored state
)
```

### Parameter Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | `bool` | `True` | Enable automatic saving |
| `storage` | `str` | `"memory"` | Backend: memory, sqlite, filesystem |
| `path` | `str` | `None` | Path for sqlite/filesystem backends |
| `trigger` | `CheckpointTrigger` | `STEP` | When to auto-save |
| `max_checkpoints` | `int` | `10` | Maximum checkpoints per agent |
| `compress` | `bool` | `False` | Compress stored state |

## Hooks and Observability

Checkpoint operations emit lifecycle hooks:

```python
from syrin import Agent, Hook

agent = Agent(model=model, checkpoint=CheckpointConfig())

def on_checkpoint_save(ctx):
    print(f"Checkpoint saved: {ctx.checkpoint_id}")
    print(f"  Reason: {ctx.checkpoint_reason}")
    print(f"  Iteration: {ctx.iteration}")

agent.events.on(Hook.CHECKPOINT_SAVE, on_checkpoint_save)

def on_checkpoint_load(ctx):
    print(f"Checkpoint loaded: {ctx.checkpoint_id}")

agent.events.on(Hook.CHECKPOINT_LOAD, on_checkpoint_load)
```

### Available Hooks

| Hook | When | Context |
|------|------|---------|
| `CHECKPOINT_SAVE` | After checkpoint is saved | `checkpoint_id`, `reason`, `iteration` |
| `CHECKPOINT_LOAD` | After state is restored | `checkpoint_id` |

## Checkpoint Reports

Track checkpoint usage for debugging:

```python
report = agent.get_checkpoint_report()
print(f"Saves: {report.checkpoints.saves}")
print(f"Loads: {report.checkpoints.loads}")
```

## Real-World Patterns

### Resumable Long Conversations

```python
from syrin import Agent, CheckpointConfig, CheckpointTrigger

agent = Agent(
    model=model,
    checkpoint=CheckpointConfig(
        storage="sqlite",
        path="/var/data/agent_checkpoints.db",
        trigger=CheckpointTrigger.STEP,
        max_checkpoints=50,
    ),
)

# User starts a long task
checkpoint_id = agent.save_checkpoint(name="task_start")

# Hours later, user returns
checkpoints = agent.list_checkpoints(name="task_start")
if checkpoints:
    agent.load_checkpoint(checkpoints[-1])
    print("Resumed your task")
else:
    print("Starting fresh")
```

### Debug Production Issues

```python
# Save checkpoints more frequently in staging
agent = Agent(
    model=model,
    checkpoint=CheckpointConfig(
        storage="filesystem",
        path="/var/log/syrin/checkpoints/",
        trigger=CheckpointTrigger.TOOL,  # More detailed
    ),
)
```

### Testing Agent Behavior

```python
# Save checkpoint after each step, then replay
agent = Agent(
    model=model,
    checkpoint=CheckpointConfig(storage="memory"),
)

# Run once
result1 = agent.run("Complex query")
cp_id = agent.save_checkpoint()

# Restore and try different approach
agent.load_checkpoint(cp_id)
result2 = agent.run("Different approach to same query")
```

## Public Checkpoint Backend API

If you need checkpoint persistence outside the default path, the checkpoint package also exports:

- `Checkpointer` as the runtime object that performs save/load operations.
- `CheckpointBackendProtocol` for implementing your own backend.
- `FilesystemCheckpointBackend`, `MemoryCheckpointBackend`, and `SQLiteCheckpointBackend` as ready-made backends.
- `get_checkpoint_backend()` and `BACKENDS` for backend lookup and registration-style wiring.

## See Also

- [Error Handling](/agent-kit/agent/error-handling) — Handling errors gracefully
- [Budget](/agent-kit/core/budget) — Budget configuration
- [Memory](/agent-kit/core/memory) — Memory configuration
- [Serving: Advanced](/agent-kit/production/serving-advanced) — Deploying checkpointed agents
