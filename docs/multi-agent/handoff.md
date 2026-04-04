---
title: Agent Spawn (Task Delegation)
description: Delegate tasks to specialized agents with context and budget control
weight: 95
---

## Sometimes One Agent Isn't Enough

Imagine a customer support system. A triage agent quickly categorizes incoming tickets, but customers need detailed technical help—not just categorization. You could have the triage agent do both, but that's not efficient. The triage agent is optimized for classification, not deep technical explanations.

The solution: **spawn a specialist**. One agent handles what it's best at, then delegates to another agent with all the relevant context.

## The Problem

Agents excel at specific tasks. But real-world workflows often require different skills at different stages:

- **Triage → Specialist**: Route to the right expert
- **Researcher → Writer**: Convert findings into polished content
- **Analyzer → Presenter**: Transform data into clear explanations
- **Collector → Validator → Formatter**: Multi-stage data processing

You could build one monolithic agent with all capabilities, but that leads to:
- Higher costs (bigger prompts, more tokens)
- Lower quality (jack of all trades, master of none)
- Harder maintenance (everything coupled together)

## The Solution: `spawn()`

`spawn()` creates a child agent and delegates a task to it, optionally passing along:
- **Memory context**: What the parent agent learned
- **Budget**: Whether the child agent shares the same spending limit

```python
from syrin import Agent, Model

model = Model.OpenAI("gpt-4o", api_key="your-api-key")


class TriageAgent(Agent):
    model = model
    system_prompt = "You classify customer issues as: billing, technical, or general."


class TechnicalSupportAgent(Agent):
    model = model
    system_prompt = "You provide detailed technical troubleshooting help."


triage = TriageAgent()
result = triage.run("My application keeps crashing when I upload files")

if "technical" in result.content.lower():
    # Delegate to technical support with full context
    help_result = triage.spawn(
        TechnicalSupportAgent,
        "Customer issue: application crashes on file upload"
    )
```

**What just happened**: The triage agent classified the issue, then spawned a technical support agent to handle the detailed work. The child agent receives the task with context about what the parent determined.

## Transfer Options

### Transfer Context

By default, `spawn()` copies memories from the parent agent to the child:

```python
result = source.spawn(TargetAgent, task, transfer_context=True)  # Default
```

This means:
- The child agent can `remember()` and `recall()` what the parent learned
- Memories are copied at spawn time (not shared references)
- Child gets up to 10 most relevant memories

If the parent has no memory backend, a warning logs but `spawn()` continues:

```python
# Parent has no memory configured — spawn works but no context transferred
source = Agent(model=model, system_prompt="Analyzer")  # No Memory() here
result = source.spawn(TargetAgent, "process this")
```

### Transfer Budget

By default, budget stays with the parent agent. Set `transfer_budget=True` to share it:

```python
# Child draws from same budget as parent
result = source.spawn(
    TargetAgent,
    "expensive task",
    transfer_budget=True  # Shares budget tracker
)
```

This is useful when you want one budget controlling the entire workflow.

## Hooks and Observability

`spawn()` emits three lifecycle hooks. `SPAWN_START` fires before the child agent is created — context includes `source_agent`, `target_agent`, `task`, `mem_count`, and `transfer_budget`. `SPAWN_END` fires after the child completes — context includes `cost`, `duration`, and `response_preview`. `SPAWN_BLOCKED` fires when a before-handler blocks the spawn — context includes `reason`.

### Observing Spawns

```python
from syrin import Agent, Hook, Model

model = Model.OpenAI("gpt-4o", api_key="your-api-key")


class Researcher(Agent):
    model = model
    system_prompt = "You research topics and provide findings."


class Writer(Agent):
    model = model
    system_prompt = "You write clear summaries."


researcher = Researcher()


def log_spawn_start(ctx):
    print(f"Spawning: {ctx.source_agent} -> {ctx.target_agent}")
    print(f"  Task: {ctx.task[:50]}...")
    print(f"  Memories transferred: {ctx.mem_count}")
    print(f"  Budget shared: {ctx.transfer_budget}")


def log_spawn_end(ctx):
    print(f"Spawn complete: ${ctx.cost:.4f} in {ctx.duration:.2f}s")
    print(f"  Preview: {ctx.response_preview[:80]}...")


researcher.events.on(Hook.SPAWN_START, log_spawn_start)
researcher.events.on(Hook.SPAWN_END, log_spawn_end)


result = researcher.spawn(Writer, "Summarize: benefits of renewable energy")
```

