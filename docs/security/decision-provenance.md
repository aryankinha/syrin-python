---
title: Decision Provenance
description: Capture every agent decision in an auditable trail using the DECISION_MADE hook and DecisionRecord.
weight: 54
---

## Overview

Decision provenance gives you a tamper-evident record of every decision an agent makes — which action it chose, why it chose it, how confident it was, and what alternatives it considered. This is the foundation of auditable AI in regulated environments.

---

## DECISION_MADE Hook

`Hook.DECISION_MADE` fires after each agent decision is finalised — after the agent has processed the LLM response and determined its next action (tool call, handoff, final response, or stop).

```python
from syrin.enums import Hook

agent.events.on(Hook.DECISION_MADE, handle_decision)
```

The event context carries a `DecisionRecord` with the full reasoning snapshot.

---

## DecisionRecord

`DecisionRecord` carries seven fields. `reasoning_summary` is a `str` that must be at least 10 characters and is always non-empty — it is a human-readable explanation of why the decision was made, extracted from the agent's chain-of-thought or tool selection rationale; if the underlying model produces no rationale, syrin synthesises one from the action taken. `confidence` is a `float` between 0.0 and 1.0 representing the agent's self-assessed confidence, where higher values indicate stronger evidence or clearer instructions. `alternatives_considered` is a `list[str]` (possibly empty) listing other actions the agent evaluated before settling on the final decision. `decision_type` is a `str` categorising the decision as one of `"tool_call"`, `"handoff"`, `"response"`, or `"stop"`. `agent_name` is a `str` giving the class name of the agent that made the decision. `iteration` is an `int` indicating which iteration of the ReAct loop the decision occurred in. `timestamp` is an ISO-8601 UTC `str` recording when the decision was finalised.

`reasoning_summary` is guaranteed to be non-empty with at least 10 characters. If the underlying model produces no rationale, syrin synthesises a summary from the action taken.

---

## Capturing All Decisions

Subscribe to `Hook.DECISION_MADE` on every agent and log records to a database or audit backend:

```python
import asyncio
import json
from datetime import datetime, timezone
from syrin import Agent, Budget, Model
from syrin.enums import Hook

decisions: list[dict] = []

def capture_decision(ctx: dict) -> None:
    record = ctx.get("decision")
    if record is None:
        return
    decisions.append({
        "agent":       record.agent_name,
        "iteration":   record.iteration,
        "type":        record.decision_type,
        "confidence":  record.confidence,
        "reasoning":   record.reasoning_summary,
        "alternatives": record.alternatives_considered,
        "timestamp":   record.timestamp,
    })

class ResearchAgent(Agent):
    model = Model.mock()
    system_prompt = "Research the topic and report your findings."

agent = ResearchAgent()
agent.events.on(Hook.DECISION_MADE, capture_decision)

agent.run("What are the key risks of large language models?")

print(json.dumps(decisions, indent=2))
```

---

## Logging to a Database

For production audit trails, write each record asynchronously:

```python
import asyncio
from syrin.enums import Hook

async def persist_decision(ctx: dict) -> None:
    record = ctx.get("decision")
    if record is None:
        return
    await db.execute(
        """
        INSERT INTO agent_decisions
            (agent_name, iteration, decision_type, confidence,
             reasoning_summary, alternatives, recorded_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        record.agent_name,
        record.iteration,
        record.decision_type,
        record.confidence,
        record.reasoning_summary,
        json.dumps(record.alternatives_considered),
        record.timestamp,
    )

agent.events.on(Hook.DECISION_MADE, persist_decision)
```

---

## Multi-Agent Decision Trail

When using a Swarm or Workflow, attach the handler to every agent to capture the full decision trail across all agents in a run:

```python
from syrin.swarm import Swarm
from syrin.enums import Hook

def capture_decision(ctx: dict) -> None:
    record = ctx.get("decision")
    if record:
        audit_log.append(record)

swarm = Swarm(agents=[researcher, analyst, writer], goal="...")

for agent in swarm.agents:
    agent.events.on(Hook.DECISION_MADE, capture_decision)

await swarm.run()

# audit_log now contains every decision from all three agents in chronological order.
```

---

## Filtering by Confidence

Low-confidence decisions are the most important to review. Filter them from the audit trail:

```python
def flag_low_confidence(ctx: dict) -> None:
    record = ctx.get("decision")
    if record and record.confidence < 0.5:
        alert_system.send(
            f"Low-confidence decision by {record.agent_name}: "
            f"{record.reasoning_summary} (confidence={record.confidence:.2f})"
        )

agent.events.on(Hook.DECISION_MADE, flag_low_confidence)
```

---

## What's Next?

- [Hooks](/debugging/hooks) — Full hook reference
- [Pry Breakpoints](/debugging/pry-breakpoints) — Pause execution at any `DebugPoint`
- [Security: PII Guardrail](/security/pii-guardrail) — Redact PII before decisions are logged
- [Security: Agent Identity](/security/agent-identity) — Sign and verify agent messages
