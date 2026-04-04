---
title: Custom Observability
description: Build custom hook handlers, tracing exporters, and audit sinks for any observability stack
weight: 230
---

## Why Custom Observability?

Syrin ships with Console, JSONL, OTLP, Langfuse, and Phoenix exporters out of the box. But if your company runs an internal APM, a proprietary audit system, or a specialized cost tracking database — you need to plug in your own backend.

Syrin gives you three extension points. A **custom hook handler** subscribes to lifecycle events — use this when you want to react to agent behavior, send alerts, write logs, or modify context. A **custom span exporter** implements the `SpanExporter` protocol — use this when you want traces in your own backend. A **custom audit sink** implements the `AuditSink` protocol — use this when you need immutable audit logs for compliance.

---

## Custom Hook Handlers

Hooks are the lowest-level observability primitive. Every lifecycle moment — LLM request, tool call, budget threshold, memory operation — fires a hook with full context.

### Subscribing to Hooks

```python
from syrin import Agent, Model
from syrin.enums import Hook

agent = Agent(model=Model.OpenAI("gpt-4o-mini", api_key="..."))


def on_llm_end(ctx):
    # ctx has: model, tokens, cost, budget_spent, duration_ms, response
    print(f"Model: {ctx.model}  Tokens: {ctx.tokens}  Cost: ${ctx.cost:.6f}")


def on_tool_call(ctx):
    # ctx has: tool_name, tool_input, tool_output, duration_ms
    print(f"Tool called: {ctx.tool_name}")


agent.events.on(Hook.LLM_REQUEST_END, on_llm_end)
agent.events.on(Hook.TOOL_CALL_END, on_tool_call)
```

### Modifying Context Before Calls

`before` hooks fire before the operation and can modify the context:

```python
agent.events.before(Hook.LLM_REQUEST_START, lambda ctx: ctx.update({
    "custom_metadata": {"request_id": generate_request_id()}
}))
```

### Reusable Hook Handler Class

For production systems, encapsulate your observability logic in a class:

```python
from syrin.enums import Hook


class DatadogObservabilityHandler:
    """Sends agent metrics to Datadog via statsd."""

    def __init__(self, statsd_client):
        self.statsd = statsd_client

    def attach(self, agent):
        agent.events.on(Hook.LLM_REQUEST_END, self._on_llm_end)
        agent.events.on(Hook.TOOL_CALL_END, self._on_tool_end)
        agent.events.on(Hook.BUDGET_THRESHOLD, self._on_budget_threshold)
        agent.events.on(Hook.AGENT_RUN_END, self._on_run_end)
        return agent

    def _on_llm_end(self, ctx):
        tags = [f"model:{ctx.model}"]
        self.statsd.increment("syrin.llm.calls", tags=tags)
        self.statsd.gauge("syrin.llm.cost", ctx.cost, tags=tags)
        self.statsd.histogram("syrin.llm.tokens", ctx.tokens, tags=tags)

    def _on_tool_end(self, ctx):
        self.statsd.increment("syrin.tool.calls", tags=[f"tool:{ctx.tool_name}"])
        self.statsd.histogram("syrin.tool.duration_ms", ctx.duration_ms)

    def _on_budget_threshold(self, ctx):
        self.statsd.gauge("syrin.budget.pct_used", ctx.percentage)

    def _on_run_end(self, ctx):
        self.statsd.increment("syrin.agent.runs")
        self.statsd.histogram("syrin.agent.run_cost", ctx.cost)


# Attach to any agent
handler = DatadogObservabilityHandler(statsd)
handler.attach(agent)
```

### Async Hook Handlers

If your handler does I/O (HTTP calls, DB writes), make it async:

```python
import asyncio

async def async_audit_hook(ctx):
    await db.insert("audit_log", {
        "event": "llm_call",
        "model": ctx.model,
        "cost": ctx.cost,
        "timestamp": ctx.timestamp,
    })

agent.events.on(Hook.LLM_REQUEST_END, async_audit_hook)
```

> Syrin handles the async dispatch — your handler is awaited in the same event loop as the agent.

---

## Custom Span Exporters

Hooks give you event-level access. Span exporters give you structured trace data — the complete call tree with timing, cost, and attributes.

### SpanExporter Protocol

```python
from syrin.observability import SpanExporter, Span

class SpanExporter(Protocol):
    def export(self, span: Span) -> None:
        """Called once per completed span."""
        ...

    def shutdown(self) -> None:
        """Flush buffers when the process is shutting down."""
        ...
```

### Example: Internal APM

```python
import json
import urllib.request
from syrin.observability import SpanExporter, Span, trace


class InternalAPMExporter(SpanExporter):
    def __init__(self, endpoint: str, api_key: str) -> None:
        self.endpoint = endpoint
        self.api_key = api_key

    def export(self, span: Span) -> None:
        payload = json.dumps({
            "name": span.name,
            "trace_id": span.trace_id,
            "duration_ms": span.duration_ms,
            "status": span.status,
            "model": span.attributes.get("llm.model"),
            "cost": span.attributes.get("llm.cost"),
            "tokens": span.attributes.get("llm.tokens.total"),
            "timestamp": span.start_time.isoformat(),
        }).encode()

        req = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        try:
            urllib.request.urlopen(req, timeout=2)
        except Exception:
            pass  # Export failures must not crash the agent


    def shutdown(self) -> None:
        pass


trace.add_exporter(InternalAPMExporter(
    endpoint="https://apm.internal/v1/spans",
    api_key="your-key",
))
```

