"""Tests for AgentRegistry — full in-process swarm agent registry."""

from __future__ import annotations

import asyncio
import time

import pytest

from syrin import Agent, Model
from syrin.enums import AgentStatus, Hook
from syrin.swarm._registry import AgentRegistry, AgentSummary

# ---------------------------------------------------------------------------
# Stub agent classes used as class references (no custom arun needed)
# ---------------------------------------------------------------------------


class _AgentA(Agent):
    model = Model.Almock()
    system_prompt = "stub A"


class _AgentB(Agent):
    model = Model.Almock()
    system_prompt = "stub B"


class _AgentC(Agent):
    model = Model.Almock()
    system_prompt = "stub C"


# ---------------------------------------------------------------------------
# Register / Unregister
# ---------------------------------------------------------------------------


def test_register_adds_agent() -> None:
    """Registering an agent should make it retrievable via get()."""
    reg = AgentRegistry()
    agent_id = asyncio.run(reg.register(_AgentA, lambda _h, _c: None))
    summary = asyncio.run(reg.get(agent_id))
    assert summary is not None
    assert summary.agent_id == agent_id
    assert summary.name == "_AgentA"
    assert summary.status == AgentStatus.IDLE


def test_register_id_format() -> None:
    """Registered agent ID must follow the 'ClassName-<6hex>' pattern."""
    import re

    reg = AgentRegistry()
    agent_id = asyncio.run(reg.register(_AgentA, lambda _h, _c: None))
    assert re.fullmatch(r"_AgentA-[0-9a-f]{6}", agent_id), (
        f"ID '{agent_id}' does not match expected format '_AgentA-<6hex>'"
    )


def test_register_same_class_produces_unique_ids() -> None:
    """Registering the same class twice produces two distinct IDs."""
    reg = AgentRegistry()
    id1 = asyncio.run(reg.register(_AgentA, lambda _h, _c: None))
    id2 = asyncio.run(reg.register(_AgentA, lambda _h, _c: None))
    assert id1 != id2


def test_register_fires_event() -> None:
    """Registering an agent should call the fire_fn with Hook.AGENT_REGISTERED."""
    fired: list[tuple[Hook, dict[str, object]]] = []

    async def run() -> None:
        async def fire(hook: Hook, ctx: dict[str, object]) -> None:  # type: ignore[override]
            fired.append((hook, ctx))

        reg = AgentRegistry()
        agent_id = await reg.register(_AgentA, fire)

        assert len(fired) == 1
        hook, ctx = fired[0]
        assert hook == Hook.AGENT_REGISTERED
        assert ctx["agent_id"] == agent_id
        assert ctx["name"] == "_AgentA"

    asyncio.run(run())


def test_unregister_removes_agent() -> None:
    """Unregistering an agent should remove it from the registry."""
    reg = AgentRegistry()
    agent_id = asyncio.run(reg.register(_AgentA, lambda _h, _c: None))
    asyncio.run(reg.unregister(agent_id))
    summary = asyncio.run(reg.get(agent_id))
    assert summary is None


def test_unregister_fires_event() -> None:
    """Unregistering should fire Hook.AGENT_UNREGISTERED."""
    fired: list[tuple[Hook, dict[str, object]]] = []

    async def run() -> None:
        async def fire(hook: Hook, ctx: dict[str, object]) -> None:  # type: ignore[override]
            fired.append((hook, ctx))

        reg = AgentRegistry()
        agent_id = await reg.register(_AgentA, fire)
        fired.clear()  # ignore the REGISTERED event
        await reg.unregister(agent_id)

        assert len(fired) == 1
        hook, ctx = fired[0]
        assert hook == Hook.AGENT_UNREGISTERED
        assert ctx["agent_id"] == agent_id

    asyncio.run(run())


def test_unregister_unknown_raises_KeyError() -> None:
    """Unregistering an unknown agent should raise KeyError."""
    reg = AgentRegistry()
    with pytest.raises(KeyError):
        asyncio.run(reg.unregister("does-not-exist"))


# ---------------------------------------------------------------------------
# Get / List
# ---------------------------------------------------------------------------


def test_get_returns_summary() -> None:
    """get() should return an AgentSummary with correct fields."""
    reg = AgentRegistry()
    agent_id = asyncio.run(reg.register(_AgentA, lambda _h, _c: None))
    summary = asyncio.run(reg.get(agent_id))
    assert isinstance(summary, AgentSummary)
    assert summary.agent_id == agent_id
    assert summary.name == "_AgentA"
    assert summary.status == AgentStatus.IDLE
    assert summary.cost_so_far == 0.0
    assert summary.goal is None
    assert summary.last_heartbeat > 0


def test_get_unknown_returns_none() -> None:
    """get() for an unknown agent_id should return None."""
    reg = AgentRegistry()
    result = asyncio.run(reg.get("missing"))
    assert result is None


def test_list_agents_all() -> None:
    """list_agents() with no filter should return all registered agents."""
    reg = AgentRegistry()
    id1 = asyncio.run(reg.register(_AgentA, lambda _h, _c: None))
    id2 = asyncio.run(reg.register(_AgentB, lambda _h, _c: None))
    agents = asyncio.run(reg.list_agents())
    ids = {a.agent_id for a in agents}
    assert ids == {id1, id2}


