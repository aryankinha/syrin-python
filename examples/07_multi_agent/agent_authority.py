"""Agent authority — role-based control actions with SwarmAuthorityGuard.

Shows how OrchestratorAgent controls WorkerAgents using the authority
guard (RBAC), and what happens when a WorkerAgent tries to control the
orchestrator — AgentPermissionError is raised.

Key concepts:
  - SwarmAuthorityGuard(roles={...}, teams={...})
  - SwarmController(actor_id=..., guard=..., state_registry=..., task_registry=...)
  - ctrl.pause_agent(worker_id), ctrl.resume_agent(worker_id)
  - ctrl.change_context(worker_id, new_context)
  - ctrl.read_agent_state(worker_id) → AgentStateSnapshot
  - AgentPermissionError — raised when unauthorised agent attempts control
  - DelegationScope — grant temporary authority

Run:
    uv run python examples/agent_authority.py
"""

from __future__ import annotations

import asyncio

from syrin.enums import AgentPermission, AgentRole, AgentStatus, DelegationScope
from syrin.swarm import (
    AgentPermissionError,
    AgentStateSnapshot,
    SwarmAuthorityGuard,
    SwarmController,
)

# ── Helper: build a minimal state + task registry ────────────────────────────


def _make_state(agent_id: str, role: AgentRole) -> AgentStateSnapshot:
    """Build a minimal AgentStateSnapshot for an agent."""
    return AgentStateSnapshot(
        agent_id=agent_id,
        status=AgentStatus.RUNNING,
        role=role,
        last_output_summary="",
        cost_spent=0.0,
        task="Process task",
        context_override=None,
        supervisor_id=None,
    )


# ── Example 1: Orchestrator pauses and resumes a worker ───────────────────────
#
# OrchestratorAgent has AgentRole.ORCHESTRATOR and has WorkerAgent in its team.
# It can pause, resume, change_context, and kill any agent in its team.


async def example_orchestrator_controls_worker() -> None:
    print("\n── Example 1: Orchestrator controls worker ───────────────────────")

    # Set up roles and teams
    guard = SwarmAuthorityGuard(
        roles={
            "orchestrator-1": AgentRole.ORCHESTRATOR,
            "worker-1": AgentRole.WORKER,
            "worker-2": AgentRole.WORKER,
        },
        teams={
            "orchestrator-1": ["worker-1", "worker-2"],  # orchestrator manages these workers
        },
    )

    # State and task registries
    state: dict[str, AgentStateSnapshot] = {
        "worker-1": _make_state("worker-1", AgentRole.WORKER),
        "worker-2": _make_state("worker-2", AgentRole.WORKER),
    }
    tasks: dict[str, asyncio.Task[object]] = {}  # no real tasks in this example

    # Orchestrator controller
    ctrl = SwarmController(
        actor_id="orchestrator-1",
        guard=guard,
        state_registry=state,
        task_registry=tasks,
    )

    # Pause worker-1
    await ctrl.pause_agent("worker-1")
    print(f"  worker-1 status after pause:  {state['worker-1'].status}")

    # Resume worker-1
    await ctrl.resume_agent("worker-1")
    print(f"  worker-1 status after resume: {state['worker-1'].status}")

    # Change context on worker-2 (inject new instructions)
    await ctrl.change_context("worker-2", "Focus on healthcare sector analysis only")
    print(f"  worker-2 context override: '{state['worker-2'].context_override}'")

    # Read worker-2 state
    snap = await ctrl.read_agent_state("worker-2")
    print(f"  worker-2 snapshot: id={snap.agent_id}  status={snap.status}  role={snap.role}")

    # Audit log
    audit = guard.audit_log()
    print(f"\n  Audit log ({len(audit)} entries):")
    for entry in audit:
        print(f"    actor={entry.actor_id}  target={entry.target_id}  action={entry.action}")


# ── Example 2: AgentPermissionError when worker tries to control orchestrator ──


