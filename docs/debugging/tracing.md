---
title: Tracing
description: Understand agent execution with distributed tracing
weight: 173
---

## Something Failed in Production

Your agent worked perfectly in development. Then in production, something went wrong. A user reported wrong routing. Another got an error. But by the time you looked, the evidence was gone.

Traditional debugging relies on reproducing the issue. But AI agents are non-deterministic. The same input might work 99 times and fail once. You need to see what happened—not recreate it.

Tracing gives you that visibility. Every agent operation becomes a **span**—a record of what happened, when, and how long it took. Spans form a tree showing the complete execution path. You see not just the final output, but every decision along the way.

## The Problem

Production debugging without tracing is guesswork:

- **What happened?** You see the error, not the cause
- **Why did it happen?** The stack trace doesn't show agent decisions
- **Where did it happen?** No visibility into which tool failed
- **When did it happen?** No timeline of operations
- **Who was affected?** No correlation with user requests

You might add logging, but logs are:
- Scattered across files
- Hard to correlate
- Missing context
- Difficult to analyze at scale

## The Solution

Syrin's tracing system captures every operation as a span:

```python
from syrin import Agent, Model
from syrin.observability import trace, ConsoleExporter, get_tracer

# Add console exporter for visibility
get_tracer().add_exporter(ConsoleExporter())

agent = Agent(model=Model.Almock())
result = agent.run("Hello")
```

**Output:**
```
agent: agent.run
  trace_id=a1b2c3d4 span_id=e5f6g7h8
  duration=145.23ms status=ok
  attributes:
    agent.name=Assistant
    input=Hello
  tool: tool.search
    trace_id=a1b2c3d4 span_id=i9j0k1l2
    duration=23.45ms status=ok
    attributes:
      tool.name=search
      tool.input={"query": "Hello"}
```

**What just happened**: You see the complete execution tree. The agent span contains a tool span. You know exactly what tools were called, with what inputs, and how long each took.

## How Tracing Works

### Spans

A **span** is a record of a single operation:

```python
from syrin.observability import Span, SpanKind, SpanContext

span = Span(
    name="my_operation",
    kind=SpanKind.TOOL,
    context=SpanContext.create(),
)
span.set_attribute("tool.name", "search")
span.set_attribute("duration_ms", 50)
```

### Span Properties

| Property | Description |
|----------|-------------|
| `name` | Operation name |
| `kind` | Type (agent, llm, tool, memory, etc.) |
| `trace_id` | Unique trace identifier |
| `span_id` | Unique span identifier |
| `parent_span_id` | Parent span (for hierarchy) |
| `start_time` | When operation started |
| `duration_ms` | How long it took |
| `status` | ok, error, or cancelled |
| `attributes` | Key-value metadata |
| `events` | Timestamped events within the span |

### Span Hierarchy

Spans form a tree reflecting the execution flow:

```
agent.run (root span)
├── llm.request (child span)
│   └── [LLM call details]
├── tool.search (child span)
│   ├── tool.input (event)
│   └── tool.output (event)
└── tool.calculate (child span)
```

## Quick Examples

### Enable Tracing with Console Output

```python
from syrin import Agent, Model
from syrin.observability import ConsoleExporter, get_tracer

get_tracer().add_exporter(ConsoleExporter())

agent = Agent(model=Model.Almock())
result = agent.run("What's the weather?")
```

### JSONL Export for Analysis

```python
from syrin import Agent, Model
from syrin.observability import JSONLExporter, get_tracer

get_tracer().add_exporter(JSONLExporter("traces.jsonl"))

agent = Agent(model=Model.Almock())
result = agent.run("Hello")
```

### Session Tracking

Group related traces:

```python
from syrin.observability import trace, session

# All spans within this block share the session ID
with session("user-123-conversation-456"):
    response1 = agent.run("Hello")
    response2 = agent.run("Follow-up question")
    response3 = agent.run("Another question")
```

### Manual Spans

Wrap custom operations:

```python
from syrin.observability import trace, SpanKind

with trace.span("my_operation", kind=SpanKind.WORKFLOW) as span:
    span.set_attribute("custom_field", "value")
    # Your code here
    result = some_operation()
    span.set_attribute("result_size", len(result))
```

## Span Kinds

| Kind | Description |
|-------|-------------|
| `AGENT` | Agent execution |
| `LLM` | LLM completion call |
| `TOOL` | Tool execution |
| `MEMORY` | Memory operation |
| `BUDGET` | Budget check |
| `GUARDRAIL` | Guardrail check |
| `HANDOFF` | Agent handoff |
| `WORKFLOW` | User-defined workflow |
| `INTERNAL` | Framework operation |

## Semantic Attributes

Standard attribute keys for consistency:

```python
from syrin.observability import SemanticAttributes

span.set_attribute(SemanticAttributes.LLM_MODEL, "gpt-4o")
span.set_attribute(SemanticAttributes.LLM_TOKENS_TOTAL, 150)
span.set_attribute(SemanticAttributes.TOOL_NAME, "search")
span.set_attribute(SemanticAttributes.TOOL_INPUT, '{"query": "..."}')
```

## Debug Mode

Enable full introspection with `debug=True`:

```python
agent = Agent(model=Model.Almock(), debug=True)
result = agent.run("Hello")
```

Debug mode:
- Enables verbose console output
- Captures full context
- Records all events
- Adds human-readable formatting

## Response Traces

Every response includes trace information:

```python
result = agent.run("Hello")

# Access trace steps
for step in result.trace:
    print(f"Step: {step.step_type}")
    print(f"  Cost: ${step.cost_usd:.6f}")
    print(f"  Latency: {step.latency_ms}ms")
```

## Tracing in HTTP Serving

Enable tracing when serving:

```python
agent = Agent(model=Model.Almock(), debug=True)
agent.serve(port=8000, enable_playground=True)
```

The playground shows trace events in real-time.

## Trace Helper Context Managers

In addition to `trace()`, `span()`, and `session()`, Syrin exports helper span constructors for common operations:

- `llm_span()` for model calls
- `tool_span()` for tool execution
- `memory_span()` for memory work
- `budget_span()` for budget accounting
- `guardrail_span()` for safety checks
- `handoff_span()` for agent-to-agent transfer
- `agent_span()` for whole-agent execution blocks

These helpers are useful when you want consistent span names and attributes in custom instrumentation.

## See Also

- [Debugging Overview](/agent-kit/debugging/overview) — Introduction to observability
- [Hooks](/agent-kit/debugging/hooks) — Event subscriptions
- [Tracing Exporters](/agent-kit/debugging/tracing-exporters) — Export to OTLP, Langfuse, Phoenix
- [Debugging Techniques](/agent-kit/debugging/debugging-techniques) — Real-world debugging patterns
