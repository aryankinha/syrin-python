"""Tests for SwarmAuthorityGuard — Phase 5, P5-T1."""

from __future__ import annotations

import pytest

from syrin.enums import AgentPermission, AgentRole, Hook
from syrin.swarm._authority import (
    AgentPermissionError,
    AuditEntry,
    SwarmAuthorityGuard,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_guard(
    roles: dict[str, AgentRole] | None = None,
    teams: dict[str, list[str]] | None = None,
    fired: list[tuple[Hook, dict[str, object]]] | None = None,
) -> SwarmAuthorityGuard:
    """Build a guard with optional event capture."""
    events: list[tuple[Hook, dict[str, object]]] = fired if fired is not None else []

    def _fire(hook: Hook, data: dict[str, object]) -> None:
        events.append((hook, data))

    return SwarmAuthorityGuard(
        roles=roles or {},
        teams=teams or {},
        fire_event_fn=_fire,
    )


# ---------------------------------------------------------------------------
# P5-T1-1: WORKER cannot call control actions
# ---------------------------------------------------------------------------


def test_worker_cannot_control() -> None:
    """WORKER role cannot CONTROL another agent — raises AgentPermissionError."""
    guard = _make_guard(
        roles={"w1": AgentRole.WORKER, "w2": AgentRole.WORKER},
        teams={},
    )
    with pytest.raises(AgentPermissionError):
        guard.require("w1", AgentPermission.CONTROL, "w2")


# ---------------------------------------------------------------------------
# P5-T1-2: SUPERVISOR can pause agents in their team
# ---------------------------------------------------------------------------


def test_supervisor_can_control_team_member() -> None:
    """SUPERVISOR can CONTROL agents in their team."""
    guard = _make_guard(
        roles={"sup": AgentRole.SUPERVISOR, "w1": AgentRole.WORKER},
        teams={"sup": ["w1"]},
    )
    # Should not raise
    guard.require("sup", AgentPermission.CONTROL, "w1")


# ---------------------------------------------------------------------------
# P5-T1-3: SUPERVISOR cannot pause agents outside their team
# ---------------------------------------------------------------------------


def test_supervisor_cannot_control_outside_team() -> None:
    """SUPERVISOR cannot CONTROL an agent not in their team."""
    guard = _make_guard(
        roles={"sup": AgentRole.SUPERVISOR, "w1": AgentRole.WORKER, "w2": AgentRole.WORKER},
        teams={"sup": ["w1"]},
    )
    with pytest.raises(AgentPermissionError):
        guard.require("sup", AgentPermission.CONTROL, "w2")


# ---------------------------------------------------------------------------
# P5-T1-4: ORCHESTRATOR can change_context on spawned agents
# ---------------------------------------------------------------------------


def test_orchestrator_can_context_team_agent() -> None:
    """ORCHESTRATOR can CONTEXT on agents in their team."""
    guard = _make_guard(
        roles={"orch": AgentRole.ORCHESTRATOR, "w1": AgentRole.WORKER},
        teams={"orch": ["w1"]},
    )
    guard.require("orch", AgentPermission.CONTEXT, "w1")


# ---------------------------------------------------------------------------
# P5-T1-5: ADMIN can call any action on any agent
# ---------------------------------------------------------------------------


def test_admin_can_do_anything() -> None:
    """ADMIN can perform any action on any agent."""
    guard = _make_guard(
        roles={"admin": AgentRole.ADMIN, "w1": AgentRole.WORKER},
        teams={},
    )
    for perm in AgentPermission:
        guard.require("admin", perm, "w1")


# ---------------------------------------------------------------------------
# P5-T1-6: AgentPermissionError has correct attributes
# ---------------------------------------------------------------------------


def test_agent_permission_error_attributes() -> None:
    """AgentPermissionError has actor_id, target_id, attempted_action."""
    err = AgentPermissionError(
        actor_id="w1",
        target_id="w2",
        attempted_action="control",
        reason="insufficient role",
    )
    assert err.actor_id == "w1"
    assert err.target_id == "w2"
    assert err.attempted_action == "control"
    assert isinstance(str(err), str)


# ---------------------------------------------------------------------------
# P5-T1-7: Successful control action fires AGENT_CONTROL_ACTION hook
# ---------------------------------------------------------------------------


def test_record_action_fires_control_hook() -> None:
    """record_action fires Hook.AGENT_CONTROL_ACTION."""
    fired: list[tuple[Hook, dict[str, object]]] = []
    guard = _make_guard(
        roles={"sup": AgentRole.SUPERVISOR, "w1": AgentRole.WORKER},
        teams={"sup": ["w1"]},
        fired=fired,
    )
    guard.record_action("sup", "w1", "pause")
    assert any(h == Hook.AGENT_CONTROL_ACTION for h, _ in fired)
    hook_data = next(d for h, d in fired if h == Hook.AGENT_CONTROL_ACTION)
    assert hook_data["actor_id"] == "sup"
    assert hook_data["target_id"] == "w1"
    assert hook_data["action"] == "pause"


# ---------------------------------------------------------------------------
# P5-T1-8: Denied action fires AGENT_PERMISSION_DENIED hook
# ---------------------------------------------------------------------------


def test_denied_action_fires_permission_denied_hook() -> None:
    """require() on a denied action fires Hook.AGENT_PERMISSION_DENIED."""
    fired: list[tuple[Hook, dict[str, object]]] = []
    guard = _make_guard(
        roles={"w1": AgentRole.WORKER, "w2": AgentRole.WORKER},
        teams={},
        fired=fired,
    )
    with pytest.raises(AgentPermissionError):
        guard.require("w1", AgentPermission.CONTROL, "w2")
    assert any(h == Hook.AGENT_PERMISSION_DENIED for h, _ in fired)
    hook_data = next(d for h, d in fired if h == Hook.AGENT_PERMISSION_DENIED)
    assert hook_data["actor_id"] == "w1"
    assert hook_data["target_id"] == "w2"


# ---------------------------------------------------------------------------
# P5-T1-9: record_action writes AuditEntry
# ---------------------------------------------------------------------------


def test_record_action_writes_audit_entry() -> None:
    """record_action persists an AuditEntry in the audit log."""
    guard = _make_guard(
        roles={"sup": AgentRole.SUPERVISOR, "w1": AgentRole.WORKER},
        teams={"sup": ["w1"]},
    )
    guard.record_action("sup", "w1", "resume")
    log = guard.audit_log()
    assert len(log) == 1
    entry = log[0]
    assert isinstance(entry, AuditEntry)
    assert entry.actor_id == "sup"
    assert entry.target_id == "w1"
    assert entry.action == "resume"


# ---------------------------------------------------------------------------
# P5-T1-10: SwarmAuthorityGuard construction with event emitter
# ---------------------------------------------------------------------------


def test_guard_construction_with_event_emitter() -> None:
    """SwarmAuthorityGuard can be constructed with a fire_event_fn."""
    fired: list[tuple[Hook, dict[str, object]]] = []

    def emitter(hook: Hook, data: dict[str, object]) -> None:
        fired.append((hook, data))

    guard = SwarmAuthorityGuard(
        roles={"admin": AgentRole.ADMIN},
        teams={},
        fire_event_fn=emitter,
    )
    assert guard is not None
    guard.record_action("admin", "w1", "kill")
    assert len(fired) == 1


# ---------------------------------------------------------------------------
# Additional: check() returns bool without raising
# ---------------------------------------------------------------------------


def test_check_returns_false_for_worker() -> None:
    """check() returns False (no raise) when permission denied."""
    guard = _make_guard(
        roles={"w1": AgentRole.WORKER, "w2": AgentRole.WORKER},
    )
    assert guard.check("w1", AgentPermission.CONTROL, "w2") is False


def test_check_returns_true_for_admin() -> None:
    """check() returns True when permission granted."""
    guard = _make_guard(roles={"admin": AgentRole.ADMIN})
    assert guard.check("admin", AgentPermission.CONTROL, "anyone") is True


def test_unknown_actor_treated_as_worker() -> None:
    """Actor not in roles dict is treated as WORKER."""
    guard = _make_guard(
        roles={"w2": AgentRole.WORKER},
    )
    with pytest.raises(AgentPermissionError):
        guard.require("unknown_actor", AgentPermission.CONTROL, "w2")
