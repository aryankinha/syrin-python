---
title: Tracing Exporters
description: Export traces to console, files, and observability platforms
weight: 174
---

## Where Does Your Trace Data Go?

You have spans. You have sessions. You have rich attributes and events. Now what?

This guide shows you how to route your trace data to the right destination—whether that's your terminal, a log file, or a full-featured observability platform. Exporters are the bridges between Syrin's tracing system and the outside world.

## The Export Pipeline

Here's how tracing works in Syrin:

1. Spans are created during agent execution
2. When a span completes, the tracer calls all registered exporters
3. Each exporter decides what to do with the span data

You can register multiple exporters simultaneously. This lets you send traces to both console (for development) and a remote platform (for production).

## ConsoleExporter: Development Debugging

The most common exporter for development. Prints spans in a tree format that's easy to read at a glance.

### Basic Usage

```python
from syrin import Agent, Model
from syrin.observability import trace, ConsoleExporter

# Register the console exporter
trace.add_exporter(ConsoleExporter())

# Create and run your agent
agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    system_prompt="You are a helpful assistant.",
)

result = agent.run("What is Python?")
```

**What just happened?** Syrin automatically captures spans for each operation. When you run this, you'll see output like:

```
agent: my_agent
  trace_id=a1b2c3d4 span_id=e5f6g7h8
  duration=1250.00ms status=ok
  attributes:
    agent.iteration=1
  events:
    - llm.fallback: from_model=gpt-4, to_model=gpt-4o-mini

llm: llm.complete
  trace_id=a1b2c3d4 span_id=i1j2k3l4
  duration=800.00ms status=ok
  attributes:
    llm.model=gpt-4o
    llm.tokens.input=45
    llm.tokens.output=120
    llm.cost=$0.0025
```

### Configuration Options

```python
exporter = ConsoleExporter(
    pretty=True,      # Format output for readability (default: True)
    colors=True,      # Use ANSI colors for status (default: True)
    verbose=False,    # Print every span, not just roots (default: False)
)
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `pretty` | bool | `True` | Pretty-print span attributes |
| `colors` | bool | `True` | Use terminal colors (green=ok, red=error, yellow=pending) |
| `verbose` | bool | `False` | Print all spans including children |

### Verbose Mode

By default, `ConsoleExporter` only prints root spans and lets child spans appear nested beneath them. Verbose mode prints every single span as it completes:

```python
trace.add_exporter(ConsoleExporter(verbose=True))
```

This is useful when you want to see LLM calls and tool executions as they happen, rather than waiting for the full trace to complete.

## JSONLExporter: File-Based Analysis

When you need to analyze traces programmatically or store them for later review, JSONLExporter writes each span as a JSON object on its own line.

### Basic Usage

```python
from syrin.observability import trace, JSONLExporter

# Append spans to a log file
exporter = JSONLExporter(filepath="traces/agent_run.jsonl")
trace.add_exporter(exporter)

# Run your agent
result = agent.run("Analyze this data")
```

**What just happened?** Each completed span gets written to the file. The JSON structure includes:

```json
{
  "name": "llm.complete",
  "kind": "llm",
  "trace_id": "a1b2c3d4e5f6g7h8",
  "span_id": "i1j2k3l4m5n6o7p",
  "parent_span_id": null,
  "session_id": "user_123_session",
  "start_time": "2026-03-21T10:30:00.000Z",
  "end_time": "2026-03-21T10:30:00.800Z",
  "duration_ms": 800.0,
  "status": "ok",
  "status_message": null,
  "attributes": {
    "llm.model": "gpt-4o",
    "llm.tokens.input": 45,
    "llm.tokens.output": 120,
    "llm.cost": 0.0025
  },
  "events": [],
  "children": []
}
```

### Analyzing JSONL Traces

You can analyze these traces with standard JSON tools:

```python
import json

# Read and analyze traces
total_cost = 0.0
total_tokens = 0

with open("traces/agent_run.jsonl") as f:
    for line in f:
        span = json.loads(line)
        if span["attributes"].get("llm.cost"):
            total_cost += span["attributes"]["llm.cost"]
        if span["attributes"].get("llm.tokens.total"):
            total_tokens += span["attributes"]["llm.tokens.total"]

