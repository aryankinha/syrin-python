"""AgentRegistry — monitor, track, and manage active agents at runtime.

The AgentRegistry is the in-process directory of all agents participating in
a swarm. Operators use it for status tracking, cost accounting, goal management,
and heartbeat-based health monitoring.

Key concepts:
  - Agent IDs are auto-generated as ``ClassName-<6hex>`` — never pass a raw string.
  - Pass the agent *class* (not an instance) when registering.
  - Use the returned ID for all subsequent registry operations.
  - ``stale_agents(timeout_seconds)`` surfaces agents that have stopped heartbeating.

Run:
    uv run python examples/23_agent_registry/agent_registry.py
"""

from __future__ import annotations

import asyncio
import time

from syrin import Agent, Model
from syrin.enums import AgentStatus, Hook
from syrin.swarm import AgentRegistry

# ── Agent definitions ─────────────────────────────────────────────────────────
#
# Agents are registered by class reference — never by a raw string name.
# The registry derives the name from the class and generates a collision-free
# ID in the format ``ClassName-<6hex>`` (e.g. ``ResearchAgent-a3f2b1``).


class ResearchAgent(Agent):
    """Gathers primary sources and data for a given research topic."""

    model = Model.mock(latency_seconds=0.02)
    system_prompt = (
        "You are a senior research analyst. Retrieve and summarise primary "
        "data sources relevant to the given topic."
    )


class AnalysisAgent(Agent):
    """Derives strategic insights from the researcher's findings."""

    model = Model.mock(latency_seconds=0.02)
    system_prompt = (
        "You are a strategic analyst. Interpret research findings and surface "
        "the three most important business implications."
    )


class WriterAgent(Agent):
    """Produces executive-grade written output from analysis."""

    model = Model.mock(latency_seconds=0.02)
    system_prompt = (
        "You are a management consultant who writes concise C-suite briefs. "
        "Transform analysis into a clear, actionable executive summary."
    )


# ── Shared no-op fire function ────────────────────────────────────────────────


def _no_op_fire(hook: Hook, ctx: dict[str, object]) -> None:
    """Placeholder hook emitter — real agents use agent.events."""


# ── Example 1: Register agents by class and inspect auto-generated IDs ────────
#
# Agents are registered by passing the class itself. The registry generates a
# unique ID in the form ``ClassName-<6hex>`` — no manual ID management needed.


async def example_register_by_class() -> None:
    print("\n── Example 1: Register agents by class reference ────────────────")

    events: list[tuple[str, str]] = []

    def fire(hook: Hook, ctx: dict[str, object]) -> None:
        events.append((str(hook), str(ctx.get("agent_id", ""))))

    registry = AgentRegistry(heartbeat_interval=5.0)

    # Register by class — the registry derives name and generates the ID
    research_id = await registry.register(ResearchAgent, fire)
    analysis_id = await registry.register(AnalysisAgent, fire)
    writer_id = await registry.register(WriterAgent, fire)

    print(f"  ResearchAgent → {research_id}")
    print(f"  AnalysisAgent → {analysis_id}")
    print(f"  WriterAgent   → {writer_id}")

    # IDs follow the ClassName-<hex> pattern; no two are alike
    assert research_id.startswith("ResearchAgent-")
    assert analysis_id.startswith("AnalysisAgent-")
    assert writer_id.startswith("WriterAgent-")
    assert len({research_id, analysis_id, writer_id}) == 3  # all unique

    agents = await registry.list_agents()
    print(f"\n  Registered: {len(agents)} agents")
    for a in agents:
        print(f"    {a.agent_id:<30}  status={a.status}")

    registered_hooks = [e for e in events if "registered" in e[0].lower()]
    print(f"\n  AGENT_REGISTERED hooks fired: {len(registered_hooks)}")


# ── Example 2: Same class, multiple instances — always unique IDs ─────────────
#
# Registering the same class more than once (e.g. three parallel research
# workers) produces distinct IDs each time. No naming collisions.


async def example_same_class_unique_ids() -> None:
    print("\n── Example 2: Same class → distinct IDs each time ───────────────")

    registry = AgentRegistry()
    ids = [await registry.register(ResearchAgent, _no_op_fire) for _ in range(3)]

    for agent_id in ids:
        print(f"  {agent_id}")

    assert len(set(ids)) == 3, "Each registration must yield a unique ID"
    print(f"  All {len(ids)} IDs are unique ✓")


# ── Example 3: Status lifecycle ───────────────────────────────────────────────
#
# An agent transitions from IDLE → RUNNING → PAUSED → STOPPED.
# Operators can filter list_agents() to see only agents in a specific state.


async def example_status_lifecycle() -> None:
    print("\n── Example 3: Status lifecycle (IDLE → RUNNING → PAUSED → STOPPED) ─")

    registry = AgentRegistry()
    agent_id = await registry.register(ResearchAgent, _no_op_fire)

    for status in [AgentStatus.RUNNING, AgentStatus.PAUSED, AgentStatus.STOPPED]:
        await registry.update_status(agent_id, status)
        summary = await registry.get(agent_id)
        assert summary is not None
        print(f"  → {status:<10}  confirmed: {summary.status}")

    # Register a second agent to demonstrate status filtering
    await registry.update_status(agent_id, AgentStatus.RUNNING)
    await registry.register(AnalysisAgent, _no_op_fire)

    running = await registry.list_agents(status=AgentStatus.RUNNING)
    idle = await registry.list_agents(status=AgentStatus.IDLE)
    print(f"\n  Running: {[a.name for a in running]}")
    print(f"  Idle:    {[a.name for a in idle]}")


