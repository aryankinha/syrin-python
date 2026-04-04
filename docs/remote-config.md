---
title: Remote Config
description: Push config changes to a running agent, roll back versions, and send lifecycle commands — all without restarting.
weight: 60
---

## Overview

`RemoteConfig` is the control-plane client for a single agent. Attach it at construction time and the agent begins listening for config pushes, version updates, and lifecycle commands from a remote source (Nexus, a custom webhook, or any polling endpoint).

```python
import os
from syrin import Agent, Model
from syrin.remote_config import RemoteConfig
from syrin.enums import RemoteField, RemoteTransport

class MyAgent(Agent):
    model = Model.mock()
    system_prompt = "You are a helpful assistant."

agent = MyAgent(
    remote_config=RemoteConfig(
        url="https://nexus.syrin.dev/config",
        agent_id="my-agent-prod",
        api_key=os.environ["NEXUS_API_KEY"],
        transport=RemoteTransport.SSE,
        allow=[RemoteField.MODEL, RemoteField.BUDGET],
        deny=[RemoteField.IDENTITY, RemoteField.AUDIT_BACKEND],
    )
)
```

---

## Config Schema

Call `agent.config_schema()` to get the JSON Schema for all remotely configurable fields on the agent. This is the schema Nexus uses to render the live config editor.

```python
schema = agent.config_schema()
# Returns a dict conforming to JSON Schema draft-07.
# Fields in RemoteConfig.deny are marked readOnly: true.
```

---

## RemoteConfig Constructor

```python
RemoteConfig(
    url="https://...",               # Remote config server URL
    agent_id="my-agent",             # Unique identifier (namespace)
    api_key="...",                   # Auth token
    transport=RemoteTransport.SSE,   # SSE | POLLING | WEBSOCKET
    poll_interval=30,                # Seconds between polls (POLLING mode)
    reconnect_on_failure=True,       # Auto-reconnect on transport error
    max_reconnect_attempts=10,       # Hard limit on reconnect tries
    allow=[RemoteField.MODEL],       # Whitelist — only these fields accepted
    deny=[RemoteField.BUDGET],       # Blacklist — always rejected (takes priority)
    validators=[...],                # Validation rules (see below)
    command_config=RemoteCommandConfig(...),  # Command security options
)
```

### Field Access Control

`allow` and `deny` take lists of `RemoteField` enum values. `deny` takes priority over `allow`.

Fourteen fields are available for remote control. `MODEL` governs the model name, provider, and generation settings. `BUDGET` controls cost limits and budget caps. `GUARDRAILS` lets you enable or disable guardrails remotely. `MEMORY` covers the memory backend, decay curves, and top_k recall count. `CONTEXT` adjusts context window settings. `TOOLS` enables or disables individual tools. `SYSTEM_PROMPT` can update the agent's system prompt text at runtime.

`RATE_LIMIT` manages rate limit settings and `CIRCUIT_BREAKER` controls circuit breaker thresholds. `OUTPUT` configures output format and `MCP` enables or disables MCP server connections. `KNOWLEDGE` controls knowledge store settings and `CHECKPOINT` manages checkpoint configuration.

The last two — `IDENTITY` and `AUDIT_BACKEND` — are security boundaries and should almost always be in your `deny` list. `IDENTITY` touches the agent's identity configuration and `AUDIT_BACKEND` controls where audit data is sent. Allowing either over the network is a significant security risk.

---

## Validators

Validators run before each config push. They raise `ConfigValidationError` to reject the change.

### max_budget

Rejects any push that would set the budget above a ceiling:

```python
from syrin.remote_config import RemoteConfig, RemoteConfigValidator

remote = RemoteConfig(
    ...,
    validators=[RemoteConfigValidator.max_budget(10.00)],
)
# A push of {"budget": 15.00} raises ConfigValidationError.
# A push of {"budget": 9.99} is accepted.
```

### require_guardrail

Rejects any push that would disable a named guardrail:

```python
validators=[RemoteConfigValidator.require_guardrail("PromptInjectionGuardrail")]
```

### Chaining

Multiple validators all run before each push — any one rejection blocks the update:

```python
validators=[
    RemoteConfigValidator.max_budget(10.00),
    RemoteConfigValidator.require_guardrail("PIIGuardrail"),
]
```

---

## Rollback

Every successful config push creates a `ConfigVersion` entry. Roll back to the previous version:

