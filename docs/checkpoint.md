# Checkpoints

Syrin provides a checkpoint system for saving and restoring agent state. This is essential for:

> **Agent integration:** For `save_checkpoint()`, `load_checkpoint()`, and the agent `checkpoint=` param, see [Agent: Checkpointing](agent/checkpointing.md).

- **Failure recovery**: Resume from the last checkpoint after crashes
- **Long-running tasks**: Save progress during multi-step workflows  
- **Budget management**: Prevent losing progress when approaching budget limits
- **Debugging**: Replay from specific checkpoints

## Quick Start

```python
from Syrin import Agent, Model, CheckpointConfig

agent = Agent(
    # model=Model("gpt-4o"),
    model=Model.Almock(),  # No API Key needed
    checkpoint=CheckpointConfig(storage="memory"),
)

checkpoint_id = agent.save_checkpoint()
checkpoints = agent.list_checkpoints()
agent.load_checkpoint(checkpoints[-1])
```

## Configuration

### CheckpointConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | `bool` | `True` | Enable checkpointing |
| `storage` | `str` | `"memory"` | Storage backend: `memory`, `sqlite`, `filesystem` |
| `path` | `str` | `None` | Path for file-based storage |
| `trigger` | `CheckpointTrigger` | `STEP` | When to auto-save |
| `max_checkpoints` | `int` | `10` | Maximum checkpoints to keep |
| `compress` | `bool` | `False` | Compress checkpoint data |

### Checkpoint Triggers

```python
from Syrin import CheckpointTrigger

CheckpointTrigger.MANUAL   # Only save explicitly
CheckpointTrigger.STEP     # After each agent step
CheckpointTrigger.TOOL     # After each tool call
CheckpointTrigger.ERROR    # On errors
CheckpointTrigger.BUDGET   # Before budget exhaustion
```

## Storage Backends

### In-Memory (Default)

```python
agent = Agent(
    # model=Model("gpt-4o"),
    model=Model.Almock(),  # No API Key needed
    checkpoint=CheckpointConfig(storage="memory"),
)
```

Best for: Testing, short-lived agents

### SQLite

```python
agent = Agent(
    # model=Model("gpt-4o"),
    model=Model.Almock(),  # No API Key needed
    checkpoint=CheckpointConfig(
        storage="sqlite",
        path="/tmp/agent_checkpoints.db",
    ),
)
```

Best for: Single-user applications, persistent local storage

### Filesystem

```python
agent = Agent(
    # model=Model("gpt-4o"),
    model=Model.Almock(),  # No API Key needed
    checkpoint=CheckpointConfig(
        storage="filesystem",
        path="/tmp/checkpoints",
    ),
)
```

Best for: Simple deployment, debugging

## API Reference

### Agent Methods

```python
agent.save_checkpoint(name: str | None = None) -> str | None
agent.load_checkpoint(checkpoint_id: str) -> bool
agent.list_checkpoints(name: str | None = None) -> list[str]
agent.get_checkpoint_report() -> AgentReport
```

### Checkpointer Class

```python
from Syrin import Checkpointer

checkpointer = Checkpointer()
checkpoint_id = checkpointer.save("agent_name", {"key": "value"})
state = checkpointer.load(checkpoint_id)
checkpoints = checkpointer.list_checkpoints("agent_name")
checkpointer.delete(checkpoint_id)
```

### CheckpointState

```python
from Syrin import CheckpointState

state = CheckpointState(
    agent_name="my_agent",
    checkpoint_id="my_agent_1",
    messages=[...],
    memory_data={...},
    budget_state={"remaining": 50.0},
    iteration=5,
    metadata={"step": "tool_execution"},
)
```

## Integration with Reports

Checkpoint operations are tracked in the response report:

```python
result = agent.response("Hello")
result.report.checkpoints.saves  # Number of saves
result.report.checkpoints.loads  # Number of loads
```

## Integration with Hooks

Checkpoint operations emit hooks:

```python
from Syrin import Hook

agent.events.on(Hook.CHECKPOINT_SAVE, lambda ctx: print(f"Saved: {ctx.checkpoint_id}"))
agent.events.on(Hook.CHECKPOINT_LOAD, lambda ctx: print(f"Loaded: {ctx.checkpoint_id}"))
```

## Best Practices

1. **Use SQLite for production**: Persistent storage survives restarts
2. **Set reasonable max_checkpoints**: Prevents unbounded storage growth
3. **Save before critical operations**: Call `save_checkpoint()` before expensive tool calls
4. **Name your checkpoints**: Use meaningful names for organization
5. **Monitor checkpoint sizes**: Large message histories can consume significant storage
