---
title: Logging
description: Configure structured logging and audit trails for Syrin agents
weight: 175
---

## What Happened While You Weren't Looking?

When your agent is running in production, you need to know what's happening. Not just the final response—but the entire journey. Which model was called? How many tokens? What tools ran? What cost accumulated?

Syrin provides two complementary logging systems: **standard Python logging** for framework operations and **AuditLog** for high-level event tracking. Together, they give you full visibility into agent behavior.

## Python Logging: Framework Internals

Syrin uses Python's standard `logging` module throughout the codebase. Each module creates its own logger, so you can control granularity.

### Logger Hierarchy

Syrin loggers follow this hierarchy:

| Logger Name | Covers |
|-------------|--------|
| `syrin` | Root logger for all Syrin modules |
| `syrin.agent` | Agent lifecycle, loop execution |
| `syrin.llm` | LLM calls and responses |
| `syrin.tool` | Tool execution |
| `syrin.memory` | Memory operations |
| `syrin.budget` | Budget tracking |
| `syrin.context` | Context management |
| `syrin.serve` | HTTP server |
| `syrin.observability` | Tracing and metrics |

### Basic Configuration

```python
import logging

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Or configure specific loggers
logging.getLogger("syrin.agent").setLevel(logging.DEBUG)
logging.getLogger("syrin.budget").setLevel(logging.WARNING)  # Quiet budget logs
```

**What just happened?** You set up logging to see agent operations at DEBUG level (verbose) while keeping budget logs quiet (WARNING and above).

### Output Example

```
2026-03-21 10:30:00 | syrin.agent | INFO | Starting agent.run for "What is Python?"
2026-03-21 10:30:00 | syrin.agent | DEBUG | Memory recall: 3 items retrieved
2026-03-21 10:30:01 | syrin.llm | INFO | LLM call: gpt-4o, tokens=45/120, cost=$0.0025
2026-03-21 10:30:01 | syrin.agent | INFO | Agent run completed in 800ms
```

### Log Levels Reference

| Level | When to Use |
|-------|-------------|
| **DEBUG** | Detailed tracing, variable values, internal decisions |
| **INFO** | Normal operations, completed steps, metrics |
| **WARNING** | Recoverable issues, approaching limits |
| **ERROR** | Failed operations that need attention |
| **CRITICAL** | System-level failures |

### Development vs Production

**Development** — verbose logging to understand behavior:

```python
logging.getLogger("syrin").setLevel(logging.DEBUG)
```

**Production** — info only, focused on key operations:

```python
logging.getLogger("syrin").setLevel(logging.INFO)
logging.getLogger("syrin.observability").setLevel(logging.WARNING)  # Reduce noise
```

## AuditLog: High-Level Event Tracking

While Python logging captures framework internals, AuditLog captures the events that matter for compliance, debugging, and cost attribution. It's designed for structured analysis.

### What Gets Audited

AuditLog tracks these event types:

- **llm_call** — LLM invocation with model, tokens, cost, latency
- **tool_call** — Tool execution with input, output, duration, errors
- **handoff** — Agent-to-agent transfers
- **spawn** — New agent spawning
- **budget_exceeded** — Budget limit reached
- **error** — Run failures

### Basic Audit Setup

```python
from syrin import Agent, AgentConfig, AuditLog, Model

audit = AuditLog(path="./audit.jsonl")

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    config=AgentConfig(audit=audit),
)

result = agent.run("Analyze this data")
```

**What just happened?** Every event during agent execution is written to `./audit.jsonl` as JSON lines. Each entry includes timestamps, model info, token counts, costs, and more.

### Audit Entry Structure

Each line in the audit file is a JSON object:

```json
{
  "timestamp": "2026-03-21T10:30:00.000Z",
  "source": "MyAgent",
  "event": "llm_call",
  "model": "gpt-4o",
  "tokens": {"input": 45, "output": 120, "total": 165},
  "cost_usd": 0.0025,
  "budget_percent": 2.5,
  "duration_ms": 800.0,
  "trace_id": "a1b2c3d4e5f6g7h8",
  "run_id": "i1j2k3l4m5n6o7p",
  "iteration": 1,
  "stop_reason": "stop"
}
```

### Filtering Events

AuditLog lets you control what gets logged:

```python
audit = AuditLog(
    path="./audit.jsonl",
    include_llm_calls=True,      # Default: True
    include_tool_calls=True,     # Default: True
    include_handoff_spawn=True,  # Default: True
    include_budget=False,         # Default: False
    include_user_input=False,     # Default: False
    include_model_output=True,    # Default: True
)
```

