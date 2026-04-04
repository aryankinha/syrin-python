---
title: Logging
description: Configure structured logging and audit trails for Syrin agents
weight: 175
---

## What Happened While You Weren't Looking?

When your agent is running in production, you need to know what's happening. Not just the final response — but the entire journey. Which model was called? How many tokens? What tools ran? What cost accumulated?

Syrin gives you two complementary systems: **Python logging** for framework internals and **AuditLog** for high-level event tracking. Together, they give you full visibility into agent behavior.

## Python Logging: Framework Internals

Syrin uses Python's standard `logging` module throughout the codebase. Each subsystem has its own logger, so you can control granularity independently.

The logger hierarchy:

`syrin` — Root logger for all Syrin modules.

`syrin.agent` — Agent lifecycle and loop execution.

`syrin.llm` — LLM calls and responses.

`syrin.tool` — Tool execution.

`syrin.memory` — Memory operations.

`syrin.budget` — Budget tracking.

`syrin.context` — Context management.

`syrin.serve` — HTTP server.

`syrin.observability` — Tracing and metrics.

### Basic Configuration

```python
import logging

# Enable INFO for everything
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Fine-grained control
logging.getLogger("syrin.agent").setLevel(logging.DEBUG)   # Verbose
logging.getLogger("syrin.budget").setLevel(logging.WARNING) # Quiet
```

### Example Output

```
2026-04-03 10:30:00 | syrin.agent | INFO | Starting agent.run for "What is Python?"
2026-04-03 10:30:00 | syrin.agent | DEBUG | Memory recall: 3 items retrieved
2026-04-03 10:30:01 | syrin.llm | INFO | LLM call: gpt-4o, tokens=45/120, cost=$0.0025
2026-04-03 10:30:01 | syrin.agent | INFO | Agent run completed in 800ms
```

### Development vs Production

For development, turn everything up to DEBUG:

```python
logging.getLogger("syrin").setLevel(logging.DEBUG)
```

For production, keep it at INFO and suppress noisy subsystems:

```python
logging.getLogger("syrin").setLevel(logging.INFO)
logging.getLogger("syrin.observability").setLevel(logging.WARNING)
```

## AuditLog: High-Level Event Tracking

Where Python logging captures framework internals, AuditLog captures the events that matter for compliance, debugging, and cost attribution. Every LLM call, tool invocation, handoff, spawn, budget event, and error is recorded as a structured JSON line.

### Setup

```python
from syrin import Agent, AuditLog, Model

audit = AuditLog(path="./audit.jsonl")

agent = Agent(
    model=Model.mock(),
    config=AgentConfig(audit=audit),
)

result = agent.run("Analyze this data")
```

### Audit Entry Format

Each line in the audit file is a JSON object:

```json
{
  "timestamp": "2026-04-03T10:30:00.000Z",
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

Six event types are audited: `llm_call`, `tool_call`, `handoff`, `spawn`, `budget_exceeded`, and `error`.

### Filtering What Gets Logged

```python
from syrin import AuditLog

audit = AuditLog(
    path="./audit.jsonl",
    include_llm_calls=True,       # Default: True
    include_tool_calls=True,      # Default: True
    include_handoff_spawn=True,   # Default: True
    include_budget=False,          # Default: False
    include_user_input=False,      # Default: False (don't store raw user input)
    include_model_output=True,     # Default: True
)
```

For compliance scenarios where you shouldn't store PII:

```python
audit = AuditLog(
    path="./compliance_audit.jsonl",
    include_llm_calls=True,
    include_tool_calls=True,
    include_user_input=False,      # Don't store raw user messages
    include_model_output=False,    # Don't store LLM outputs
)
```

### Querying Audit Entries

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

### Analyzing Cost Data

```python
import json
from collections import defaultdict

total_cost = 0.0
tokens_by_model = defaultdict(int)
durations = []

with open("./audit.jsonl") as f:
    for line in f:
        entry = json.loads(line)
        if entry["event"] == "llm_call":
            total_cost += entry.get("cost_usd", 0)
            tokens_by_model[entry["model"]] += entry["tokens"]["total"]
            durations.append(entry["duration_ms"])

print(f"Total cost: ${total_cost:.4f}")
print(f"Tokens by model: {dict(tokens_by_model)}")
if durations:
    print(f"Avg LLM latency: {sum(durations) / len(durations):.0f}ms")
```

## Custom Audit Backend

Send audit data to your data warehouse, SIEM, or analytics platform:

```python
from syrin.audit import AuditBackendProtocol, AuditEntry, AuditFilters

class CustomAuditBackend(AuditBackendProtocol):
    def __init__(self, api_endpoint: str, api_key: str):
        self.api_endpoint = api_endpoint
        self.api_key = api_key

    def write(self, entry: AuditEntry) -> None:
        import requests
        requests.post(
            self.api_endpoint,
            json=entry.model_dump(),
            headers={"Authorization": f"Bearer {self.api_key}"},
        )

    def query(self, filters: AuditFilters) -> list[AuditEntry]:
        raise NotImplementedError("Query not supported for this backend")

audit = AuditLog(
    custom_backend=CustomAuditBackend(
        api_endpoint="https://analytics.example.com/audit",
        api_key="your-api-key",
    )
)
```

## Adding Custom Context to Hooks

Hook callbacks let you add custom fields to structured logs:

```python
import logging
from syrin.enums import Hook
from syrin.observability import current_span

def log_llm_details(ctx):
    # Add to the active tracing span
    span = current_span()
    if span:
        span.set_attribute("custom.user_tier", "premium")

    # Write to your logging system with structured fields
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

## Structured JSON Logging

For log ingestion systems (Datadog, Splunk, ELK), emit JSON:

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

- [Tracing](/debugging/tracing) — Span-based tracing with OpenTelemetry exporters
- [Hooks Reference](/debugging/hooks-reference) — All 182 lifecycle hooks
- [Pry](/debugging/pry) — Interactive step-through debugger
