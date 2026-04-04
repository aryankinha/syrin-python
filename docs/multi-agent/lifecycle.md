---
title: Lifecycle Controls
description: play(), pause(), resume(), cancel(), RunHandle, PauseMode, and cross-process checkpoint resume for Workflow and Swarm
weight: 72
---

## Controlling Long-Running Pipelines

A `Workflow` runs for seconds, minutes, or longer. Sometimes you need to pause it mid-flight. Sometimes a server restarts and you need to pick up where you left off. This is what lifecycle controls are for.

The key distinction: `run()` is a convenience method that starts and waits in one call. `play()` starts the workflow in the background and immediately returns a `RunHandle` you can use to pause, resume, or cancel.

## Starting Non-Blocking with play()

```python
import asyncio
from syrin import Agent, Budget, Model
from syrin.workflow import Workflow

class StepA(Agent):
    model = Model.mock()

class StepB(Agent):
    model = Model.mock()

class StepC(Agent):
    model = Model.mock()

async def main():
    wf = (
        Workflow("demo", budget=Budget(max_cost=1.00))
        .step(StepA)
        .step(StepB)
        .step(StepC)
    )

    handle = wf.play("Run the pipeline")
    # Returns immediately — workflow is running in background

    print(handle.status)        # WorkflowStatus.RUNNING
    print(handle.run_id)        # "run-4f7a3b2c1d0e"
    print(handle.step_index)    # -1 (no step completed yet)
    print(handle.budget_spent)  # 0.0

    result = await handle.wait()  # Block until finished
    print(result.content)

asyncio.run(main())
```

The `RunHandle` has four attributes: `run_id` is the unique identifier for this run (also appears in hook context). `status` is the current lifecycle state. `step_index` is the zero-based index of the last completed step (starts at -1 before any step finishes). `budget_spent` is the total cost accumulated so far in USD.

`await handle.wait()` blocks until the workflow reaches a terminal state and returns the final `Response`. If the workflow was cancelled before finishing, it raises `WorkflowCancelledError`.

## Pausing

Three pause modes give you control over how clean the pause is.

### AFTER_CURRENT_STEP (default)

Finish the currently running step, then pause before the next one. This is the safest option — the in-progress step completes and its output is preserved.

```python
await wf.pause()  # Default mode: AFTER_CURRENT_STEP
```

### DRAIN

Like `AFTER_CURRENT_STEP`, but also waits for any pending tool calls inside the current step to complete. Use this when tools make external API calls that must not be interrupted.

```python
from syrin.enums import PauseMode

await wf.pause(PauseMode.DRAIN)
```

### IMMEDIATE

Interrupt the workflow as soon as possible, potentially in the middle of a step. The in-flight step's output is lost. Use this only when you need to abort fast and don't care about partial results.

```python
await wf.pause(PauseMode.IMMEDIATE)
```

After any pause, `handle.status` becomes `WorkflowStatus.PAUSED` and the `WORKFLOW_PAUSED` hook fires.

## Resuming

```python
await wf.resume()
```

Picks up from the step boundary where the workflow paused. The `WORKFLOW_RESUMED` hook fires and execution continues. If the workflow was cancelled before you call `resume()`, it raises `WorkflowCancelledError`.

## Cancelling

```python
await wf.cancel()
```

Permanently stops the workflow. Any running step is abandoned. `handle.status` becomes `WorkflowStatus.CANCELLED`. Calling `resume()` after cancellation raises `WorkflowCancelledError`.

## Full Pause/Resume Example

