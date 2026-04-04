---
title: Agent Authority
description: Role-based access control and permission delegation for multi-agent swarms
weight: 77
---

## Who's in Charge?

In a multi-agent system, you don't want every agent to be able to pause, kill, or reprogram every other agent. That's chaos. The authority system gives you role-based access control: some agents can control others, some can only signal, some can read state. You define the rules, and the guard enforces them.

## Roles

Every agent in a swarm has an `AgentRole`. There are four:

`AgentRole.ADMIN` has full control over all agents and swarm settings. Nothing is off-limits.

`AgentRole.ORCHESTRATOR` can spawn agents, change context, and issue control commands — but only on agents in its assigned team.

`AgentRole.SUPERVISOR` can pause and resume agents in its assigned team. It can't change context or spawn.

`AgentRole.WORKER` is the standard role. Workers can execute tasks and send A2A signals, but they can't control other agents. Unknown actors are treated as WORKER by default.

## Permissions

Roles map to sets of `AgentPermission` values:

`AgentPermission.READ` — Read another agent's state and output.

`AgentPermission.SIGNAL` — Send A2A messages to another agent. Every role has this.

`AgentPermission.CONTROL` — Issue control commands: pause, resume, kill, skip.

`AgentPermission.CONTEXT` — Read another agent's full context window.

`AgentPermission.SPAWN` — Spawn child agents on behalf of another agent.

`AgentPermission.ADMIN` — All of the above.

The default rules: ADMIN has every permission on every agent. ORCHESTRATOR has CONTROL, CONTEXT, and SPAWN on agents in its team. SUPERVISOR has CONTROL on agents in its team. WORKER has SIGNAL only.

## SwarmAuthorityGuard

```python
from syrin.swarm import SwarmAuthorityGuard
from syrin.enums import AgentRole, AgentPermission

guard = SwarmAuthorityGuard(
    roles={
        "supervisor-1": AgentRole.SUPERVISOR,
        "worker-1":     AgentRole.WORKER,
        "worker-2":     AgentRole.WORKER,
    },
    teams={
        "supervisor-1": ["worker-1", "worker-2"],  # supervisor's team
    },
)

# Check without raising — returns True/False
if guard.check("supervisor-1", AgentPermission.CONTROL, "worker-1"):
    print("Permission granted")

# Require — raises AgentPermissionError if denied
guard.require("supervisor-1", AgentPermission.CONTROL, "worker-1")
```

`check()` returns `True` or `False`. Use it when you want to branch on permission. `require()` raises `AgentPermissionError` if the permission is denied — use it when a denied permission should stop execution.

## Permission Delegation

Temporarily grant permissions to another agent for the current run:

```python
from syrin.enums import DelegationScope

# Grant the CMO the ability to issue control commands for this run
guard.delegate(
    delegator_id="ceo",
    delegate_id="cmo",
    permissions=[AgentPermission.CONTROL],
    scope=DelegationScope.CURRENT_RUN,
)

# Revoke when done
guard.revoke_delegation(delegator_id="ceo", delegate_id="cmo")
```

Two delegation rules: only an `ADMIN` can delegate `AgentPermission.ADMIN`. Any agent can delegate permissions it already holds (except ADMIN).

`DelegationScope.PERMANENT` raises `NotImplementedError` in v0.11.0 — permanent delegation arrives in v0.12.0.

## Hooks

Three hooks fire for authority events:

`Hook.AGENT_CONTROL_ACTION` fires after a successful `record_action()` call.

`Hook.AGENT_PERMISSION_DENIED` fires when `require()` denies a permission.

`Hook.AGENT_DELEGATION` fires when `delegate()` succeeds.

## Audit Log

Every successful control action is recorded and retrievable:

```python
guard.record_action("supervisor-1", "worker-1", "pause")
log = guard.audit_log()
# [AuditEntry(actor_id="supervisor-1", target_id="worker-1", action="pause", timestamp=...)]
```

Use this for compliance, debugging, or tracing how agents interacted.

## SwarmController

`SwarmController` is the high-level API for taking control actions — it combines the guard check with the actual state modification:

```python
from syrin.swarm import SwarmController, SwarmAuthorityGuard, AgentStateSnapshot
from syrin.enums import AgentRole, AgentStatus

guard = SwarmAuthorityGuard(
    roles={"sup": AgentRole.SUPERVISOR, "w1": AgentRole.WORKER},
    teams={"sup": ["w1"]},
)

state = {
    "w1": AgentStateSnapshot(
        agent_id="w1",
        status=AgentStatus.RUNNING,
        role=AgentRole.WORKER,
        last_output_summary="Processing...",
        cost_spent=0.10,
        task="analyse data",
        context_override=None,
        supervisor_id="sup",
    )
}

ctrl = SwarmController(
    actor_id="sup",
    guard=guard,
    state_registry=state,
    task_registry={},
)

await ctrl.pause_agent("w1")
await ctrl.change_context("w1", "Be more concise")
await ctrl.resume_agent("w1")
snap = await ctrl.read_agent_state("w1")
```

Five control methods are available. `pause_agent(id)` requires CONTROL permission and sets the agent's status to PAUSED. `resume_agent(id)` requires CONTROL and returns the agent to RUNNING. `skip_agent(id)` requires CONTROL and sets status to IDLE, cancelling the current task. `kill_agent(id)` requires CONTROL and sets status to KILLED. `change_context(id, ctx)` requires CONTROL and sets the agent's `context_override` string. `read_agent_state(id)` requires READ permission and returns an `AgentStateSnapshot`.

The `AgentStateSnapshot` has these fields: `agent_id`, `status` (an `AgentStatus` value), `role` (an `AgentRole` value), `last_output_summary` (always 500 characters or fewer), `cost_spent`, `task`, `context_override`, and `supervisor_id`.

## See Also

- [Swarm](/multi-agent/swarm) — Parallel, consensus, and reflection topologies
- [MonitorLoop](/multi-agent/monitor-loop) — Async supervisor loop
- [Broadcast](/multi-agent/broadcast) — Publish events across the swarm
