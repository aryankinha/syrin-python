---
title: Remote Config
description: Runtime configuration updates, A/B testing, and rollback for agents
weight: 120
---

## Change Your Agent Without Restarting

You deployed an agent. Now you need to:
- Lower the budget because costs are too high
- Enable a new tool for testing
- Switch from REACT to SINGLE_SHOT loop strategy
- Rollback a bad change

Before remote config, you had to:
1. Change the code
2. Redeploy
3. Restart the service
4. Lose in-flight requests

With remote config, you push changes instantly. No restart. No downtime.

## The Problem

Production systems need flexibility:
- **Cost control**: Adjust budgets without redeploying
- **A/B testing**: Try different prompts or strategies
- **Feature flags**: Enable/disable tools gradually
- **Incident response**: Lower limits during high-traffic events
- **Rollback**: Revert bad changes instantly

Traditional approaches:
- Environment variables (require restart)
- Config files (require restart)
- Feature flags services (complex setup)

Remote config provides a simple REST API for live configuration.

## Quick Start

### Enable Remote Config

```python
from syrin import Agent, Model, Budget
from syrin.remote import init

# With Syrin Cloud
init(api_key="your-syrin-api-key")

# Or self-hosted (no API key needed)
init()  # Uses built-in /config routes
```

The fastest end-to-end local walkthrough is `examples/12_remote_config/init_and_serve.py`.

### Configure the Agent

```python
model = Model.OpenAI("gpt-4o", api_key="your-api-key")

agent = Agent(
    model=model,
    system_prompt="You are a helpful assistant.",
    budget=Budget(max_cost=1.00),
)
agent.serve(port=8000)
```

### Get Current Configuration

```bash
curl http://localhost:8000/config
```

**Response:**
```json
{
  "agent_id": "assistant:Assistant",
  "sections": {
    "agent": {
      "fields": [
        {"path": "agent.loop_strategy", "type": "str", "enum_values": ["react", "single_shot", "hitl"]},
        {"path": "agent.system_prompt", "type": "str"}
      ]
    },
    "budget": {
      "fields": [
        {"path": "budget.max_cost", "type": "float"},
        {"path": "budget.reserve", "type": "float"}
      ]
    },
    "tools": {
      "fields": [
        {"path": "tools.remember_fact.enabled", "type": "bool"},
        {"path": "tools.recall_fact.enabled", "type": "bool"}
      ]
    }
  },
  "baseline_values": {
    "agent.loop_strategy": "react",
    "agent.system_prompt": "You are a helpful assistant.",
    "budget.max_cost": 1.0
  },
  "overrides": {},
  "current_values": {
    "agent.loop_strategy": "react",
    "agent.system_prompt": "You are a helpful assistant.",
    "budget.max_cost": 1.0
  }
}
```

### Apply a Change

```bash
curl -X PATCH http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "assistant:Assistant",
    "version": 1,
    "overrides": [
      {"path": "budget.max_cost", "value": 0.50},
      {"path": "agent.loop_strategy", "value": "single_shot"}
    ]
  }'
```

**Response:**
```json
{
  "accepted": ["budget.max_cost", "agent.loop_strategy"],
  "rejected": [],
  "pending_restart": []
}
```

### Verify the Change

```bash
curl http://localhost:8000/config
```

**Updated response:**
```json
{
  "baseline_values": {
    "agent.loop_strategy": "react",
    "budget.max_cost": 1.0
  },
  "overrides": {
    "budget.max_cost": 0.5,
    "agent.loop_strategy": "single_shot"
  },
  "current_values": {
    "agent.loop_strategy": "single_shot",
    "budget.max_cost": 0.5
  }
}
```

## Full Local Workflow

If you want to understand remote config in one pass, use this order:

1. Run `PYTHONPATH=. python examples/12_remote_config/init_and_serve.py`
2. Call `GET /config` to inspect the schema and current values
3. Patch one safe field such as `budget.max_cost`
4. Call `GET /config` again to confirm the override moved from baseline to current
5. Send a normal `/chat` request and observe the agent running with the new value
6. Revert with `value: null` to return to baseline

That flow teaches the three key ideas:

- baseline values come from code
- overrides come from the remote config API
- current values are the effective runtime configuration

## Key Concepts

### Baseline vs Overrides

| Concept | Description |
|---------|-------------|
| **Baseline** | Values from code (frozen at first GET) |
| **Overrides** | User-applied changes |
| **Current** | Effective values (baseline + overrides) |

When you revert (`value: null`), the path is removed from overrides. Current falls back to baseline.

### Reverting Changes

```bash
curl -X PATCH http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "assistant:Assistant",
    "version": 2,
    "overrides": [
      {"path": "budget.max_cost", "value": null}
    ]
  }'
```

**Response:**
```json
{
  "accepted": ["budget.max_cost"],
  "rejected": [],
  "pending_restart": []
}
```

Now `current_values.budget.max_cost` is back to baseline (1.0).

### Schema Fields

Each field includes metadata for UI rendering:

| Field | Description |
|-------|-------------|
| `baseline_value` | Value from code |
| `current_value` | Effective value |
| `overridden` | True if this path has a remote override |
| `enum_values` | For dropdowns (e.g., loop strategies) |
| `constraints` | Min/max values |

## What Can Be Configured?

### Agent Section

