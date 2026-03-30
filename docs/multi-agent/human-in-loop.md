---
title: Human in the Loop
description: Add human approval gates for safety-critical tool execution
weight: 96
---

## Sometimes AI Needs a Second Pair of Eyes

Your agent just decided to delete all customer records. In production. That's a problem.

AI agents are powerful, but certain actions—deleting data, sending emails, approving payments—require human judgment. Not because AI is incompetent, but because some decisions have consequences that warrant human oversight.

Human in the Loop (HITL) bridges this gap. Your agent pauses before dangerous operations, requests approval, and proceeds only when a human signs off.

## The Problem

Tool-calling agents can execute actions autonomously. But real systems need safeguards:

- **Deleting data**: One wrong ID and data is gone
- **Sending emails**: Irreversible communication to users
- **Financial transactions**: Money movements need authorization
- **System changes**: Infrastructure modifications affect everyone

You could restrict tools entirely, but then you lose automation for safe operations. Or you could auto-approve everything, which is risky. What you need is nuanced control.

## The Solution

HITL pauses agent execution to request human approval before each tool runs:

```python
from syrin import Agent, ApprovalGate, Hook, Model, tool

model = Model.OpenAI("gpt-4o", api_key="your-api-key")


@tool(description="Delete a record by ID")
def delete_record(id: str) -> str:
    return f"Deleted record {id}"


def approve_callback(msg: str, timeout: int, ctx: dict) -> bool:
    print(f"Approval requested: {msg}")
    return input("Approve? [y/n]: ").lower() == "y"


agent = Agent(
    model=model,
    system_prompt="Use delete_record when asked to delete records.",
    tools=[delete_record],
    approval_gate=ApprovalGate(callback=approve_callback),
)

result = agent.run("Delete record abc123")
# Pauses here, waits for approval
# Only executes if approved
```

**What just happened**: The agent wanted to call `delete_record`, but HITL intercepted the request. Your callback received the approval request. If you approved, the tool executed. If not, the agent tried a different approach.

## Approval Gates

Syrin provides `ApprovalGate` for callback-based approval. But you can implement `ApprovalGateProtocol` for any workflow:

### Callback Gate

Sync or async callbacks for simple integration:

```python
from syrin import ApprovalGate, HumanInTheLoop

gate = ApprovalGate(callback=my_approval_function)
agent = Agent(
    model=model,
    approval_gate=gate,
    custom_loop=HumanInTheLoop(approval_gate=gate),
)
```

### Slack Integration

Implement the protocol to post to Slack:

```python
import asyncio
from syrin.hitl import ApprovalGateProtocol


class SlackApprovalGate(ApprovalGateProtocol):
    async def request(self, message: str, timeout: int, context: dict) -> bool:
        slack_msg = f"🤖 *Approval Request*\n{message}"
        await slack_client.chat_post(channel="#approvals", text=slack_msg)
        
        result = await wait_for_slack_reaction(channel_id, timeout=timeout)
        return result == "white_check_mark"
```

### Webhook Gate

Forward to an external approval system:

```python
class WebhookApprovalGate(ApprovalGateProtocol):
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def request(self, message: str, timeout: int, context: dict) -> bool:
        response = await http_client.post(
            self.webhook_url,
            json={"message": message, "context": context, "timeout": timeout},
        )
        approval_id = response.json()["approval_id"]
        return await poll_for_result(approval_id, timeout=timeout)
```

## Per-Tool Control

Mark individual tools as requiring approval while others run freely:

```python
from syrin import Agent, ApprovalGate, Model, tool

model = Model.OpenAI("gpt-4o", api_key="your-api-key")


@tool(requires_approval=True, description="Delete a record by ID")
def delete_record(id: str) -> str:
    return f"Deleted record {id}"


@tool(description="Search for records")  # No approval needed
def search(query: str) -> str:
    return f"Results for: {query}"


gate = ApprovalGate(callback=lambda msg, timeout, ctx: input("Approve? ") == "y")


class HITLAgent(Agent):
    model = model
    system_prompt = "Use delete_record to delete, search to find."
    tools = [delete_record, search]
    approval_gate = gate
    human_approval_timeout = 60


agent = HITLAgent()

# search runs automatically
agent.run("Search for customer records")

# delete_record pauses for approval
agent.run("Delete record abc123")
```