### Example: Cost Tracking Database

If you're tracking per-user or per-project spend, push LLM spans into your database:

```python
from syrin.observability import SpanExporter, Span, SpanKind


class CostTrackingExporter(SpanExporter):
    def __init__(self, db, project_id: str) -> None:
        self.db = db
        self.project_id = project_id

    def export(self, span: Span) -> None:
        # Only record LLM spans — they're the ones with cost
        if span.kind != SpanKind.LLM:
            return

        cost = span.attributes.get("llm.cost", 0.0)
        if cost == 0.0:
            return

        self.db.execute(
            """
            INSERT INTO llm_spend
                (project_id, trace_id, model, cost_usd, tokens_in, tokens_out, ts)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.project_id,
                span.trace_id,
                span.attributes.get("llm.model"),
                cost,
                span.attributes.get("llm.tokens.input", 0),
                span.attributes.get("llm.tokens.output", 0),
                span.start_time,
            ),
        )

    def shutdown(self) -> None:
        self.db.commit()
```

> **Keep `export()` fast.** It's called synchronously on the hot path. For slow backends (HTTP, DB writes), use a background queue or `BatchingExporter` (see [Tracing Exporters](/agent-kit/debugging/tracing-exporters)).

---

## Custom Audit Sink

The `AuditLog` records every agent action that touches external systems — LLM calls, tool executions, memory writes, handoffs. Unlike spans (which are for debugging), audit records are designed for compliance, replay, and accountability.

### AuditSink Protocol

```python
from syrin.audit import AuditSink, AuditRecord

class AuditSink(Protocol):
    def write(self, record: AuditRecord) -> None:
        """Write an immutable audit record."""
        ...
```

`AuditRecord` has nine fields. `event_type` (str) is one of `"llm_call"`, `"tool_call"`, `"memory_write"`, or `"handoff"`. `agent_id` (str) identifies which agent produced the record. `session_id` (str or None) provides session context. `timestamp` (datetime) records when the event occurred. `input` (dict) holds what was sent — the prompt or tool arguments. `output` (dict) holds what was returned — the response or tool result. `cost_usd` (float) is the cost in USD. `model` (str or None) is the model used, if applicable. `metadata` (dict) holds any extra context you want to attach.

### Example: Append-Only Compliance Log

```python
import json
from pathlib import Path
from syrin.audit import AuditSink, AuditRecord


class ComplianceAuditSink(AuditSink):
    """Append-only JSONL audit log for compliance."""

    def __init__(self, filepath: str) -> None:
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: AuditRecord) -> None:
        line = json.dumps({
            "event_type": record.event_type,
            "agent_id": record.agent_id,
            "session_id": record.session_id,
            "timestamp": record.timestamp.isoformat(),
            "input": record.input,
            "output": record.output,
            "cost_usd": record.cost_usd,
            "model": record.model,
            "metadata": record.metadata,
        })
        with open(self.filepath, "a") as f:
            f.write(line + "\n")
```

### Attaching a Custom Audit Sink

```python
from syrin import Agent, Model
from syrin.audit import AuditLog

audit_log = AuditLog(sink=ComplianceAuditSink("audit/agent_actions.jsonl"))

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="..."),
    audit_log=audit_log,
)

result = agent.run("Draft the contract for ACME Corp")
# Every LLM call, tool use, and memory write is now in audit/agent_actions.jsonl
```

---

## Putting It Together: Full Custom Stack

Here's a production pattern that combines all three extension points:

```python
from syrin import Agent, Budget, Model
from syrin.audit import AuditLog
from syrin.enums import ExceedPolicy, Hook
from syrin.observability import trace

# 1. Span exporter → internal APM
trace.add_exporter(InternalAPMExporter(
    endpoint="https://apm.internal/v1/spans",
    api_key=APM_API_KEY,
))

# 2. Audit sink → compliance database
audit_log = AuditLog(sink=ComplianceAuditSink("audit/production.jsonl"))

# 3. Agent with budget and compliance logging
agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key=OPENAI_KEY),
    budget=Budget(max_cost=5.00, exceed_policy=ExceedPolicy.STOP),
    audit_log=audit_log,
    session_id=f"user:{user_id}",
)

# 4. Hook handler → Datadog metrics
DatadogObservabilityHandler(statsd).attach(agent)

# Now every run is fully observable:
# - Spans go to your internal APM
# - Metrics go to Datadog
# - Audit records go to your compliance JSONL
result = agent.run(user_message)
```

---

## Additional Observability and Audit Exports

The public observability and audit surface also includes:

- `SpanStatus` when you need to set success/error state explicitly on spans.
- `AuditEvent`, `AuditHookHandler`, and `JsonlAuditBackend` for lower-level audit pipelines.

## What's Next?

- [Custom Model](/agent-kit/advanced/custom-model) — Implement your own LLM provider
- [Custom Context](/agent-kit/advanced/custom-context) — Control what gets sent to the model
- [Tracing Exporters](/agent-kit/debugging/tracing-exporters) — Built-in exporters + batching patterns
- [Hooks Reference](/agent-kit/debugging/hooks-reference) — All 72+ hook events with context fields
