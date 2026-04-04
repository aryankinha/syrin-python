"""Tests for permission delegation — Phase 5, P5-T6."""

from __future__ import annotations

import pytest

from syrin.enums import AgentPermission, AgentRole, DelegationScope, Hook
from syrin.swarm._authority import AgentPermissionError, SwarmAuthorityGuard

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_guard(
    roles: dict[str, AgentRole] | None = None,
    teams: dict[str, list[str]] | None = None,
    fired: list[tuple[Hook, dict[str, object]]] | None = None,
) -> SwarmAuthorityGuard:
    events: list[tuple[Hook, dict[str, object]]] = fired if fired is not None else []

    def _fire(hook: Hook, data: dict[str, object]) -> None:
        events.append((hook, data))

    return SwarmAuthorityGuard(
        roles=roles or {},
        teams=teams or {},
        fire_event_fn=_fire,
    )


# ---------------------------------------------------------------------------
# P5-T6-1: delegate gives delegate_id the permission
# ---------------------------------------------------------------------------


def test_delegate_grants_permission() -> None:
    """After delegate(), CMO can perform CONTROL action."""
    guard = _make_guard(
        roles={"ceo": AgentRole.ADMIN, "cmo": AgentRole.ORCHESTRATOR, "w1": AgentRole.WORKER},
        teams={"ceo": ["cmo", "w1"], "cmo": []},
    )
    # cmo cannot control w1 before delegation (no team members)
    assert guard.check("cmo", AgentPermission.CONTROL, "w1") is False

    guard.delegate(
        delegator_id="ceo",
        delegate_id="cmo",
        permissions=[AgentPermission.CONTROL],
        scope=DelegationScope.CURRENT_RUN,
    )

    # After delegation, cmo can control w1
    assert guard.check("cmo", AgentPermission.CONTROL, "w1") is True


# ---------------------------------------------------------------------------
# P5-T6-2: revoke_delegation removes the granted permission
# ---------------------------------------------------------------------------


def test_revoke_delegation_removes_permission() -> None:
    """After revoke_delegation(), CMO loses the delegated permission."""
    guard = _make_guard(
        roles={"ceo": AgentRole.ADMIN, "cmo": AgentRole.ORCHESTRATOR, "w1": AgentRole.WORKER},
        teams={},
    )
    guard.delegate(
        delegator_id="ceo",
        delegate_id="cmo",
        permissions=[AgentPermission.CONTROL],
        scope=DelegationScope.CURRENT_RUN,
    )
    assert guard.check("cmo", AgentPermission.CONTROL, "w1") is True

    guard.revoke_delegation(delegator_id="ceo", delegate_id="cmo")

    assert guard.check("cmo", AgentPermission.CONTROL, "w1") is False


# ---------------------------------------------------------------------------
# P5-T6-3: DelegationScope.PERMANENT requires ADMIN role
# ---------------------------------------------------------------------------


def test_permanent_delegation_raises_not_implemented() -> None:
    """DelegationScope.PERMANENT raises AgentPermissionError for non-ADMIN roles."""
    guard = _make_guard(roles={"ceo": AgentRole.ADMIN, "cmo": AgentRole.ORCHESTRATOR})
    # Non-ADMIN (ORCHESTRATOR) cannot make permanent delegations
    with pytest.raises(AgentPermissionError):
        guard.delegate(
            delegator_id="cmo",
            delegate_id="w1",
            permissions=[AgentPermission.CONTROL],
            scope=DelegationScope.PERMANENT,
        )


def test_permanent_delegation_allowed_for_admin() -> None:
    """DelegationScope.PERMANENT succeeds when delegator has ADMIN role."""
    guard = _make_guard(roles={"ceo": AgentRole.ADMIN, "cmo": AgentRole.ORCHESTRATOR})
    # ADMIN can make permanent delegations
    guard.delegate(
        delegator_id="ceo",
        delegate_id="cmo",
        permissions=[AgentPermission.CONTROL],
        scope=DelegationScope.PERMANENT,
    )
    assert guard.check("cmo", AgentPermission.CONTROL, "any") is True


# ---------------------------------------------------------------------------
# P5-T6-4: Only ADMIN can delegate ADMIN permission
# ---------------------------------------------------------------------------


def test_only_admin_can_delegate_admin_permission() -> None:
    """ADMIN role is required to delegate AgentPermission.ADMIN."""
    guard = _make_guard(
        roles={"sup": AgentRole.SUPERVISOR, "w1": AgentRole.WORKER},
    )
    with pytest.raises(AgentPermissionError):
        guard.delegate(
            delegator_id="sup",
            delegate_id="w1",
            permissions=[AgentPermission.ADMIN],
            scope=DelegationScope.CURRENT_RUN,
        )


# ---------------------------------------------------------------------------
# P5-T6-5: Non-ADMIN delegating ADMIN permission raises AgentPermissionError
# ---------------------------------------------------------------------------


def test_non_admin_delegating_admin_raises() -> None:
    """ORCHESTRATOR cannot delegate AgentPermission.ADMIN."""
    guard = _make_guard(
        roles={"orch": AgentRole.ORCHESTRATOR, "w1": AgentRole.WORKER},
    )
    with pytest.raises(AgentPermissionError):
        guard.delegate(
            delegator_id="orch",
            delegate_id="w1",
            permissions=[AgentPermission.ADMIN],
            scope=DelegationScope.CURRENT_RUN,
        )


# ---------------------------------------------------------------------------
# P5-T6-6: Hook.AGENT_DELEGATION fires on successful delegation
# ---------------------------------------------------------------------------


def test_delegation_fires_hook() -> None:
    """Successful delegate() fires Hook.AGENT_DELEGATION."""
    fired: list[tuple[Hook, dict[str, object]]] = []
    guard = _make_guard(
        roles={"ceo": AgentRole.ADMIN, "cmo": AgentRole.ORCHESTRATOR},
        fired=fired,
    )
    guard.delegate(
        delegator_id="ceo",
        delegate_id="cmo",
        permissions=[AgentPermission.CONTROL],
        scope=DelegationScope.CURRENT_RUN,
    )
    assert any(h == Hook.AGENT_DELEGATION for h, _ in fired)
    hook_data = next(d for h, d in fired if h == Hook.AGENT_DELEGATION)
    assert hook_data["delegator_id"] == "ceo"
    assert hook_data["delegate_id"] == "cmo"
    assert AgentPermission.CONTROL in hook_data["permissions"]  # type: ignore[operator]
    assert hook_data["scope"] == DelegationScope.CURRENT_RUN


# ---------------------------------------------------------------------------
# P5-T6-7: Delegated permission appears in guard.check() results
# ---------------------------------------------------------------------------


def test_delegated_permission_in_check() -> None:
    """Delegated permission is reflected in guard.check()."""
    guard = _make_guard(
        roles={"ceo": AgentRole.ADMIN, "cmo": AgentRole.WORKER, "target": AgentRole.WORKER},
        teams={},
    )
    # Worker cannot SPAWN before delegation
    assert guard.check("cmo", AgentPermission.SPAWN, "target") is False

    guard.delegate(
        delegator_id="ceo",
        delegate_id="cmo",
        permissions=[AgentPermission.SPAWN],
        scope=DelegationScope.CURRENT_RUN,
    )

    assert guard.check("cmo", AgentPermission.SPAWN, "target") is True
