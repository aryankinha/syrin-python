---
title: Agent Handoff
description: Transfer control between specialized agents with context preservation
weight: 95
---

## Sometimes One Agent Isn't Enough

Imagine a customer support system. A triage agent quickly categorizes incoming tickets, but customers need detailed technical help—not just categorization. You could have the triage agent do both, but that's not efficient. The triage agent is optimized for classification, not deep technical explanations.

The solution: **agent handoff**. One agent handles what it's best at, then transfers control to another agent with all the relevant context.

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

## The Solution

Handoff lets one agent transfer control to another, optionally passing along:
- **Memory context**: What the first agent learned
- **Budget**: Whether the second agent shares the same spending limit

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
    # Transfer to technical support with full context
    help_result = triage.handoff(
        TechnicalSupportAgent,
        "Customer issue: application crashes on file upload"
    )
```

**What just happened**: The triage agent classified the issue, then handed off to technical support. The second agent receives the task with context about what the first agent determined.

## Transfer Options

### Transfer Context

By default, handoff copies memories from the source agent to the target:

```python
result = source.handoff(TargetAgent, task, transfer_context=True)  # Default
```

This means:
- The target agent can `remember()` and `recall()` what the source learned
- Memories are copied at handoff time (not shared references)
- Target gets up to 10 most relevant memories

If the source has no memory backend, a warning logs but handoff continues:

```python
# Source has no memory configured — handoff works but no context transferred
source = Agent(model=model, system_prompt="Analyzer")  # No Memory() here
result = source.handoff(TargetAgent, "process this")
```

### Transfer Budget

By default, budget stays with the source agent. Set `transfer_budget=True` to share it:

```python
# Target draws from same budget as source
result = source.handoff(
    TargetAgent,
    "expensive task",
    transfer_budget=True  # Shares budget tracker
)
```

This is useful when you want one budget controlling the entire workflow.

## Hooks and Observability

Handoff emits lifecycle hooks for full observability:

| Hook | When | Key Context |
|------|------|-------------|
| `HANDOFF_START` | Before transfer begins | `source_agent`, `target_agent`, `task`, `mem_count`, `transfer_budget` |
| `HANDOFF_END` | After target completes | `cost`, `duration`, `response_preview` |
| `HANDOFF_BLOCKED` | When blocked | `reason` |

### Observing Handoffs

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


def log_handoff_start(ctx):
    print(f"Starting handoff: {ctx.source_agent} -> {ctx.target_agent}")
    print(f"  Task: {ctx.task[:50]}...")
    print(f"  Memories transferred: {ctx.mem_count}")
    print(f"  Budget shared: {ctx.transfer_budget}")


def log_handoff_end(ctx):
    print(f"Handoff complete: ${ctx.cost:.4f} in {ctx.duration:.2f}s")
    print(f"  Preview: {ctx.response_preview[:80]}...")


researcher.events.on(Hook.HANDOFF_START, log_handoff_start)
researcher.events.on(Hook.HANDOFF_END, log_handoff_end)


result = researcher.handoff(Writer, "Summarize: benefits of renewable energy")
```

**What just happened**: Every handoff is logged with timing, cost, and content preview. You can ship this to your observability platform.

### Context Snapshot

`HANDOFF_START` includes a `handoff_context` snapshot showing context state at transfer time:

```python
def inspect_context(ctx):
    snapshot = ctx.handoff_context
    print(f"Context tokens: {snapshot.total_tokens}")
    print(f"Utilization: {snapshot.utilization_pct:.1f}%")
    print(f"Rotation risk: {snapshot.context_rot_risk}")
    # Export for audit trail
    audit_data = snapshot.to_dict()

researcher.events.on(Hook.HANDOFF_START, inspect_context)
```

This helps you monitor context pressure during handoffs.

## Blocking Handoffs

Sometimes you need to validate handoffs before they occur. Use `HandoffBlockedError` in a before-handler:

```python
from syrin import Agent, HandoffBlockedError, Hook, Model

model = Model.OpenAI("gpt-4o", api_key="your-api-key")


class RequestHandler(Agent):
    model = model
    system_prompt = "You handle user requests."


class AdminAgent(Agent):
    model = model
    system_prompt = "You perform administrative tasks."


handler = RequestHandler()


def log_blocked(ctx):
    print(f"Handoff blocked: {ctx.reason}")

handler.events.on(Hook.HANDOFF_BLOCKED, log_blocked)


@handler.events.before(Hook.HANDOFF_START)
def validate_handoff(ctx):
    # Block handoffs to admin for non-admin users
    if ctx.target_agent == "AdminAgent" and not is_admin_user():
        raise HandoffBlockedError(
            "Unauthorized admin handoff",
            ctx.source_agent,
            ctx.target_agent,
            ctx.task,
        )


def is_admin_user() -> bool:
    return False  # Your auth logic here


# This will be blocked
try:
    result = handler.handoff(AdminAgent, "delete all records")
except HandoffBlockedError as e:
    print(f"Caught: {e}")
```

**What just happened**: The before-handler validates the handoff. If it raises `HandoffBlockedError`, the transfer is aborted and `HANDOFF_BLOCKED` emits.

## Retry Pattern

The target agent can request a retry with format hints:

```python
from syrin import Agent, HandoffRetryRequested, Model, Response
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
            raise HandoffRetryRequested(
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
        result = collector.handoff(DataProcessor, task)
        print(f"Success on attempt {attempt + 1}")
        break
    except HandoffRetryRequested as e:
        print(f"Retry requested: {e.format_hint}")
        task = '{"title": "Report", "items": ["a", "b"]}'  # Fixed format
```

**What just happened**: The source agent retries with formatted data after the target rejects plain text.

## Parameter Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `target_agent` | `type[Agent]` | Required | Agent class to transfer control to |
| `task` | `str` | Required | Task description for the target |
| `transfer_context` | `bool` | `True` | Copy memories to target |
| `transfer_budget` | `bool` | `False` | Share budget with target |

## Exception Reference

| Exception | When Raised |
|-----------|-------------|
| `HandoffBlockedError` | Before-handler blocks the transfer |
| `HandoffRetryRequested` | Target requests retry with format hint |
| `ValidationError` | Invalid target_agent or empty task |

## See Also

- [Dynamic Pipeline](/agent-kit/multi-agent/dynamic-pipeline) — LLM decides which agents to spawn
- [Pipeline](/agent-kit/multi-agent/pipeline) — Sequential and parallel agent execution
- [Spawn](/agent-kit/multi-agent/handoff) — Create child agents with shared budget
- [Hooks Reference](/agent-kit/debugging/hooks) — Complete hook lifecycle documentation