print(f"Total cost: ${total_cost:.4f}")
print(f"Total tokens: {total_tokens}")
```

### Log Rotation Strategy

For production systems, rotate log files by time or size:

```python
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from syrin.observability import trace, JSONLExporter

# Generate filename with timestamp
def get_trace_path():
    return f"traces/{datetime.now().strftime('%Y%m%d_%H')}.jsonl"

exporter = JSONLExporter(filepath=get_trace_path())
trace.add_exporter(exporter)
```

## InMemoryExporter: Testing and Debugging

When you need to inspect spans in code—particularly useful for testing—InMemoryExporter stores them in a list you can examine.

### Basic Usage

```python
from syrin.observability import trace, InMemoryExporter

# Create in-memory exporter
exporter = InMemoryExporter()
trace.add_exporter(exporter)

# Run your agent
result = agent.run("Hello")

# Inspect the spans
root_spans = exporter.get_root_spans()
print(f"Number of traces: {len(root_spans)}")

for span in root_spans:
    print(f"Trace: {span.name}")
    print(f"Duration: {span.duration_ms:.2f}ms")
    
    # Walk all child spans
    for child in span.walk():
        print(f"  - {child.kind.value}: {child.name}")
```

### Writing Tests

The in-memory exporter shines in tests:

```python
import pytest
from syrin import Agent, Model
from syrin.observability import trace, InMemoryExporter, SpanKind

@pytest.fixture
def tracing_exporter():
    exporter = InMemoryExporter()
    trace.add_exporter(exporter)
    yield exporter
    exporter.clear()

def test_agent_calls_llm(tracing_exporter):
    agent = Agent(
        model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
        system_prompt="You are a helpful assistant.",
    )
    
    result = agent.run("Hello")
    
    # Find LLM spans
    root = tracing_exporter.get_root_spans()[0]
    llm_spans = [s for s in root.walk() if s.kind == SpanKind.LLM]
    
    assert len(llm_spans) >= 1
    assert llm_spans[0].attributes.get("llm.model") == "gpt-4o"
    
    # Check cost was tracked
    total_cost = sum(
        s.attributes.get("llm.cost", 0) 
        for s in root.walk()
    )
    assert total_cost > 0
```

## OTLPExporter: OpenTelemetry Integration

Connect Syrin to any OpenTelemetry-compatible backend—Jaeger, Grafana Tempo, Datadog, Honeycomb, and more.

### Prerequisites

```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-http
```

### Basic Usage

```python
from syrin.observability import trace, OTLPExporter

exporter = OTLPExporter(
    endpoint="http://localhost:4318/v1/traces",  # OTLP HTTP endpoint
    service_name="my-agent",                        # Service name in traces
)

trace.add_exporter(exporter)
```

### Common Backend Configurations

**Grafana Tempo (via OpenTelemetry Collector):**

```python
exporter = OTLPExporter(
    endpoint="http://localhost:4318/v1/traces",
    headers={"Authorization": "Bearer your-token"},
    service_name="syrin-agent",
)
```

**Datadog:**

```python
exporter = OTLPExporter(
    endpoint="https://api.datadoghq.com/api/v2/lm/otelhttp",
    headers={
        "DD-API-KEY": "your-datadog-api-key",
        "DD-APPLICATION-KEY": "your-datadog-app-key",
    },
    service_name="production-agent",
)
```

**Honeycomb:**

```python
exporter = OTLPExporter(
    endpoint="https://api.honeycomb.io/v1/traces",
    headers={"x-honeycomb-team": "your-api-key"},
    service_name="honeycomb-agent",
)
```

### OpenTelemetry Collector Setup

For most production setups, you'll route through an OTel Collector:

```yaml
# collector.yaml
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024

exporters:
  jaeger:
    endpoint: jaeger:14250
  prometheus:
    endpoint: 0.0.0.0:8889

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [jaeger]
    metrics:
      receivers: [prometheus]
      processors: [batch]
      exporters: [prometheus]
```

Then point Syrin at the collector:

```python
exporter = OTLPExporter(
    endpoint="http://collector:4318/v1/traces",
    service_name="syrin-agent",
)
```

## LangfuseExporter: AI-Native Observability

Langfuse is built specifically for AI applications. It provides prompt management, evaluation, cost analytics, and debugging—everything you need for production LLM apps.

### Prerequisites

```bash
pip install langfuse
```

### Basic Usage

```python
from syrin.observability import trace
from syrin.observability.langfuse import LangfuseExporter

