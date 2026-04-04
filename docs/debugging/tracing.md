---
title: Tracing
description: Capture every span of an agent run — for production debugging, auditing, and observability platforms
weight: 173
---

## What Is Tracing?

Every agent run is a tree of operations: memory recall, context preparation, LLM call, tool execution. Tracing captures each of those operations as a **span** — a named record with a start time, duration, status, and attributes.

When something fails in production, you don't have to reproduce it. You look at the trace and see exactly what happened, in order, with timing.

## Enabling Tracing

Tracing is always running internally. To see it, add an exporter:

```python
from syrin import Agent, Model
from syrin.observability import get_tracer, ConsoleExporter

# Print every span to the console
get_tracer().add_exporter(ConsoleExporter())

agent = Agent(model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"), system_prompt="You are helpful.")
# model = Model.mock()  # no API key needed for testing
result = agent.run("Hello!")
```

Output (color removed for readability):

```
agent: agent.response
  trace_id=0338f95d span_id=e9397da1
  duration=1194.43ms status=ok
  attributes:
    agent.name=agent
    agent.class=Agent
    input=Hello
    llm.model=almock/default
    llm.tokens.total=30
    cost.usd=$0.00004
  memory: memory.recall
    trace_id=0338f95d span_id=cb8dc975
    duration=0.01ms status=ok
    attributes:
      memory.operation=recall
      memory.results.count=0
  internal: context.prepare
    trace_id=0338f95d span_id=e49002ee
    duration=0.19ms status=ok
    attributes:
      context.max_tokens=8192
      context.tokens=13
  llm: llm.iteration_1
    trace_id=0338f95d span_id=3621196c
    duration=1185.98ms status=ok
    attributes:
      llm.model=almock/default
      llm.tokens.total=30
```

Every span shares a `trace_id` — so you can link the whole tree back to one `agent.run()` call.

## Collecting Spans in Memory

For programmatic access, use `InMemoryExporter`:

```python
from syrin import Agent, Model
from syrin.observability import get_tracer, InMemoryExporter

exporter = InMemoryExporter()
get_tracer().add_exporter(exporter)

agent = Agent(model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"), system_prompt="You are helpful.")
# model = Model.mock()  # no API key needed for testing
result = agent.run("Hello!")

print(f"Total spans: {len(exporter.spans)}")
for span in exporter.spans:
    print(f"  {span.name} — {span.duration_ms:.2f}ms — {span.status}")
    for key, val in list(span.attributes.items())[:2]:
        print(f"    {key}: {val}")
```

Output:

```
Total spans: 5
  memory.recall — 0.01ms — ok
    memory.operation: recall
    memory.kind: persistent
  memory.recall — 0.02ms — ok
    memory.operation: recall
    memory.kind: conversation
  context.prepare — 0.16ms — ok
    context.max_tokens: 8192
    context.tokens: 14
  llm.iteration_1 — 1185.98ms — ok
    llm.model: almock/default
    agent.iteration: 1
  agent.response — 1194.43ms — ok
    agent.name: agent
    cost.usd: 4.1e-05
```

## Saving Traces to JSONL

For persistent logs, use `JSONLExporter`:

```python
from syrin import Agent, Model
from syrin.observability import get_tracer, JSONLExporter

# Write every span to a file
get_tracer().add_exporter(JSONLExporter("traces.jsonl"))

agent = Agent(model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"), system_prompt="You are helpful.")
# model = Model.mock()  # no API key needed for testing
agent.run("Analyze this document for key insights")
# Spans are written to traces.jsonl as newline-delimited JSON
```

Each line in `traces.jsonl` is one span as a JSON object. Use this for:
- Long-term audit trails
- Batch analysis of many runs
- Feeding into log aggregation systems

## Span Attributes

Each span has these standard fields:

**`span.name`** — the operation name, e.g. `"agent.response"`, `"llm.iteration_1"`, `"memory.recall"`, `"context.prepare"`, `"tool.call"`.

**`span.context.trace_id`** — shared across all spans in one `agent.run()` call. Use this to group related spans.

**`span.duration_ms`** — how long the operation took in milliseconds.

**`span.status`** — `"ok"` or `"error"`.

**`span.attributes`** — a dict of key-value pairs. Common attributes:
- `agent.name` — the agent's name
- `llm.model` — model ID for LLM spans
- `llm.tokens.total` — tokens consumed
- `cost.usd` — cost in USD
- `memory.operation` — `"recall"`, `"store"`, `"forget"`
- `tool.name` — for tool spans
- `context.max_tokens`, `context.tokens` — context stats

## Multiple Exporters

You can add multiple exporters at once. Each span is sent to all of them:

```python
from syrin.observability import get_tracer, ConsoleExporter, JSONLExporter, InMemoryExporter

tracer = get_tracer()
tracer.add_exporter(ConsoleExporter())          # Dev: see in terminal
tracer.add_exporter(JSONLExporter("audit.jsonl"))  # Prod: persist to disk
tracer.add_exporter(InMemoryExporter())          # Tests: assert on spans
```

## Custom Exporters

If you use an external observability platform (Datadog, Honeycomb, Jaeger, etc.), implement the `SpanExporter` protocol:

```python
from syrin.observability import SpanExporter, Span

class DatadogExporter(SpanExporter):
    def export(self, span: Span) -> None:
        # Send span to Datadog
        dd_trace_api.record(
            name=span.name,
            trace_id=span.context.trace_id,
            duration=span.duration_ms,
            attributes=dict(span.attributes),
        )

from syrin.observability import get_tracer
get_tracer().add_exporter(DatadogExporter())
```

## Hooks vs. Tracing

Both hooks and tracing give you visibility into agent execution, but they serve different purposes.

**Hooks** run during execution, in the same thread as the agent. Use hooks when you need to react in real time — alerting when budget is low, stopping on a guardrail hit, routing based on a tool result. Hooks are the action layer.

**Tracing** captures the same events as structured spans, written after the fact. Use tracing when you need to reconstruct what happened after a run — debugging a production failure, auditing compliance, analyzing performance trends. Tracing is the record layer.

In practice, most production systems use both: hooks for live monitoring and reaction, tracing for persistent records.

## Debug Mode

For development, `debug=True` on the agent prints a human-readable trace to the console without any exporter setup:

```python
from syrin import Agent, Model

agent = Agent(
    model=Model.mock(),
    system_prompt="You are helpful.",
    debug=True,  # Prints every event as it fires
)
agent.run("Hello!")
```

This is the fastest way to see what's happening during development. For production observability, use exporters.

## What's Next

- [Hooks & Events](/agent-kit/debugging/hooks) — React to events during execution
- [Hooks Reference](/agent-kit/debugging/hooks-reference) — All 182 hooks with context keys
- [Logging](/agent-kit/debugging/logging) — Structured log output