**What just happened**: Every spawn is logged with timing, cost, and content preview. You can ship this to your observability platform.

### Context Snapshot

`SPAWN_START` includes a `spawn_context` snapshot showing context state at delegation time:

```python
def inspect_context(ctx):
    snapshot = ctx.spawn_context
    print(f"Context tokens: {snapshot.total_tokens}")
    print(f"Utilization: {snapshot.utilization_pct:.1f}%")
    print(f"Rotation risk: {snapshot.context_rot_risk}")
    # Export for audit trail
    audit_data = snapshot.to_dict()

researcher.events.on(Hook.SPAWN_START, inspect_context)
```

This helps you monitor context pressure during delegation.

## Blocking Spawns

Sometimes you need to validate spawns before they occur. Use `SpawnBlockedError` in a before-handler:

```python
from syrin import Agent, SpawnBlockedError, Hook, Model

model = Model.OpenAI("gpt-4o", api_key="your-api-key")


class RequestHandler(Agent):
    model = model
    system_prompt = "You handle user requests."


class AdminAgent(Agent):
    model = model
    system_prompt = "You perform administrative tasks."


handler = RequestHandler()


def log_blocked(ctx):
    print(f"Spawn blocked: {ctx.reason}")

handler.events.on(Hook.SPAWN_BLOCKED, log_blocked)


@handler.events.before(Hook.SPAWN_START)
def validate_spawn(ctx):
    # Block spawns to admin for non-admin users
    if ctx.target_agent == "AdminAgent" and not is_admin_user():
        raise SpawnBlockedError(
            "Unauthorized admin spawn",
            ctx.source_agent,
            ctx.target_agent,
            ctx.task,
        )


def is_admin_user() -> bool:
    return False  # Your auth logic here


# This will be blocked
try:
    result = handler.spawn(AdminAgent, "delete all records")
except SpawnBlockedError as e:
    print(f"Caught: {e}")
```

**What just happened**: The before-handler validates the spawn. If it raises `SpawnBlockedError`, the delegation is aborted and `SPAWN_BLOCKED` emits.

## Retry Pattern

The child agent can request a retry with format hints:

```python
from syrin import Agent, SpawnRetryRequested, Model, Response
from syrin.types import TokenUsage

model = Model.OpenAI("gpt-4o", api_key="your-api-key")


class DataCollector(Agent):
    model = model
    system_prompt = "You collect data in any format."


class DataProcessor(Agent):
    model = model
    system_prompt = "You expect structured JSON data."

    _retry_count = 0

    def response(self, user_input: str, **kwargs):
        self._retry_count += 1
        if self._retry_count == 1:
            # First attempt: reject plain text
            raise SpawnRetryRequested(
                "Invalid format",
                format_hint='{"title": "string", "items": ["array"]}',
            )
        return Response(
            content=f"Processed: {user_input[:50]}...",
            cost=0.001,
            tokens=TokenUsage(10, 20, 30),
        )


collector = DataCollector()

task = "plain text data"
for attempt in range(3):
    try:
        result = collector.spawn(DataProcessor, task)
        print(f"Success on attempt {attempt + 1}")
        break
    except SpawnRetryRequested as e:
        print(f"Retry requested: {e.format_hint}")
        task = '{"title": "Report", "items": ["a", "b"]}'  # Fixed format
```

**What just happened**: The parent agent retries with formatted data after the child rejects plain text.

## Parameter Reference

Four parameters control a spawn. `target_agent` (type[Agent], required) is the agent class to delegate to. `task` (str, required) is the task description for the child. `transfer_context` (bool, default `True`) copies memories from the parent to the child at spawn time. `transfer_budget` (bool, default `False`) shares the budget tracker with the child.

## Exception Reference

Three exceptions can be raised. `SpawnBlockedError` is raised when a before-handler explicitly blocks the spawn. `SpawnRetryRequested` is raised by the child agent when it wants the parent to retry with a different format. `ValidationError` is raised when `target_agent` is invalid or `task` is empty.

## See Also

- [Dynamic Pipeline](/agent-kit/multi-agent/dynamic-pipeline) — LLM decides which agents to spawn
- [Pipeline](/agent-kit/multi-agent/pipeline) — Sequential and parallel agent execution
- [Hooks Reference](/agent-kit/debugging/hooks) — Complete hook lifecycle documentation