exporter = LangfuseExporter(
    public_key="pk-...",      # From your Langfuse project
    secret_key="sk-...",
)

trace.add_exporter(exporter)

# Run your agent
result = agent.run("Hello")
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `public_key` | str | None | Langfuse public key |
| `secret_key` | str | None | Langfuse secret key |
| `host` | str | None | Self-hosted Langfuse URL |
| `environment` | str | None | Environment name (production, development) |

### Self-Hosted Langfuse

If you're running Langfuse self-hosted:

```python
exporter = LangfuseExporter(
    public_key="pk-...",
    secret_key="sk-...",
    host="https://your-langfuse.example.com",
    environment="production",
)

trace.add_exporter(exporter)
```

### What Gets Exported

LangfuseExporter automatically maps Syrin spans:

- **Agent runs** → Langfuse traces
- **LLM calls** → Langfuse generations (with token usage and cost)
- **Tool calls** → Langfuse spans
- **Session metadata** → Trace metadata

You can then use Langfuse to:

- Compare prompts and model performance
- Run evaluations on outputs
- Track costs across models and agents
- Debug specific traces

## PhoenixExporter: Local AI Debugging

Phoenix (by Arize) is an open-source observability platform optimized for local development and testing. It runs entirely locally—no cloud account required.

### Prerequisites

```bash
pip install arize-phoenix
```

### Basic Usage

```python
from syrin.observability import trace
from syrin.observability.phoenix import PhoenixExporter

exporter = PhoenixExporter(
    project_name="my-agent-debugging",
)

trace.add_exporter(exporter)

# Start Phoenix server in another terminal:
# phoenix serve

# Run your agent
result = agent.run("Analyze this")
```

### Phoenix Inline Mode

When you don't want to run a Phoenix server, use PhoenixInlineExporter to capture traces in memory and print a summary:

```python
from syrin.observability.phoenix import PhoenixInlineExporter

exporter = PhoenixInlineExporter()
trace.add_exporter(exporter)

# Run your agent multiple times
for query in queries:
    result = agent.run(query)

# Print summary
exporter.print_summary()
```

Output looks like:

```
============================================================
Phoenix Traces Summary
============================================================

Trace 1: agent.research
  Trace ID: a1b2c3d4
  Duration: 1250.00ms
  Spans: 5
  Kinds: {'agent': 1, 'llm': 2, 'tool': 2}

Trace 2: agent.summarize
  Trace ID: e5f6g7h8
  Duration: 800.00ms
  Spans: 3
  Kinds: {'agent': 1, 'llm': 1, 'memory': 1}

============================================================
```

## Combining Exporters

You can register multiple exporters for different purposes:

```python
from syrin.observability import trace, ConsoleExporter, JSONLExporter

# Development: see traces in terminal
trace.add_exporter(ConsoleExporter(colors=True))

# Analysis: save to file
trace.add_exporter(JSONLExporter(filepath="traces/production.jsonl"))

# Both get the same span data
result = agent.run("Hello")
```

## Hook Integration with Exporters

Exporters work seamlessly with hooks. For example, add custom attributes before export:

```python
from syrin.observability import trace, ConsoleExporter, current_span

trace.add_exporter(ConsoleExporter())


# Add context to every span via hook
def add_user_context(ctx):
    span = current_span()
    if span:
        span.set_attribute("user.id", get_current_user_id())
        span.set_attribute("request.correlation_id", get_correlation_id())


agent.events.on(Hook.LLM_REQUEST_END, add_user_context)
```

## Building a Custom Exporter

None of the built-in exporters fit your stack? Implement the `SpanExporter` protocol — it's two methods.

### The Protocol

```python
from syrin.observability import SpanExporter, Span

class SpanExporter(Protocol):
    def export(self, span: Span) -> None:
        """Called once per completed span."""
        ...

    def shutdown(self) -> None:
        """Called when the tracer is shutting down. Flush buffers here."""
        ...
```

