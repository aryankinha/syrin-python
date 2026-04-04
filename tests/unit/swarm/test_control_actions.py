"""Tests for SwarmController control actions — Phase 5, P5-T2."""

from __future__ import annotations

import asyncio

import pytest

from syrin.enums import AgentRole, AgentStatus
from syrin.swarm._authority import AgentPermissionError, SwarmAuthorityGuard
from syrin.swarm._control import AgentStateSnapshot, SwarmController

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_supervisor_guard(
    actor_id: str = "sup",
    target_id: str = "w1",
) -> SwarmAuthorityGuard:
    """Return a guard where actor is SUPERVISOR over target."""
    return SwarmAuthorityGuard(
        roles={actor_id: AgentRole.SUPERVISOR, target_id: AgentRole.WORKER},
        teams={actor_id: [target_id]},
    )


def _make_snapshot(agent_id: str = "w1") -> AgentStateSnapshot:
    """Build a minimal AgentStateSnapshot."""
    return AgentStateSnapshot(
        agent_id=agent_id,
        status=AgentStatus.RUNNING,
        role=AgentRole.WORKER,
        last_output_summary="Hello",
        cost_spent=0.05,
        task="do work",
        context_override=None,
        supervisor_id=None,
    )


def _make_controller(
    actor_id: str = "sup",
    target_id: str = "w1",
    guard: SwarmAuthorityGuard | None = None,
    task_registry: dict[str, asyncio.Task[object]] | None = None,
) -> SwarmController:
    g = guard or _make_supervisor_guard(actor_id, target_id)
    state = {target_id: _make_snapshot(target_id)}
    tasks: dict[str, asyncio.Task[object]] = task_registry or {}
    return SwarmController(
        actor_id=actor_id,
        guard=g,
        state_registry=state,
        task_registry=tasks,
    )


# ---------------------------------------------------------------------------
# P5-T2-1: pause_agent sets status to PAUSED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pause_agent_sets_paused() -> None:
    """pause_agent('w1') sets w1's status to PAUSED."""
    ctrl = _make_controller()
    await ctrl.pause_agent("w1")
    snap = await ctrl.read_agent_state("w1")
    assert snap.status == AgentStatus.PAUSED


# ---------------------------------------------------------------------------
# P5-T2-2: resume_agent sets status to RUNNING
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resume_agent_sets_running() -> None:
    """resume_agent('w1') sets w1's status to RUNNING."""
    ctrl = _make_controller()
    await ctrl.pause_agent("w1")
    await ctrl.resume_agent("w1")
    snap = await ctrl.read_agent_state("w1")
    assert snap.status == AgentStatus.RUNNING


# ---------------------------------------------------------------------------
# P5-T2-3: skip_agent sets status to IDLE and cancels task
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skip_agent_sets_idle_and_cancels() -> None:
    """skip_agent sets IDLE and cancels the agent's asyncio task."""

    async def _long_running() -> None:
        await asyncio.sleep(100)

    task: asyncio.Task[object] = asyncio.create_task(_long_running())
    task_reg: dict[str, asyncio.Task[object]] = {"w1": task}
    ctrl = _make_controller(task_registry=task_reg)
    await ctrl.skip_agent("w1")
    snap = await ctrl.read_agent_state("w1")
    assert snap.status == AgentStatus.IDLE
    # Allow event loop to process the cancellation
    await asyncio.sleep(0)
    assert task.cancelled()


# ---------------------------------------------------------------------------
# P5-T2-4: change_context stores context override
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_change_context_stores_override() -> None:
    """change_context stores the new context in state registry."""
    ctrl = _make_controller()
    await ctrl.change_context("w1", "Be concise")
    snap = await ctrl.read_agent_state("w1")
    assert snap.context_override == "Be concise"


# ---------------------------------------------------------------------------
# P5-T2-5: kill_agent sets KILLED and cancels task
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kill_agent_sets_killed_and_cancels() -> None:
    """kill_agent sets KILLED and cancels the agent task."""

    async def _long_running() -> None:
        await asyncio.sleep(100)

    task: asyncio.Task[object] = asyncio.create_task(_long_running())
    task_reg: dict[str, asyncio.Task[object]] = {"w1": task}
    ctrl = _make_controller(task_registry=task_reg)
    await ctrl.kill_agent("w1")
    snap = await ctrl.read_agent_state("w1")
    assert snap.status == AgentStatus.KILLED
    # Allow event loop to process the cancellation
    await asyncio.sleep(0)
    assert task.cancelled()