# ── Example 4: Heartbeat monitoring ──────────────────────────────────────────
#
# Long-running agents are expected to call heartbeat() at regular intervals.
# The registry tracks when the next heartbeat is due and surfaces agents that
# have gone quiet via stale_agents(timeout_seconds).


async def example_heartbeat_monitoring() -> None:
    print("\n── Example 4: Heartbeat monitoring ─────────────────────────────")

    registry = AgentRegistry(heartbeat_interval=2.0)
    healthy_id = await registry.register(ResearchAgent, _no_op_fire)
    stale_id = await registry.register(AnalysisAgent, _no_op_fire)

    # Simulate the stale agent not sending a heartbeat for 90 seconds
    async with registry._lock:
        registry._agents[stale_id].summary.last_heartbeat = time.monotonic() - 90.0

    # Send a fresh heartbeat for the healthy agent
    await registry.heartbeat(healthy_id)

    stale = await registry.stale_agents(timeout_seconds=30.0)
    print(f"  Stale agents (>30s without heartbeat): {[a.name for a in stale]}")
    assert any(a.agent_id == stale_id for a in stale)

    fresh = await registry.stale_agents(timeout_seconds=300.0)
    print(f"  Stale agents (>5 min without heartbeat): {[a.name for a in fresh]}")


# ── Example 5: Cost accounting per agent ─────────────────────────────────────
#
# Costs accumulate per agent via update_cost(). The registry maintains a
# running total (cost_so_far) per agent — useful for dashboards and budget
# alerting at the operator level.


async def example_cost_accounting() -> None:
    print("\n── Example 5: Per-agent cost accounting ─────────────────────────")

    registry = AgentRegistry()
    research_id = await registry.register(ResearchAgent, _no_op_fire)
    writer_id = await registry.register(WriterAgent, _no_op_fire)

    # Simulate LLM call costs accumulating over a multi-step run
    research_calls = [0.0031, 0.0045, 0.0028, 0.0062]
    writer_calls = [0.0018, 0.0024]

    for cost in research_calls:
        await registry.update_cost(research_id, cost)
    for cost in writer_calls:
        await registry.update_cost(writer_id, cost)

    for agent_id in [research_id, writer_id]:
        summary = await registry.get(agent_id)
        assert summary is not None
        print(f"  {summary.name:<20}  cost=${summary.cost_so_far:.4f}")


# ── Example 6: Goal tracking ──────────────────────────────────────────────────
#
# An agent's current goal is visible in the registry and changes as the swarm
# progresses. syrin fires Hook.GOAL_UPDATED whenever set_goal() is called —
# wire it up for dashboards, audit logs, or dynamic routing.


async def example_goal_tracking() -> None:
    print("\n── Example 6: Goal tracking with Hook.GOAL_UPDATED ──────────────")

    class TrackedAgent(Agent):
        model = Model.mock(latency_seconds=0.01)
        system_prompt = "You are a research agent."

    goal_events: list[str] = []
    agent = TrackedAgent()
    agent.events.on(
        Hook.GOAL_UPDATED,
        lambda ctx: goal_events.append(str(ctx.get("goal", ""))),
    )

    agent.set_goal("Collect AI market data — Q1 2025")
    agent.set_goal("Analyse competitive positioning")
    agent.set_goal("Draft executive brief")

    print(f"  Goal transitions ({len(goal_events)}):")
    for i, goal in enumerate(goal_events, 1):
        print(f"    {i}. {goal}")

    assert len(goal_events) == 3


# ── Example 7: Unregister (terminate) an agent ────────────────────────────────
#
# When an agent completes its work or is forcibly killed, unregister() removes
# it from the registry and fires Hook.AGENT_UNREGISTERED. Downstream monitors
# can react to this event to clean up resources or trigger compensating actions.


async def example_unregister() -> None:
    print("\n── Example 7: Unregister (terminate) an agent ───────────────────")

    lifecycle_events: list[str] = []

    def fire(hook: Hook, ctx: dict[str, object]) -> None:
        lifecycle_events.append(str(hook))

    registry = AgentRegistry()
    transient_id = await registry.register(ResearchAgent, fire)
    permanent_id = await registry.register(WriterAgent, fire)

    before = await registry.list_agents()
    print(f"  Active before unregister: {[a.name for a in before]}")

    await registry.unregister(transient_id)

    after = await registry.list_agents()
    print(f"  Active after unregister:  {[a.name for a in after]}")
    print(f"  Lifecycle hooks fired:    {lifecycle_events}")

    assert any(a.agent_id == permanent_id for a in after)
    assert not any(a.agent_id == transient_id for a in after)


# ── Main ──────────────────────────────────────────────────────────────────────


async def main() -> None:
    await example_register_by_class()
    await example_same_class_unique_ids()
    await example_status_lifecycle()
    await example_heartbeat_monitoring()
    await example_cost_accounting()
    await example_goal_tracking()
    await example_unregister()
    print("\nAll AgentRegistry examples completed.")


if __name__ == "__main__":
    asyncio.run(main())
