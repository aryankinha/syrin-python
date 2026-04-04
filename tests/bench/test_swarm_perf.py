"""Performance benchmarks for swarm with Almock — must complete in < 5s total."""

from __future__ import annotations

import time

import pytest

from syrin import Agent, Model
from syrin.enums import Hook
from syrin.swarm import Swarm
from syrin.swarm._registry import AgentRegistry


class _BenchAgent(Agent):
    """Benchmark agent using Almock (no real LLM calls)."""

    model = Model.Almock()
    system_prompt = "Bench agent."


def _noop_fire(hook: Hook, ctx: object) -> None:
    """No-op hook emitter for benchmark registry registration."""


@pytest.mark.asyncio
async def test_swarm_pipeline_10_agents_under_5s() -> None:
    """10-agent parallel swarm with Almock — wall-clock < 5s."""
    agents: list[Agent] = [_BenchAgent() for _ in range(10)]
    swarm = Swarm(agents=agents, goal="performance benchmark")
    t0 = time.perf_counter()
    result = await swarm.run()
    elapsed = time.perf_counter() - t0
    assert elapsed < 5.0, f"Swarm took {elapsed:.2f}s, expected < 5s"
    assert result is not None


@pytest.mark.asyncio
async def test_registry_query_100_agents_under_50ms() -> None:
    """Register 100 agents, list_agents() — assert < 50ms."""
    registry = AgentRegistry()
    # Create 100 distinct agent classes so each registration is unique
    agent_classes = [type(f"BenchAgent{i}", (_BenchAgent,), {}) for i in range(100)]
    for cls in agent_classes:
        await registry.register(cls, _noop_fire)

    t0 = time.perf_counter()
    agents = await registry.list_agents()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms < 50.0, f"Registry.list_agents() took {elapsed_ms:.2f}ms, expected < 50ms"
    assert len(agents) == 100