# ---------------------------------------------------------------------------
# P5-T2-6: read_agent_state returns AgentStateSnapshot
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_agent_state_returns_snapshot() -> None:
    """read_agent_state returns a valid AgentStateSnapshot."""
    ctrl = _make_controller()
    snap = await ctrl.read_agent_state("w1")
    assert isinstance(snap, AgentStateSnapshot)
    assert snap.agent_id == "w1"


# ---------------------------------------------------------------------------
# P5-T2-7: last_output_summary is always ≤ 500 chars
# ---------------------------------------------------------------------------


def test_last_output_summary_capped() -> None:
    """AgentStateSnapshot.last_output_summary is always ≤ 500 chars."""
    long_text = "x" * 1000
    snap = AgentStateSnapshot(
        agent_id="w1",
        status=AgentStatus.RUNNING,
        role=AgentRole.WORKER,
        last_output_summary=long_text,
        cost_spent=0.0,
        task="task",
        context_override=None,
        supervisor_id=None,
    )
    assert len(snap.last_output_summary) <= 500


# ---------------------------------------------------------------------------
# P5-T2-8: AgentStateSnapshot has all required fields
# ---------------------------------------------------------------------------


def test_agent_state_snapshot_fields() -> None:
    """AgentStateSnapshot exposes all documented fields."""
    snap = AgentStateSnapshot(
        agent_id="a1",
        status=AgentStatus.IDLE,
        role=AgentRole.SUPERVISOR,
        last_output_summary="ok",
        cost_spent=1.23,
        task="analyse",
        context_override="be brief",
        supervisor_id="sup",
    )
    assert snap.agent_id == "a1"
    assert snap.status == AgentStatus.IDLE
    assert snap.role == AgentRole.SUPERVISOR
    assert snap.last_output_summary == "ok"
    assert snap.cost_spent == 1.23
    assert snap.task == "analyse"
    assert snap.context_override == "be brief"
    assert snap.supervisor_id == "sup"


# ---------------------------------------------------------------------------
# P5-T2-9: Control actions require permission check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_control_action_denied_raises() -> None:
    """Worker cannot control another worker — AgentPermissionError raised."""
    guard = SwarmAuthorityGuard(
        roles={"w1": AgentRole.WORKER, "w2": AgentRole.WORKER},
        teams={},
    )
    state = {"w2": _make_snapshot("w2")}
    ctrl = SwarmController(
        actor_id="w1",
        guard=guard,
        state_registry=state,
        task_registry={},
    )
    with pytest.raises(AgentPermissionError):
        await ctrl.pause_agent("w2")


# ---------------------------------------------------------------------------
# P5-T2-10: Permission check fires correct hooks on success/deny
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_control_action_fires_hook_on_success() -> None:
    """Successful control action fires Hook.AGENT_CONTROL_ACTION."""
    from syrin.enums import Hook

    fired: list[tuple[Hook, dict[str, object]]] = []

    def _fire(hook: Hook, data: dict[str, object]) -> None:
        fired.append((hook, data))

    guard = SwarmAuthorityGuard(
        roles={"sup": AgentRole.SUPERVISOR, "w1": AgentRole.WORKER},
        teams={"sup": ["w1"]},
        fire_event_fn=_fire,
    )
    state = {"w1": _make_snapshot("w1")}
    ctrl = SwarmController(
        actor_id="sup",
        guard=guard,
        state_registry=state,
        task_registry={},
    )
    await ctrl.pause_agent("w1")
    assert any(h == Hook.AGENT_CONTROL_ACTION for h, _ in fired)


# ---------------------------------------------------------------------------
# pause_agent with PauseMode.DRAIN sets status to DRAINING
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pause_agent_drain_sets_draining_status() -> None:
    """pause_agent(mode=PauseMode.DRAIN) sets agent status to DRAINING."""
    from syrin.enums import PauseMode

    ctrl = _make_controller()
    await ctrl.pause_agent("w1", mode=PauseMode.DRAIN)
    snap = await ctrl.read_agent_state("w1")
    assert snap.status == AgentStatus.DRAINING


@pytest.mark.asyncio
async def test_pause_agent_immediate_sets_paused_status() -> None:
    """pause_agent(mode=PauseMode.IMMEDIATE) sets agent status to PAUSED."""
    from syrin.enums import PauseMode

    ctrl = _make_controller()
    await ctrl.pause_agent("w1", mode=PauseMode.IMMEDIATE)
    snap = await ctrl.read_agent_state("w1")
    assert snap.status == AgentStatus.PAUSED