async def example_worker_denied() -> None:
    print("\n── Example 2: Worker denied — AgentPermissionError ─────────────")

    guard = SwarmAuthorityGuard(
        roles={
            "orchestrator-1": AgentRole.ORCHESTRATOR,
            "worker-1": AgentRole.WORKER,
        },
        teams={"orchestrator-1": ["worker-1"]},
    )

    state: dict[str, AgentStateSnapshot] = {
        "orchestrator-1": _make_state("orchestrator-1", AgentRole.ORCHESTRATOR),
    }

    # Worker controller — actor is worker-1
    worker_ctrl = SwarmController(
        actor_id="worker-1",
        guard=guard,
        state_registry=state,
        task_registry={},
    )

    # Worker attempts to pause orchestrator — should be denied
    try:
        await worker_ctrl.pause_agent("orchestrator-1")
        print("  ERROR: pause should have been denied")
    except AgentPermissionError as e:
        print("  AgentPermissionError caught!")
        print(f"    actor_id:         {e.actor_id}")
        print(f"    target_id:        {e.target_id}")
        print(f"    attempted_action: {e.attempted_action}")
        print(f"    reason:           {e.reason}")

    # Worker attempts to read orchestrator state — also denied (worker has no READ)
    try:
        await worker_ctrl.read_agent_state("orchestrator-1")
        print("  ERROR: read should have been denied")
    except AgentPermissionError as e:
        print(f"\n  AgentPermissionError on read: {e.attempted_action}")


# ── Example 3: Permission check without raising ───────────────────────────────


async def example_permission_check() -> None:
    print("\n── Example 3: guard.check() — non-raising permission test ──────")

    guard = SwarmAuthorityGuard(
        roles={
            "admin-1": AgentRole.ADMIN,
            "orch-1": AgentRole.ORCHESTRATOR,
            "worker-1": AgentRole.WORKER,
        },
        teams={"orch-1": ["worker-1"]},
    )

    checks = [
        ("admin-1", AgentPermission.CONTROL, "worker-1", True),  # admin can do anything
        ("orch-1", AgentPermission.CONTROL, "worker-1", True),  # orch controls team
        ("orch-1", AgentPermission.CONTROL, "admin-1", False),  # orch can't control admin
        ("worker-1", AgentPermission.CONTROL, "orch-1", False),  # worker can't control orch
        ("worker-1", AgentPermission.SIGNAL, "orch-1", True),  # worker can signal
        ("worker-1", AgentPermission.READ, "orch-1", False),  # worker can't read
    ]

    print(f"  {'Actor':<12} {'Permission':<12} {'Target':<12} {'Expected':<10} Result")
    for actor, perm, target, expected in checks:
        result = guard.check(actor, perm, target)
        status = "PASS" if result == expected else "MISMATCH"
        print(f"  {actor:<12} {perm!s:<12} {target:<12} {str(expected):<10} {result}  [{status}]")


# ── Example 4: Delegation — grant temporary authority ─────────────────────────
#
# An orchestrator can delegate CONTROL permission to another agent for
# the duration of the current swarm run.


async def example_delegation() -> None:
    print("\n── Example 4: Delegation of authority ───────────────────────────")

    guard = SwarmAuthorityGuard(
        roles={
            "orchestrator-1": AgentRole.ORCHESTRATOR,
            "supervisor-1": AgentRole.SUPERVISOR,
            "worker-1": AgentRole.WORKER,
        },
        teams={"orchestrator-1": ["supervisor-1", "worker-1"]},
    )

    # Before delegation: supervisor-1 cannot change context on worker-1
    # (supervisor can only CONTROL = pause/resume, not CONTEXT)
    can_context_before = guard.check("supervisor-1", AgentPermission.CONTEXT, "worker-1")
    print(f"  Before delegation — supervisor can CONTEXT worker: {can_context_before}")

    # Delegate CONTEXT permission from orchestrator to supervisor
    guard.delegate(
        delegator_id="orchestrator-1",
        delegate_id="supervisor-1",
        permissions=[AgentPermission.CONTEXT],
        scope=DelegationScope.CURRENT_RUN,
    )

    # After delegation: supervisor-1 now has CONTEXT permission
    can_context_after = guard.check("supervisor-1", AgentPermission.CONTEXT, "worker-1")
    print(f"  After delegation  — supervisor can CONTEXT worker: {can_context_after}")

    # Revoke delegation
    guard.revoke_delegation("orchestrator-1", "supervisor-1")
    can_context_revoked = guard.check("supervisor-1", AgentPermission.CONTEXT, "worker-1")
    print(f"  After revocation  — supervisor can CONTEXT worker: {can_context_revoked}")


# ── Main ──────────────────────────────────────────────────────────────────────


async def main() -> None:
    await example_orchestrator_controls_worker()
    await example_worker_denied()
    await example_permission_check()
    await example_delegation()
    print("\nAll agent authority examples completed.")


if __name__ == "__main__":
    asyncio.run(main())