**What just happened**: `search` executes without pausing. `delete_record` triggers the approval gate. Only tools with `requires_approval=True` pause.

## Hooks and Observability

HITL emits lifecycle hooks for monitoring approvals:

| Hook | When | Context |
|------|------|---------|
| `HITL_PENDING` | Before approval request | `name`, `arguments`, `message`, `iteration` |
| `HITL_APPROVED` | After approval granted | `name`, `arguments`, `approved`, `iteration` |
| `HITL_REJECTED` | After approval denied | `name`, `arguments`, `approved`, `iteration` |

### Monitoring Approvals

```python
from syrin import Agent, ApprovalGate, Hook, Model

model = Model.OpenAI("gpt-4o", api_key="your-api-key")


class MonitoredAgent(Agent):
    model = model
    approval_gate = ApprovalGate(callback=lambda msg, t, ctx: True)


agent = MonitoredAgent()


def on_pending(ctx):
    print(f"⏳ Awaiting approval: {ctx.name}")
    print(f"   Arguments: {ctx.arguments}")


def on_approved(ctx):
    print(f"✅ Approved: {ctx.name}")


def on_rejected(ctx):
    print(f"❌ Rejected: {ctx.name}")


agent.events.on(Hook.HITL_PENDING, on_pending)
agent.events.on(Hook.HITL_APPROVED, on_approved)
agent.events.on(Hook.HITL_REJECTED, on_rejected)

agent.run("Execute sensitive operation")
```

### Audit Trail

Send approvals to your logging system:

```python
import structlog

logger = structlog.get_logger()


def audit_approval(ctx):
    logger.info(
        "tool_approved",
        tool=ctx.name,
        arguments=ctx.arguments,
        iteration=ctx.iteration,
        user="human_approver",  # Track who approved
    )


def audit_rejection(ctx):
    logger.warning(
        "tool_rejected",
        tool=ctx.name,
        arguments=ctx.arguments,
        iteration=ctx.iteration,
    )


agent.events.on(Hook.HITL_APPROVED, audit_approval)
agent.events.on(Hook.HITL_REJECTED, audit_rejection)
```

## Configuration Options

### HumanInTheLoop Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `approval_gate` | `ApprovalGateProtocol` | Required | Approval backend |
| `approve` | `Callable` | None | Legacy: async callback (tool_name, args) -> bool |
| `timeout` | `int` | 300 | Seconds to wait for approval |
| `max_iterations` | `int` | 10 | Maximum tool-call loops |

### Agent Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `approval_gate` | `ApprovalGateProtocol` | None | Gate for HITL loop |
| `human_approval_timeout` | `int` | 300 | Per-call timeout override |

## Timeout Handling

When approval times out, the tool call is rejected:

```python
from syrin import ApprovalGate, Model
import asyncio


async def slow_approval(msg: str, timeout: int, ctx: dict) -> bool:
    # Simulate slow approval process
    await asyncio.sleep(timeout + 1)  # Exceeds timeout
    return True


gate = ApprovalGate(callback=slow_approval)

agent = Agent(
    model=model,
    approval_gate=gate,
    human_approval_timeout=5,  # 5 second timeout
)

result = agent.run("Delete record abc123")
# Times out after 5 seconds, tool call rejected
# Agent tries alternative approach or reports failure
```

**What just happened**: The approval callback took too long. The agent treated it as a rejection and continued with the next iteration or returned the rejection message.

## Retry and Recovery

When rejected, the agent can retry with different arguments or give up:

```python
from syrin import Agent, ApprovalGate, Hook, Model

model = Model.OpenAI("gpt-4o", api_key="your-api-key")


class RetryAgent(Agent):
    model = model
    approval_gate = ApprovalGate(callback=lambda msg, t, ctx: False)  # Always reject


agent = RetryAgent()
result = agent.run("Delete record abc123")

print(result.content)
# "I cannot proceed with deleting record abc123 as approval was not granted."
# Agent respected the rejection and informed the user
```

## See Also

- [Loop Strategies](/agent-kit/agent/running-agents) — All loop modes including HITL
- [Pipeline](/agent-kit/multi-agent/pipeline) — Sequential agent execution
- [Dynamic Pipeline](/agent-kit/multi-agent/dynamic-pipeline) — LLM-driven routing
- [Hooks Reference](/agent-kit/debugging/hooks) — Complete hook lifecycle