For compliance, you might want to exclude user input and model output:

```python
audit = AuditLog(
    path="./compliance_audit.jsonl",
    include_llm_calls=True,
    include_tool_calls=False,
    include_handoff_spawn=False,
    include_user_input=False,
    include_model_output=False,  # Don't store PII in outputs
)
```

### Querying Audit Entries

The JSONL backend supports basic querying:

```python
from datetime import datetime, timedelta
from syrin import AuditFilters

backend = audit.get_backend()

# Last 10 entries
recent = backend.query(AuditFilters(limit=10))

# Entries since yesterday
yesterday = datetime.now() - timedelta(days=1)
recent = backend.query(AuditFilters(since=yesterday))

# Specific agent's LLM calls
llm_calls = backend.query(AuditFilters(
    agent="ResearchAgent",
    event="llm_call",
    limit=50,
))
```

### Analyzing Audit Data

```python
import json
from collections import defaultdict

# Load and analyze audit data
total_cost = 0.0
tokens_by_model = defaultdict(int)
duration_by_event = defaultdict(list)

with open("./audit.jsonl") as f:
    for line in f:
        entry = json.loads(line)
        
        if entry["event"] == "llm_call":
            total_cost += entry.get("cost_usd", 0)
            tokens_by_model[entry["model"]] += entry["tokens"]["total"]
            duration_by_event["llm_call"].append(entry["duration_ms"])

print(f"Total cost: ${total_cost:.4f}")
print(f"Tokens by model: {dict(tokens_by_model)}")
print(f"Avg LLM latency: {sum(duration_by_event['llm_call']) / len(duration_by_event['llm_call']):.0f}ms")
```

## Custom Audit Backend

For production systems, implement the `AuditBackendProtocol` to send audit data to your data warehouse, SIEM, or analytics platform:

```python
from syrin.audit import AuditBackendProtocol, AuditEntry, AuditFilters
from syrin.audit.models import AuditEntry

class CustomAuditBackend(AuditBackendProtocol):
    def __init__(self, api_endpoint: str, api_key: str):
        self.api_endpoint = api_endpoint
        self.api_key = api_key

    def write(self, entry: AuditEntry) -> None:
        # Send to your analytics platform
        requests.post(
            self.api_endpoint,
            json=entry.model_dump(),
            headers={"Authorization": f"Bearer {self.api_key}"},
        )

    def query(self, filters: AuditFilters) -> list[AuditEntry]:
        # Implement if you need to read back
        raise NotImplementedError("Query not supported for this backend")

# Use custom backend
audit = AuditLog(
    custom_backend=CustomAuditBackend(
        api_endpoint="https://analytics.example.com/audit",
        api_key="your-api-key",
    )
)
```

## Combining Logging and Audit

For complete observability, use both systems together:

**Python logging** — Framework operations, debugging, real-time monitoring

```python
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
```

**AuditLog** — Structured event tracking for compliance and analysis

```python
audit = AuditLog(path="./audit.jsonl")
```

Together, they give you real-time visibility (logging) plus long-term analysis capability (audit).

## Logging with Hooks

Hooks let you add custom logging alongside Syrin's built-in logging:

```python
from syrin.observability import current_span


def log_llm_details(ctx):
    span = current_span()
    if span:
        span.set_attribute("custom.user_tier", get_user_tier())
        span.set_attribute("custom.request_source", get_request_source())

    # Also write to your logging system
    logging.getLogger("myapp.llm").info(
        "LLM call completed",
        extra={
            "model": ctx.get("model"),
            "tokens": ctx.get("tokens"),
            "cost": ctx.get("cost"),
        }
    )


agent.events.on(Hook.LLM_REQUEST_END, log_llm_details)
```

## Structured Logging Best Practices

For production systems, use structured logging (JSON format) for easier parsing:

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            **record.__dict__.get("extra", {}),
        })

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.getLogger("syrin").addHandler(handler)
```

## What's Next?

- [Debugging Techniques](/agent-kit/debugging/debugging-techniques) — Real-world debugging patterns
- [Tracing Exporters](/agent-kit/debugging/tracing-exporters) — Route traces to observability platforms
- [Hooks Reference](/agent-kit/debugging/hooks-reference) — Complete hooks reference

## See Also

- [Tracing Overview](/agent-kit/debugging/tracing) — Understanding spans and sessions
- [Hooks System](/agent-kit/debugging/hooks) — Reacting to agent lifecycle events
- [Audit Logging Examples](https://github.com/anomalyco/syrin-python/tree/main/examples/10_observability) — Working code examples