```python
# Roll back to the version immediately before current
await agent.remote_config.rollback()

# Roll back to a specific version number
await agent.remote_config.rollback(version=3)
```

Rollback creates a new `ConfigVersion` entry (it does not rewrite history). `Hook.CONFIG_ROLLBACK` fires on success.

### Config History

```python
history = await agent.remote_config.get_history(last_n=5)
for v in history:
    print(f"v{v.version}  applied_by={v.applied_by}  fields={v.fields_changed}")
```

Each `ConfigVersion` carries six fields. `version` is a monotonically increasing integer — version 1 is the first push, version 2 is the second, and so on. `applied_at` is the UTC datetime of when the change landed. `applied_by` is the `changed_by` value passed to `apply()`, which also appears in the audit log. `fields_changed` is a list of the top-level field keys that were modified by this version. `previous_values` holds the before-state as a dict and `new_values` holds the after-state. Finally, `rollback_token` is a UUID4 that lets you safely reference a specific version for rollback without relying on version numbers alone.

---

## Remote Commands

`RemoteCommand` values are sent from the control plane to control the agent's lifecycle without touching its config. Eight commands are available.

`PAUSE` (value: `agent.pause`) pauses the agent after the current step completes. `RESUME` (value: `agent.resume`) resumes a paused agent. `KILL` (value: `agent.kill`) terminates the agent immediately. `ROLLBACK` (value: `agent.rollback`) rolls back to the previous checkpoint.

`FLUSH_MEMORY` (value: `agent.memory.flush`) clears agent memory entirely. `ROTATE_SECRET` (value: `agent.secret.rotate`) triggers a secret re-fetch from the secrets store. `RELOAD_TOOLS` (value: `agent.tools.reload`) reloads tool definitions without a restart. `DRAIN` (value: `agent.drain`) completes the current run and then pauses — useful for graceful shutdown.

### Kill Confirmation

By default `kill_requires_confirmation=True` — a KILL command arms a 30-second confirmation window. A second KILL within that window executes; after the window expires the pending confirmation resets:

```python
from syrin.remote_config import RemoteCommandConfig

remote = RemoteConfig(
    ...,
    command_config=RemoteCommandConfig(
        kill_requires_confirmation=True,     # default
        require_signed_commands=True,        # Ed25519 signed commands only
        audit_all_commands=True,             # log every attempt
    ),
)
```

---

## Audit Log

Every command attempt — whether accepted or rejected — is recorded as a `CommandAuditEntry`. The entry has five fields: `command` is the `RemoteCommand` that was attempted, `timestamp` is an ISO-8601 UTC string, `actor_id` identifies the sender (from the `changed_by` field), `success` is a boolean indicating whether the command executed, and `reason` explains the rejection when `success` is `False`.

Retrieve the audit log:

```python
processor = agent._remote_command_processor
for entry in processor.audit_log():
    print(f"{entry.timestamp}  {entry.command}  actor={entry.actor_id}  ok={entry.success}")
```

---

## Agent Isolation

Each `RemoteConfig` instance is scoped to a single `agent_id`. Agents with different `agent_id` values are completely isolated — a config push addressed to `"agent-A"` never reaches `"agent-B"`, even when both share the same remote URL.

```python
agent_a = ResearchAgent(
    remote_config=RemoteConfig(url="...", agent_id="research-prod")
)
agent_b = WriterAgent(
    remote_config=RemoteConfig(url="...", agent_id="writer-prod")
)
# Pushing to research-prod has no effect on writer-prod.
```

---

## Hooks

Six hooks cover the full config lifecycle. `Hook.CONFIG_RECEIVED` fires when a new config payload arrives from the remote source — before any validation or application. `Hook.CONFIG_APPLIED` fires after a change is successfully applied. `Hook.CONFIG_ROLLBACK` fires when a config version is rolled back. `Hook.CONFIG_REJECTED` fires when a field change is blocked by access control or a validator — this is your signal that something tried to change something it shouldn't.

On the command side, `Hook.COMMAND_EXECUTED` fires when a remote command is accepted and runs successfully, and `Hook.COMMAND_REJECTED` fires when a command is blocked (unsigned, wrong state, or in the wrong confirmation window).

---

## What's Next?

- [Agent Registry](/agent-registry) — register, list, and control agents at runtime
- [Hooks](/debugging/hooks) — subscribe to `CONFIG_APPLIED` and `COMMAND_EXECUTED` for monitoring
- [Security: Agent Identity](/security/agent-identity) — Ed25519 signed commands
