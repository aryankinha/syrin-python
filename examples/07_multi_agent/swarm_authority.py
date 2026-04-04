"""Authority and control — production swarms with enforcement boundaries.

In a research demo, any agent can call any action. In production, that is a
liability. A worker agent should not be able to pause another worker. Only
a supervisor should be able to redirect an agent mid-run. An admin is the
only one who can terminate a pipeline.

SwarmAuthorityGuard enforces these boundaries through role-based access control.
SwarmController translates allowed actions into state changes. BroadcastBus
lets agents signal phase transitions to downstream consumers. MonitorLoop gives
a supervisor agent eyes on all active workers in real time.

Use this module when:
  - Your swarm runs in production and you need audit-grade control boundaries
  - Human-in-the-loop approval gates require pausing and resuming specific agents
  - A pipeline stage completion needs to notify downstream agents reliably
  - You want to watch agent output in real time and intervene if quality drops

Run:
    uv run python examples/07_multi_agent/swarm_authority.py
"""

from __future__ import annotations

import asyncio

from syrin.enums import (
    AgentPermission,
    AgentRole,
    AgentStatus,
    DelegationScope,
    Hook,
    MonitorEventType,
)
from syrin.swarm import (
    AgentPermissionError,
    AgentStateSnapshot,
    AuditEntry,
    BroadcastBus,
    BroadcastConfig,
    BroadcastEvent,
    MonitorEvent,
    MonitorLoop,
    SwarmAuthorityGuard,
    SwarmController,
)

# ── Demo 1: A supervisor managing their team ──────────────────────────────────
#
# A supervisor can issue control actions to the workers they manage.
# They cannot reach outside their team, and workers cannot control each other.
# This mirrors how a real operations team is structured: leads manage their
# direct reports; peers do not direct each other.


def demo_authority() -> None:
    """Supervisor can control their own workers but not other teams' workers."""
    print("\n=== Demo 1: Role-based authority — supervisor managing their team ===")

    fired: list[tuple[Hook, object]] = []

    guard = SwarmAuthorityGuard(
        roles={
            "admin-agent": AgentRole.ADMIN,
            "supervisor-1": AgentRole.SUPERVISOR,
            "worker-1": AgentRole.WORKER,
            "worker-2": AgentRole.WORKER,
        },
        teams={
            "supervisor-1": ["worker-1"],  # supervisor-1 is responsible for worker-1 only
        },
        fire_event_fn=lambda h, d: fired.append((h, d)),
    )

    # Supervisor can control their direct report
    guard.require("supervisor-1", AgentPermission.CONTROL, "worker-1")
    print("  supervisor-1 → worker-1:  CONTROL granted (direct report)")

    # Supervisor cannot reach into another team
    try:
        guard.require("supervisor-1", AgentPermission.CONTROL, "worker-2")
    except AgentPermissionError as e:
        print(f"  supervisor-1 → worker-2:  DENIED — {e.reason}")

    # Workers cannot control each other — peers have no authority over peers
    try:
        guard.require("worker-1", AgentPermission.CONTROL, "worker-2")
    except AgentPermissionError as e:
        print(f"  worker-1 → worker-2:      DENIED — {e.reason}")

    # Admin can always act on any agent in the swarm
    guard.require("admin-agent", AgentPermission.ADMIN, "worker-1")
    print("  admin-agent → worker-1:   ADMIN granted (unrestricted)")

    # Every action is recorded for compliance and debugging
    guard.record_action("supervisor-1", "worker-1", "pause")
    log: list[AuditEntry] = guard.audit_log()
    print(f"  Audit log: {len(log)} entry — action={log[-1].action!r} by {log[-1].actor_id!r}")
    print(f"  Hooks fired: {[h.value for h, _ in fired]}")


# ── Demo 2: A senior agent temporarily delegating control during an incident ──
#
# Sometimes a senior agent needs to hand off authority temporarily — for example,
# when an on-call engineer grants an automated incident responder the ability to
# pause agents while the incident is being handled. The delegation is scoped to
# the current run and can be revoked as soon as the incident resolves.


def demo_delegation() -> None:
    """Admin delegates CONTROL to an orchestrator for the duration of a run."""
    print("\n=== Demo 2: Delegation — temporary authority grant during an incident ===")

    guard = SwarmAuthorityGuard(
        roles={
            "admin-agent": AgentRole.ADMIN,
            "incident-responder": AgentRole.ORCHESTRATOR,
            "worker-3": AgentRole.WORKER,
        },
        teams={"incident-responder": []},
    )

    # Before delegation: the incident responder cannot control workers
    can_before = guard.check("incident-responder", AgentPermission.CONTROL, "worker-3")
    print(f"  Before delegation: incident-responder CONTROL worker-3 = {can_before}")

    # Admin grants temporary CONTROL authority scoped to the current run
    guard.delegate(
        delegator_id="admin-agent",
        delegate_id="incident-responder",
        permissions=[AgentPermission.CONTROL],
        scope=DelegationScope.CURRENT_RUN,
    )

    can_after = guard.check("incident-responder", AgentPermission.CONTROL, "worker-3")
    print(f"  During incident:   incident-responder CONTROL worker-3 = {can_after}")

    # Incident resolved — revoke the delegation
    guard.revoke_delegation(delegator_id="admin-agent", delegate_id="incident-responder")
    can_revoked = guard.check("incident-responder", AgentPermission.CONTROL, "worker-3")
    print(f"  After resolution:  incident-responder CONTROL worker-3 = {can_revoked}")