def test_list_agents_filtered_by_status() -> None:
    """list_agents(status=...) should return only agents with that status."""
    reg = AgentRegistry()
    id1 = asyncio.run(reg.register(_AgentA, lambda _h, _c: None))
    id2 = asyncio.run(reg.register(_AgentB, lambda _h, _c: None))
    asyncio.run(reg.update_status(id1, AgentStatus.RUNNING))

    running = asyncio.run(reg.list_agents(status=AgentStatus.RUNNING))
    idle = asyncio.run(reg.list_agents(status=AgentStatus.IDLE))

    assert len(running) == 1
    assert running[0].agent_id == id1
    assert len(idle) == 1
    assert idle[0].agent_id == id2


# ---------------------------------------------------------------------------
# Update methods
# ---------------------------------------------------------------------------


def test_update_status() -> None:
    """update_status() should change the agent's status."""
    reg = AgentRegistry()
    agent_id = asyncio.run(reg.register(_AgentA, lambda _h, _c: None))
    asyncio.run(reg.update_status(agent_id, AgentStatus.RUNNING))
    summary = asyncio.run(reg.get(agent_id))
    assert summary is not None
    assert summary.status == AgentStatus.RUNNING


def test_update_cost() -> None:
    """update_cost() should add to the agent's cost_so_far."""
    reg = AgentRegistry()
    agent_id = asyncio.run(reg.register(_AgentA, lambda _h, _c: None))
    asyncio.run(reg.update_cost(agent_id, 0.05))
    asyncio.run(reg.update_cost(agent_id, 0.10))
    summary = asyncio.run(reg.get(agent_id))
    assert summary is not None
    assert abs(summary.cost_so_far - 0.15) < 1e-9


def test_update_goal() -> None:
    """update_goal() should set the agent's goal string."""
    reg = AgentRegistry()
    agent_id = asyncio.run(reg.register(_AgentA, lambda _h, _c: None))
    asyncio.run(reg.update_goal(agent_id, "Summarize quarterly report"))
    summary = asyncio.run(reg.get(agent_id))
    assert summary is not None
    assert summary.goal == "Summarize quarterly report"


# ---------------------------------------------------------------------------
# Heartbeat / Stale detection
# ---------------------------------------------------------------------------


def test_heartbeat_updates_timestamp() -> None:
    """heartbeat() should update last_heartbeat to current time."""
    reg = AgentRegistry()
    agent_id = asyncio.run(reg.register(_AgentA, lambda _h, _c: None))
    before = time.monotonic()
    asyncio.run(reg.heartbeat(agent_id))
    summary = asyncio.run(reg.get(agent_id))
    assert summary is not None
    assert summary.last_heartbeat >= before


def test_stale_agents_detection() -> None:
    """stale_agents() should return agents whose last_heartbeat is older than timeout."""

    async def run() -> list[AgentSummary]:
        reg = AgentRegistry()
        await reg.register(_AgentA, lambda _h, _c: None)
        stale_id = await reg.register(_AgentB, lambda _h, _c: None)
        # Manually force a very old heartbeat on the stale agent
        async with reg._lock:
            reg._agents[stale_id].summary.last_heartbeat = time.monotonic() - 1000.0
        return await reg.stale_agents(timeout_seconds=10.0)

    stale = asyncio.run(run())
    assert len(stale) == 1
    assert stale[0].name == "_AgentB"


def test_stale_agents_empty_when_fresh() -> None:
    """stale_agents() should return empty list when all agents are fresh."""
    reg = AgentRegistry()
    asyncio.run(reg.register(_AgentA, lambda _h, _c: None))
    result = asyncio.run(reg.stale_agents(timeout_seconds=60.0))
    assert result == []


# ---------------------------------------------------------------------------
# Concurrency safety
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_register() -> None:
    """Concurrent registrations should not race and all agents should be registered."""
    reg = AgentRegistry()

    # Use dynamically-created subclasses so each has a distinct class identity
    agent_classes = [type(f"ConcurrentAgent{i}", (_AgentA,), {}) for i in range(20)]

    await asyncio.gather(*[reg.register(cls, lambda _h, _c: None) for cls in agent_classes])
    agents = await reg.list_agents()
    assert len(agents) == 20


# ---------------------------------------------------------------------------
# expected_next_heartbeat
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_expected_next_heartbeat_set_on_register() -> None:
    """AgentSummary.expected_next_heartbeat is set relative to heartbeat_interval."""
    reg = AgentRegistry(heartbeat_interval=10.0)
    before = time.monotonic()
    agent_id = await reg.register(_AgentA, lambda _h, _c: None)
    after = time.monotonic()
    summary = await reg.get(agent_id)
    assert summary is not None
    assert summary.expected_next_heartbeat >= before + 10.0
    assert summary.expected_next_heartbeat <= after + 10.0


@pytest.mark.asyncio
async def test_expected_next_heartbeat_updated_on_heartbeat() -> None:
    """expected_next_heartbeat advances when heartbeat() is called."""
    reg = AgentRegistry(heartbeat_interval=5.0)
    agent_id = await reg.register(_AgentA, lambda _h, _c: None)
    before_beat = time.monotonic()
    await reg.heartbeat(agent_id)
    after_beat = time.monotonic()
    summary = await reg.get(agent_id)
    assert summary is not None
    assert summary.expected_next_heartbeat >= before_beat + 5.0
    assert summary.expected_next_heartbeat <= after_beat + 5.0
