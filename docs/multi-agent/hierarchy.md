---
title: Hierarchical Agent Composition
description: Agent.team, parent-child hierarchies, supervisor_id, authority chain inheritance, and the company org-chart pattern
weight: 77
---

## Overview

syrin supports hierarchical agent composition through `Agent.team`.  Setting `team` on an agent class declares that it manages a group of child agents.  When placed in a `Swarm`, the parent automatically spawns its team members and gains `CONTROL` + `CONTEXT` permissions over them.

## `Agent.team` — Declare a Team

```python
from syrin import Agent, Model
from syrin.enums import AgentRole

class BackendEngineer(Agent):
    model = Model.mock()
    system_prompt = "Implement backend services."

class FrontendEngineer(Agent):
    model = Model.mock()
    system_prompt = "Implement frontend components."

class EngineeringLead(Agent):
    model = Model.mock()
    system_prompt = "Coordinate engineering tasks."
    team = [BackendEngineer, FrontendEngineer]   # ClassVar
```

`team` is a `ClassVar[list[type[Agent]]]`.  It is read by the `Swarm` at construction time.

## How Swarm Expands the Team

When a `Swarm` is constructed with `agents=[EngineeringLead()]`, it:

1. Detects `EngineeringLead.team = [BackendEngineer, FrontendEngineer]`.
2. Instantiates each team member.
3. Appends them to `swarm._agents`.
4. Sets `member._supervisor_id = parent.agent_id` on each member.
5. Records `swarm._team_map[parent_id] = [member_ids]` for the authority system.

Nesting is recursive: if `BackendEngineer.team = [DatabaseEngineer]`, `DatabaseEngineer` is also expanded and its `_supervisor_id` points to `BackendEngineer`.

## Company Org-Chart Example

```python
import asyncio
from syrin import Agent, Budget, Model
from syrin.response import Response
from syrin.swarm import Swarm

class DatabaseEngineer(Agent):
    model = Model.mock()
    system_prompt = "Design and implement database schemas."

class BackendEngineer(Agent):
    model = Model.mock()
    system_prompt = "Implement API endpoints and business logic."
    team = [DatabaseEngineer]

class FrontendEngineer(Agent):
    model = Model.mock()
    system_prompt = "Build UI components and user flows."

class CTO(Agent):
    model = Model.mock()
    system_prompt = "Define technical strategy and architecture."
    team = [BackendEngineer, FrontendEngineer]

class CEO(Agent):
    model = Model.mock()
    system_prompt = "Set company direction and priorities."
    team = [CTO]

async def main() -> None:
    # Swarm expands: CEO → CTO → [BackendEngineer → DatabaseEngineer, FrontendEngineer]
    swarm = Swarm(
        agents=[CEO()],
        goal="Build the new product feature",
        budget=Budget(max_cost=10.00),
    )
    result = await swarm.run()
    print(result.content)

asyncio.run(main())
```

The swarm runs all expanded agents concurrently (PARALLEL topology).  Each agent in the hierarchy has its `_supervisor_id` set.

## Automatic Permission Grants

When the swarm expands the team, `SwarmAuthorityGuard` is configured automatically:

- A parent agent gets `AgentRole.SUPERVISOR` (or `ORCHESTRATOR` if it has a `team`).
- Team members get `AgentRole.WORKER`.
- The parent can issue `CONTROL` and `CONTEXT` actions on its direct reports.

```python
from syrin.swarm import SwarmAuthorityGuard
from syrin.enums import AgentPermission

guard = SwarmAuthorityGuard(
    roles={
        "ceo": AgentRole.ORCHESTRATOR,
        "cto": AgentRole.SUPERVISOR,
        "backend_engineer": AgentRole.WORKER,
    },
    teams={
        "ceo": ["cto"],
        "cto": ["backend_engineer"],
    },
)

# CEO can control CTO
guard.require("ceo", AgentPermission.CONTROL, "cto")   # passes

# CTO can control BackendEngineer
guard.require("cto", AgentPermission.CONTROL, "backend_engineer")  # passes

# BackendEngineer cannot control CTO
guard.require("backend_engineer", AgentPermission.CONTROL, "cto")  # raises AgentPermissionError
```

## Reading `supervisor_id` from `AgentStateSnapshot`

`AgentStateSnapshot.supervisor_id` tells you which agent manages this one:

```python
from syrin.swarm import SwarmController, SwarmAuthorityGuard, AgentStateSnapshot
from syrin.enums import AgentRole, AgentStatus

state = {
    "backend_engineer": AgentStateSnapshot(
        agent_id="backend_engineer",
        status=AgentStatus.RUNNING,
        role=AgentRole.WORKER,
        last_output_summary="Implementing API...",
        cost_spent=0.10,
        task="Build /api/users endpoint",
        context_override=None,
        supervisor_id="cto",         # ← set by Swarm._expand_team_agents()
    )
}
```

Access it to build observability dashboards or log the authority chain.

## Delegation

A parent can temporarily grant permissions to a peer agent via `guard.delegate()`:

```python
from syrin.enums import AgentPermission, DelegationScope

# CEO delegates CONTROL to CMO for this run
guard.delegate(
    delegator_id="ceo",
    delegate_id="cmo",
    permissions=[AgentPermission.CONTROL],
    scope=DelegationScope.CURRENT_RUN,
)

# CMO can now control CTO
guard.require("cmo", AgentPermission.CONTROL, "cto")  # passes

# Revoke later
guard.revoke_delegation(delegator_id="ceo", delegate_id="cmo")
```

> **Note:** `DelegationScope.PERMANENT` raises `NotImplementedError` in v0.11.0.  Permanent delegation arrives in v0.12.0.

Delegation rules:
- Only `ADMIN` role can delegate `AgentPermission.ADMIN`.
- Any agent can delegate permissions they currently hold (except `ADMIN`).

## Authority Chain Inheritance

The authority chain flows top-down through `supervisor_id`:

```
CEO (ORCHESTRATOR)
  └── CTO (SUPERVISOR)
        ├── BackendEngineer (WORKER, supervisor_id="cto")
        │     └── DatabaseEngineer (WORKER, supervisor_id="backend_engineer")
        └── FrontendEngineer (WORKER, supervisor_id="cto")
```

A supervisor can act on direct reports.  Skip-level control requires delegation or an `ADMIN` role.  Unknown actors are treated as `WORKER` (minimal permissions).

## Team Expansion Details

`Swarm._expand_team_agents()` processes the queue iteratively (breadth-first) to handle arbitrary nesting depth.  It sets `_supervisor_id` using `object.__setattr__` to work with frozen dataclasses or agents without arbitrary `__setattr__`.

Duplicate agent IDs are detected via `processed_ids` to prevent infinite loops in circular team definitions.

## See Also

- [Authority](/multi-agent/authority)
- [Swarm](/multi-agent/swarm)
- [Budget delegation](/multi-agent/budget-delegation)