| Path | Type | Description |
|------|------|-------------|
| `agent.system_prompt` | `str` | System prompt |
| `agent.loop_strategy` | `str` | `react`, `single_shot`, `hitl` |
| `agent.max_tool_iterations` | `int` | Max tool call loops |
| `agent.human_approval_timeout` | `int` | HITL timeout in seconds |

### Budget Section

| Path | Type | Description |
|------|------|-------------|
| `budget.max_cost` | `float` | Run budget in USD |
| `budget.reserve` | `float` | Reserve amount |
| `budget.rate_limits.hour` | `float` | Hourly limit |
| `budget.rate_limits.day` | `float` | Daily limit |

### Tools Section

| Path | Type | Description |
|------|------|-------------|
| `tools.{name}.enabled` | `bool` | Enable/disable a tool |

### Memory Section

| Path | Type | Description |
|------|------|-------------|
| `memory.top_k` | `int` | Max memories to recall |
| `memory.relevance_threshold` | `float` | Min relevance score |

## Hot Swaps (Require Restart)

Some changes require a restart to take full effect. These are flagged as `pending_restart`:

| Path | Requires Restart |
|------|-----------------|
| `memory.backend` | ✅ Memory backend change |
| `memory.path` | ✅ File path change |
| `checkpoint.storage` | ✅ Checkpoint storage change |
| `checkpoint.path` | ✅ Checkpoint path change |

**What happens:**
1. The change is applied to in-memory state
2. `pending_restart` is returned
3. Backend storage (Redis, files) only changes after restart

**Your workflow:**
1. Apply change via PATCH
2. Change is effective in memory
3. Restart the service
4. Backend storage is updated

## Streaming Updates

Subscribe to configuration changes via SSE:

```bash
curl http://localhost:8000/config/stream
```

**Response:**
```
event: heartbeat
data: {"version": 0}

event: heartbeat
data: {"version": 0}
...
```

In a real dashboard, `GET /config/stream` is the right way to keep a configuration UI or operator tool synchronized with live changes.

**When a change is applied:**
```
event: override
data: {
  "agent_id": "assistant:Assistant",
  "version": 1,
  "overrides": [{"path": "budget.max_cost", "value": 0.5}]
}
```

This enables real-time dashboards and monitoring.

## A/B Testing

### Scenario

Test two different system prompts:

```bash
# Variant A (control)
curl -X PATCH http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "assistant:Assistant",
    "version": 1,
    "overrides": [
      {"path": "agent.system_prompt", "value": "You are a helpful assistant. Be concise."}
    ]
  }'
```

### Measure Results

```bash
curl http://localhost:8000/budget
```

Track which variant has better cost efficiency or user satisfaction.

### Rollback

```bash
# Revert to baseline
curl -X PATCH http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "assistant:Assistant",
    "version": 2,
    "overrides": [
      {"path": "agent.system_prompt", "value": null}
    ]
  }'
```

## Syrin Cloud Integration

### Setup

```python
from syrin.remote import init

init(api_key="your-syrin-api-key")
```

### How It Works

1. **Agent registers** with Syrin Cloud on startup
2. **Cloud stores** schema and baseline
3. **You push changes** via cloud dashboard or API
4. **SSE stream** delivers changes to agent

### Transport Options

| Transport | Use Case |
|----------|----------|
| **SSE** (default) | Real-time updates via streaming connection |
| **Polling** | When SSE is blocked by firewall |
| **Serve** | Self-hosted, no cloud |

```python
from syrin.remote import init, PollingTransport

# Polling fallback
init(
    api_key="your-syrin-api-key",
    transport=PollingTransport(poll_interval=30.0),
)
```

## Security

### Validation

All overrides are validated against the schema:
- Unknown paths are rejected
- Invalid enum values are rejected
- Type mismatches are rejected
- Callables cannot be overridden

### Authentication

For self-hosted:
- Add auth middleware to `/config` routes
- Syrin Cloud uses API keys

### Best Practices

1. **Audit logging**: Log all PATCH requests
2. **Approval workflow**: Require approval for production changes
3. **Rollback plan**: Always know how to revert
4. **Test first**: Test changes in staging

## API Reference

### GET /config

Returns agent schema with baseline, overrides, and current values.

### PATCH /config

Apply overrides.

**Request:**
```json
{
  "agent_id": "string",
  "version": 1,
  "overrides": [
    {"path": "string", "value": null},
    {"path": "string", "value": "new_value"}
  ]
}
```

**Response:**
```json
{
  "accepted": ["path1", "path2"],
  "rejected": [["path3", "reason"]],
  "pending_restart": ["memory.backend"]
}
```

### GET /config/stream

SSE stream for real-time change notifications.

## Public Remote Config Types

The remote-config package also exports the schema and transport objects used under the hood:

- `AgentSchema`, `ConfigSchema`, `FieldSchema`, and `extract_agent_schema()` / `extract_schema()` for schema introspection.
- `ConfigOverride`, `OverridePayload`, `ResolveResult`, `SyncRequest`, and `SyncResponse` for override application and sync flows.
- `ConfigRegistry`, `ConfigResolver`, and `get_registry()` for runtime registration and resolution.
- `ConfigTransport`, `ServeTransport`, `SSETransport`, and `PollingTransport` for transport implementations.

## See Also

- [Serving: HTTP API](/agent-kit/production/serving-http) — REST API reference
- [Serving: Advanced](/agent-kit/production/serving-advanced) — Production patterns
- [Budget](/agent-kit/core/budget) — Budget configuration
- [Memory](/agent-kit/core/memory) — Memory configuration