`Span` is a dataclass with the same fields as the JSONL output:

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Span name (e.g., `"llm.complete"`) |
| `kind` | SpanKind | `AGENT`, `LLM`, `TOOL`, `MEMORY`, `RETRIEVAL` |
| `trace_id` | str | Groups all spans from one `agent.run()` call |
| `span_id` | str | Unique span identifier |
| `parent_span_id` | str \| None | Parent span, or None for root |
| `session_id` | str \| None | Session set at agent construction |
| `start_time` | datetime | When span started |
| `end_time` | datetime | When span ended |
| `duration_ms` | float | Duration in milliseconds |
| `status` | str | `"ok"`, `"error"`, or `"pending"` |
| `status_message` | str \| None | Error message on failure |
| `attributes` | dict | Key-value pairs (model, tokens, cost, etc.) |
| `events` | list | Timestamped events inside the span |

### Example: Send to an Internal API

```python
import json
import urllib.request
from syrin.observability import SpanExporter, Span, trace


class InternalAPMExporter(SpanExporter):
    """Send spans to an internal APM system."""

    def __init__(self, endpoint: str, api_key: str) -> None:
        self.endpoint = endpoint
        self.api_key = api_key

    def export(self, span: Span) -> None:
        payload = json.dumps({
            "name": span.name,
            "kind": span.kind.value,
            "trace_id": span.trace_id,
            "duration_ms": span.duration_ms,
            "status": span.status,
            "attributes": span.attributes,
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
            pass  # Don't let export failures crash the agent

    def shutdown(self) -> None:
        pass  # No buffer to flush for synchronous HTTP


trace.add_exporter(InternalAPMExporter(
    endpoint="https://apm.internal/v1/spans",
    api_key="your-key",
))
```

### Example: Batching Exporter

For high-volume systems, batch spans before sending:

```python
import threading
from collections import deque
from syrin.observability import SpanExporter, Span


class BatchingExporter(SpanExporter):
    """Buffer spans and flush in batches."""

    def __init__(self, backend: SpanExporter, batch_size: int = 100) -> None:
        self.backend = backend
        self.batch_size = batch_size
        self._buffer: deque[Span] = deque()
        self._lock = threading.Lock()

    def export(self, span: Span) -> None:
        with self._lock:
            self._buffer.append(span)
            if len(self._buffer) >= self.batch_size:
                self._flush()

    def _flush(self) -> None:
        """Must be called with self._lock held."""
        while self._buffer:
            self.backend.export(self._buffer.popleft())

    def shutdown(self) -> None:
        with self._lock:
            self._flush()
        self.backend.shutdown()
```

### Example: Filter Exporter

Only export spans that match a condition:

```python
class FilterExporter(SpanExporter):
    """Only export LLM spans — skip tool and memory spans."""

    def __init__(self, backend: SpanExporter, kinds: set) -> None:
        self.backend = backend
        self.kinds = kinds

    def export(self, span: Span) -> None:
        if span.kind in self.kinds:
            self.backend.export(span)

    def shutdown(self) -> None:
        self.backend.shutdown()


# Usage: only send LLM spans to your expensive APM
from syrin.observability import SpanKind

trace.add_exporter(FilterExporter(
    backend=OTLPExporter(endpoint="http://apm:4318/v1/traces"),
    kinds={SpanKind.LLM, SpanKind.AGENT},
))
```

> **Don't block the agent.** The `export()` method is called synchronously after each span. Keep it fast — use async queues or fire-and-forget HTTP for slow destinations. If you must do I/O, wrap in a background thread or use `BatchingExporter`.

## Choosing the Right Exporter

| Use Case | Recommended Exporter |
|----------|---------------------|
| Local development | `ConsoleExporter` |
| CI/CD testing | `InMemoryExporter` |
| Production debugging | `JSONLExporter` + remote platform |
| Grafana/Tempo | `OTLPExporter` |
| Datadog | `OTLPExporter` |
| Cost analytics | `LangfuseExporter` |
| Local AI iteration | `PhoenixExporter` |
| Prompt experimentation | `PhoenixExporter` |

## What's Next?

- [Logging](/debugging/logging) — Configure structured logging alongside tracing
- [Debugging Techniques](/debugging/debugging-techniques) — Real-world debugging patterns
- [Hooks Reference](/debugging/hooks-reference) — Complete hooks reference

## See Also

- [Tracing Overview](/debugging/tracing) — Understanding spans and sessions
- [Hooks System](/debugging/hooks) — Reacting to agent lifecycle events
- [Observability Examples](https://github.com/anomalyco/syrin-python/tree/main/examples/10_observability) — Working code examples
