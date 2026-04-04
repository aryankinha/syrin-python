---
title: Remote Config
description: Runtime configuration updates, A/B testing, and rollback for agents
weight: 120
---

## Change Your Agent Without Restarting

You deployed an agent. Now you need to lower the budget because costs are spiking, enable a new tool for testing, switch from REACT to SINGLE_SHOT loop strategy, or rollback a bad prompt change.

Before remote config, that meant changing code, redeploying, restarting the service, and losing in-flight requests. With remote config, you push changes instantly — no restart, no downtime.

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

That flow teaches the three key ideas: baseline values come from code, overrides come from the remote config API, and current values are the effective runtime configuration — the combination of both.

## Key Concepts

### Baseline vs Overrides

The config system has three layers. **Baseline** holds the values from code — frozen at the first `GET` request. **Overrides** are the user-applied changes pushed via the API. **Current** is the effective runtime value, calculated as baseline plus overrides.

When you revert (`value: null`), the path is removed from overrides and current falls back to baseline automatically.

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

Each field includes metadata for UI rendering. `baseline_value` is the value from code. `current_value` is the effective runtime value. `overridden` is a boolean that is true if this path has an active remote override. `enum_values` lists valid string options for dropdown-style fields like loop strategies. `constraints` carries min/max bounds for numeric fields.

## What Can Be Configured?

### Agent Section

Four agent-level paths are available. `agent.system_prompt` (string) changes the system prompt. `agent.loop_strategy` (string) switches between `react`, `single_shot`, and `hitl`. `agent.max_tool_iterations` (int) caps the number of tool-call loops. `agent.human_approval_timeout` (int) sets the HITL confirmation timeout in seconds.

### Budget Section

Four budget paths control cost. `budget.max_cost` (float) sets the per-run budget in USD. `budget.reserve` (float) holds back a reserve amount. `budget.rate_limits.hour` (float) sets the hourly spend limit. `budget.rate_limits.day` (float) sets the daily spend limit.

### Tools Section

`tools.{name}.enabled` (bool) enables or disables any individual tool by name. Substitute `{name}` with the tool's registered name.

### Memory Section

Two memory paths are remotely configurable. `memory.top_k` (int) sets the maximum number of memories recalled per query. `memory.relevance_threshold` (float) sets the minimum relevance score for a memory to be returned.

## Hot Swaps (Require Restart)

Some changes require a service restart to fully take effect. These are flagged as `pending_restart` in the PATCH response.

Four paths trigger this behavior. `memory.backend` requires a restart because the memory backend handles state outside the process. `memory.path` requires a restart because the file path change only takes effect when the backend initializes. `checkpoint.storage` and `checkpoint.path` both require a restart for the same reason — the checkpoint backend is initialized at startup.

What actually happens when you hit one of these paths: the change is applied to in-memory state immediately and returned as `pending_restart`, but the backend storage (Redis, files, etc.) only switches after a service restart. Your workflow is to apply the change via PATCH, confirm it's in memory, then restart when convenient.

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

Three transport options are available. **SSE** (the default) delivers real-time updates via a persistent streaming connection — best for most production deployments. **Polling** checks for changes on a configurable interval, making it the right choice when SSE is blocked by a firewall or proxy. **Serve** mode is self-hosted with no cloud dependency.

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

All overrides are validated against the schema. Unknown paths are rejected. Invalid enum values are rejected. Type mismatches are rejected. Callables cannot be overridden remotely.

### Authentication

For self-hosted deployments, add auth middleware to the `/config` routes. Syrin Cloud uses API keys.

### Best Practices

Audit log all PATCH requests so you know who changed what and when. Require approval for production changes — a second pair of eyes prevents expensive mistakes. Always have a rollback plan before pushing changes. Test in staging first.

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
