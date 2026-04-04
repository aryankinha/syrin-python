"""Tests for hierarchical authority — Phase 5, P5-T5."""

from __future__ import annotations

import pytest

from syrin.enums import AgentPermission, AgentRole, AgentStatus
from syrin.swarm._authority import AgentPermissionError, SwarmAuthorityGuard
from syrin.swarm._control import AgentStateSnapshot

# ---------------------------------------------------------------------------
# P5-T5-1: Agent class attribute `team` is accessible
# ---------------------------------------------------------------------------


def test_agent_team_class_attribute() -> None:
    """Agent subclass with team class attribute — attribute accessible."""
    from syrin import Agent, Model

    class WorkerA(Agent):
        model = Model.Almock()
        system_prompt = "Worker A"

    class WorkerB(Agent):
        model = Model.Almock()
        system_prompt = "Worker B"

    class SupervisorAgent(Agent):
        model = Model.Almock()
        system_prompt = "Supervisor"
        team: list[type[Agent]] = [WorkerA, WorkerB]

    assert hasattr(SupervisorAgent, "team")
    assert WorkerA in SupervisorAgent.team
    assert WorkerB in SupervisorAgent.team


# ---------------------------------------------------------------------------
# P5-T5-2: Guard with team relationships grants SUPERVISOR control
# ---------------------------------------------------------------------------


def test_guard_supervisor_controls_team() -> None:
    """SwarmAuthorityGuard with team dict grants SUPERVISOR CONTROL over team."""
    guard = SwarmAuthorityGuard(
        roles={"sup": AgentRole.SUPERVISOR, "w1": AgentRole.WORKER},
        teams={"sup": ["w1"]},
    )
    assert guard.check("sup", AgentPermission.CONTROL, "w1") is True


# ---------------------------------------------------------------------------
# P5-T5-3: SUPERVISOR role gives CONTROL permission over team workers
# ---------------------------------------------------------------------------


def test_supervisor_gets_control_over_team_workers() -> None:
    """Supervisor in teams dict has CONTROL permission on listed workers."""
    guard = SwarmAuthorityGuard(
        roles={
            "sup": AgentRole.SUPERVISOR,
            "w1": AgentRole.WORKER,
            "w2": AgentRole.WORKER,
        },
        teams={"sup": ["w1", "w2"]},
    )
    assert guard.check("sup", AgentPermission.CONTROL, "w1") is True
    assert guard.check("sup", AgentPermission.CONTROL, "w2") is True


# ---------------------------------------------------------------------------
# P5-T5-4: AgentStateSnapshot.supervisor_id set for team workers
# ---------------------------------------------------------------------------


def test_snapshot_supervisor_id_set() -> None:
    """AgentStateSnapshot.supervisor_id is set for workers in a team."""
    snap = AgentStateSnapshot(
        agent_id="w1",
        status=AgentStatus.RUNNING,
        role=AgentRole.WORKER,
        last_output_summary="output",
        cost_spent=0.1,
        task="analyse",
        context_override=None,
        supervisor_id="sup",
    )
    assert snap.supervisor_id == "sup"


# ---------------------------------------------------------------------------
# P5-T5-5: 3-level hierarchy: ADMIN → SUPERVISOR → WORKER permission chain
# ---------------------------------------------------------------------------


def test_three_level_hierarchy_permissions() -> None:
    """3-level hierarchy: ADMIN controls all, SUPERVISOR controls team, WORKER cannot control."""
    guard = SwarmAuthorityGuard(
        roles={
            "admin": AgentRole.ADMIN,
            "sup": AgentRole.SUPERVISOR,
            "w1": AgentRole.WORKER,
        },
        teams={"sup": ["w1"]},
    )
    # ADMIN can control anyone
    assert guard.check("admin", AgentPermission.CONTROL, "sup") is True
    assert guard.check("admin", AgentPermission.CONTROL, "w1") is True
    # SUPERVISOR can control team member
    assert guard.check("sup", AgentPermission.CONTROL, "w1") is True
    # WORKER cannot control anyone
    assert guard.check("w1", AgentPermission.CONTROL, "sup") is False
    assert guard.check("w1", AgentPermission.CONTROL, "admin") is False


# ---------------------------------------------------------------------------
# P5-T5-6: Supervisor cannot control agents not in their team
# ---------------------------------------------------------------------------


def test_supervisor_cannot_control_outside_team() -> None:
    """Supervisor cannot control an agent not listed in their team."""
    guard = SwarmAuthorityGuard(
        roles={
            "sup": AgentRole.SUPERVISOR,
            "w1": AgentRole.WORKER,
            "w2": AgentRole.WORKER,
        },
        teams={"sup": ["w1"]},  # w2 is NOT in sup's team
    )
    with pytest.raises(AgentPermissionError):
        guard.require("sup", AgentPermission.CONTROL, "w2")


# ---------------------------------------------------------------------------
# P5-T5-7: Admin can control anyone regardless of team
# ---------------------------------------------------------------------------


def test_admin_can_control_anyone() -> None:
    """Admin can control any agent, even if not in a team."""
    guard = SwarmAuthorityGuard(
        roles={"admin": AgentRole.ADMIN, "w1": AgentRole.WORKER},
        teams={},  # no teams at all
    )
    guard.require("admin", AgentPermission.CONTROL, "w1")
    guard.require("admin", AgentPermission.SPAWN, "w1")
    guard.require("admin", AgentPermission.ADMIN, "w1")