```python
import asyncio
from syrin import Agent, Budget, Model
from syrin.enums import PauseMode
from syrin.workflow import Workflow

class StepA(Agent):
    model = Model.mock()

class StepB(Agent):
    model = Model.mock()

class StepC(Agent):
    model = Model.mock()

async def main():
    wf = (
        Workflow("demo", budget=Budget(max_cost=1.00))
        .step(StepA)
        .step(StepB)
        .step(StepC)
    )
    handle = wf.play("Run the pipeline")

    await asyncio.sleep(0.1)         # Let StepA start
    await wf.pause(PauseMode.DRAIN)  # Wait for StepA to finish cleanly
    print(handle.status)             # WorkflowStatus.PAUSED
    print(handle.step_index)         # 0 (StepA completed)

    await wf.resume()                # Continue with StepB and StepC
    result = await handle.wait()
    print(result.content)

asyncio.run(main())
```

## Checkpoint Backend — Cross-Process Resume

If your process crashes mid-workflow, you lose everything unless you've configured a checkpoint backend. With one configured, every completed step is saved and can be resumed in a fresh process.

**Process 1 — Start:**

```python
from syrin.checkpoint import SQLiteCheckpointBackend
from syrin.workflow import Workflow

backend = SQLiteCheckpointBackend(path="workflow.db")
wf = Workflow("long-pipeline", checkpoint_backend=backend)
wf.step(StepA).step(StepB).step(StepC)

handle = wf.play("Run the pipeline")
print(f"Run ID: {handle.run_id}")  # Save this value — you'll need it to resume
```

If the process crashes after StepA completes, the checkpoint is already saved. Nothing is lost.

**Process 2 — Resume:**

```python
from syrin.checkpoint import SQLiteCheckpointBackend
from syrin.workflow import Workflow

backend = SQLiteCheckpointBackend(path="workflow.db")
wf = Workflow(
    "long-pipeline",
    checkpoint_backend=backend,
    resume_run_id="run-4f7a3b2c1d0e",  # The ID from Process 1
)
wf.step(StepA).step(StepB).step(StepC)

result = await wf.run("Run the pipeline")
# StepA is skipped — its output is loaded from the checkpoint
# Execution resumes at StepB
```

Four checkpoint backends are available. `MemoryCheckpointBackend` is in-process only (ephemeral — useful for testing). `SQLiteCheckpointBackend` writes to a single file and needs no server. `FilesystemCheckpointBackend` writes each checkpoint as a JSON file. `PostgresCheckpointBackend` is for production and requires `psycopg2`.

Any object implementing the `CheckpointBackendProtocol` (`.save()` and `.load()` methods) also works as a custom backend.

## Swarm Lifecycle

`Swarm` uses the same lifecycle API:

```python
from syrin.swarm import Swarm, SwarmConfig
from syrin.enums import SwarmTopology

swarm = Swarm(agents=[...], goal="...")

handle = swarm.play()
await swarm.pause()
await swarm.resume()
await swarm.cancel()

result = await handle.wait()  # Returns SwarmResult
```

You can also stop a single agent without affecting the rest of the swarm:

```python
await swarm.cancel_agent("AgentName")
```

## Lifecycle States

A workflow or swarm starts in `RUNNING`. It moves to `PAUSED` when you call `pause()`, back to `RUNNING` when you call `resume()`, and finally to one of three terminal states: `COMPLETED` (all steps finished), `FAILED` (unhandled exception), or `CANCELLED` (you called `cancel()`).

## Hooks

Subscribe to lifecycle transitions with these hooks from `syrin.enums.Hook`:

- `Hook.WORKFLOW_STARTED` fires when `run()` or `play()` is called
- `Hook.WORKFLOW_PAUSED` fires after the pause takes effect
- `Hook.WORKFLOW_RESUMED` fires after the resume takes effect
- `Hook.WORKFLOW_COMPLETED` fires when all steps finish successfully
- `Hook.WORKFLOW_FAILED` fires on an unhandled exception in a step
- `Hook.WORKFLOW_CANCELLED` fires when `cancel()` is called

## See Also

- [Workflow](/multi-agent/workflow) — Step types and builder pattern
- [Visualization](/multi-agent/visualization) — Visualize workflow state
- [Swarm](/multi-agent/swarm) — Parallel, consensus, and reflection topologies
