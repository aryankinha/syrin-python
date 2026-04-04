"""Swarm blast radius tests: failure isolation."""

from __future__ import annotations

import pytest

from syrin import Agent, Model
from syrin.enums import FallbackStrategy
from syrin.swarm import Swarm
from syrin.swarm._config import SwarmConfig


class _HealthyAgent(Agent):
    """Agent that always succeeds."""

    model = Model.Almock()
    system_prompt = "Healthy agent."


class _BoomAgent(Agent):
    """Agent that always raises immediately."""

    model = Model.Almock()
    system_prompt = "Boom agent."

    def run(self, task: str, **kwargs: object) -> object:  # type: ignore[override]
        raise RuntimeError("BOOM: intentional blast-radius failure")


@pytest.mark.asyncio
async def test_agent_failure_does_not_crash_swarm() -> None:
    """A failing agent with SKIP_AND_CONTINUE does not crash the swarm."""
    agents: list[Agent] = [_HealthyAgent(), _BoomAgent(), _HealthyAgent()]
    config = SwarmConfig(on_agent_failure=FallbackStrategy.SKIP_AND_CONTINUE)
    swarm = Swarm(agents=agents, goal="blast radius test", config=config)
    # Should not raise
    result = await swarm.run()
    assert result is not None


@pytest.mark.asyncio
async def test_healthy_agents_complete_despite_failure() -> None:
    """Healthy agents complete even when one agent fails."""
    agents: list[Agent] = [
        _HealthyAgent(),
        _HealthyAgent(),
        _BoomAgent(),
        _HealthyAgent(),
    ]
    config = SwarmConfig(on_agent_failure=FallbackStrategy.SKIP_AND_CONTINUE)
    swarm = Swarm(agents=agents, goal="healthy agents test", config=config)
    result = await swarm.run()
    # We had 3 healthy agents + 1 failing
    # agent_results or partial_results should have >= 1 result from healthy agents
    total = len(result.agent_results or []) + len(result.partial_results or [])
    assert total >= 1
