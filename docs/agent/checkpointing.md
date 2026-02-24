# Checkpointing

> **Config & backends:** For CheckpointConfig, storage backends (sqlite, filesystem), and CheckpointTrigger details, see [Checkpoints](../checkpoint.md).

Checkpoints save and restore agent state so you can resume runs or recover from failures.

## Configuration

```python
from syrin import Agent
from syrin.checkpoint import CheckpointConfig
from syrin.enums import CheckpointTrigger

agent = Agent(
    model=model,
    checkpoint=CheckpointConfig(
        enabled=True,
        storage="sqlite",
        path="/tmp/agent_checkpoints.db",
        trigger=CheckpointTrigger.STEP,
        max_checkpoints=10,
    ),
)
```

## CheckpointTrigger

| Trigger | When |
|---------|------|
| `MANUAL` | Only when `save_checkpoint()` is called |
| `STEP` | After each response step |
| `TOOL` | After each tool call |
| `ERROR` | On exception |
| `BUDGET` | On budget exceeded |

## Manual Checkpoints

### save_checkpoint()

```python
checkpoint_id = agent.save_checkpoint(
    name="my_agent",
    reason="before_expensive_step",
)
```

**Returns:** `str | None` (checkpoint ID or `None` if disabled)

### load_checkpoint()

```python
success = agent.load_checkpoint(checkpoint_id)
```

**Returns:** `bool`

### list_checkpoints()

```python
ids = agent.list_checkpoints(name="my_agent")
```

**Returns:** `list[str]`

## get_checkpoint_report()

```python
report = agent.get_checkpoint_report()
# report.checkpoints.saves
# report.checkpoints.loads
```

## Checkpoint State

State includes:

- `iteration` (token count / progress)
- `messages`
- `memory_data`
- `budget_state`
- `checkpoint_reason`

## Automatic Checkpoints

With `trigger=STEP` or `TOOL`, checkpoints are saved automatically at the configured points. With `ERROR` or `BUDGET`, they are saved when those events occur.

## See Also

- [Checkpoints](../checkpoint.md) — Full config, storage backends, triggers