# ── Demo 3: A supervisor pausing an agent that has gone off-track ─────────────
#
# During a live run, a supervisor observes that a worker is hallucinating or
# pursuing an irrelevant direction. The supervisor uses SwarmController to
# pause the worker, inject a corrective context override, and then resume it.
# The full action sequence is recorded in the audit log.


async def demo_controller() -> None:
    """Supervisor pauses an off-track worker and redirects its context."""
    print("\n=== Demo 3: Controller — pause, redirect, and resume a worker ===")

    guard = SwarmAuthorityGuard(
        roles={
            "supervisor-1": AgentRole.SUPERVISOR,
            "worker-1": AgentRole.WORKER,
        },
        teams={"supervisor-1": ["worker-1"]},
    )

    state: dict[str, AgentStateSnapshot] = {
        "worker-1": AgentStateSnapshot(
            agent_id="worker-1",
            status=AgentStatus.RUNNING,
            role=AgentRole.WORKER,
            last_output_summary="Analysing all market segments globally...",
            cost_spent=0.05,
            task="analyse quarterly report",
            context_override=None,
            supervisor_id="supervisor-1",
        )
    }

    ctrl = SwarmController(
        actor_id="supervisor-1",
        guard=guard,
        state_registry=state,
        task_registry={},
    )

    snap = await ctrl.read_agent_state("worker-1")
    print(f"  Initial status:  {snap.status}")

    # Worker is going too broad — pause it before it wastes more budget
    await ctrl.pause_agent("worker-1")
    snap = await ctrl.read_agent_state("worker-1")
    print(f"  After pause:     {snap.status}")

    # Inject corrective context — narrow the worker's scope
    await ctrl.change_context("worker-1", "Focus exclusively on Q4 North America numbers")
    snap = await ctrl.read_agent_state("worker-1")
    print(f"  Context override: {snap.context_override!r}")

    # Resume — worker will pick up with the corrected context
    await ctrl.resume_agent("worker-1")
    snap = await ctrl.read_agent_state("worker-1")
    print(f"  After resume:    {snap.status}")

    audit = guard.audit_log()
    print(f"  Audit actions:   {[e.action for e in audit]}")


# ── Demo 4: Pipeline stage completion notifying downstream agents ──────────────
#
# When a research phase finishes, downstream agents (writers, reviewers, QA)
# need to know they can start their work. BroadcastBus delivers this signal
# to every subscriber simultaneously without the orchestrator needing to
# maintain a list of who to notify. Agents subscribe to the topics they care
# about; the publisher just broadcasts.


async def demo_broadcast() -> None:
    """Research phase completes and notifies all downstream pipeline agents."""
    print("\n=== Demo 4: Broadcast — pipeline stage completion notification ===")

    fired: list[tuple[Hook, object]] = []
    bus = BroadcastBus(
        config=BroadcastConfig(max_payload_bytes=4096),
        fire_event_fn=lambda h, d: fired.append((h, d)),
    )

    received: list[BroadcastEvent] = []

    # Writer and QA agent subscribe to research events
    bus.subscribe("writer-agent", "research.*", received.append)
    # Ops monitor subscribes to all pipeline events
    bus.subscribe("ops-monitor", "*", received.append)

    # Research phase complete — broadcast to all research topic subscribers
    count = await bus.broadcast(
        "orchestrator",
        "research.done",
        {"phase": "research", "findings_count": 12, "quality_score": 0.91},
    )
    print(f"  'research.done' delivered to {count} subscribers")
    if received:
        print(f"  writer-agent received: {received[0].payload}")

    # Finance report arrives — only the wildcard subscriber (ops-monitor) gets this
    count2 = await bus.broadcast(
        "finance-agent",
        "finance.done",
        {"revenue": 1_200_000, "period": "Q4"},
    )
    print(f"  'finance.done' delivered to {count2} subscriber(s) (ops-monitor only)")
    print(f"  AGENT_BROADCAST hooks fired: {sum(1 for h, _ in fired if h == Hook.AGENT_BROADCAST)}")


# ── Demo 5: Quality monitor watching agent output in real time ────────────────
#
# A MonitorLoop polls active agents and surfaces events as they arrive —
# heartbeats when agents are running, OUTPUT_READY when output is available
# for review. A supervisor agent (or a human operator) can iterate over events
# and decide whether to intervene. This is the foundation for automated quality
# gates in production pipelines.


async def demo_monitor() -> None:
    """Ops monitor watches a worker agent and captures its output for review."""
    print("\n=== Demo 5: MonitorLoop — real-time output monitoring ===")

    events_seen: list[MonitorEvent] = []

    async with MonitorLoop(
        targets=["worker-1"],
        poll_interval=0.05,  # fast for demo; use longer intervals in production
        max_interventions=2,
    ) as monitor:
        # Simulate the worker agent completing a task and emitting output
        monitor.notify_agent_output("worker-1", "Q4 analysis complete: revenue up 18% YoY")

        async for event in monitor:
            events_seen.append(event)
            print(f"  [{event.event_type}] agent={event.agent_id}")

            if event.event_type == MonitorEventType.OUTPUT_READY:
                # Output is ready — review it and decide whether to accept or intervene
                print(f"  Output ready for review: {event.data['output']!r}")
                break

            if len(events_seen) >= 5:
                break

    print(f"  Total events observed: {len(events_seen)}")


# ── Main ──────────────────────────────────────────────────────────────────────


async def main() -> None:
    """Run all authority and control demonstrations."""
    demo_authority()
    demo_delegation()
    await demo_controller()
    await demo_broadcast()
    await demo_monitor()
    print("\nAll authority and control demos complete.")


if __name__ == "__main__":
    asyncio.run(main())
