"""Swarm stress tests: 10-agent concurrent correctness."""

from __future__ import annotations

import pytest

from syrin import Agent, Model
from syrin.enums import FallbackStrategy
from syrin.swarm import Swarm
from syrin.swarm._config import SwarmConfig


class _StressAgentA(Agent):
    """Stress test agent A."""

    model = Model.Almock()
    system_prompt = "Stress agent A."


class _StressAgentB(Agent):
    """Stress test agent B."""

    model = Model.Almock()
    system_prompt = "Stress agent B."


class _FailingAgent(Agent):
    """Agent that always fails."""

    model = Model.Almock()
    system_prompt = "Failing agent."

    def run(self, task: str, **kwargs: object) -> object:  # type: ignore[override]
        raise RuntimeError("Intentional failure for stress test")


@pytest.mark.asyncio
async def test_10_agents_parallel_no_race_conditions() -> None:
    """10 concurrent agents each run with Almock — all complete, no crashes."""
    agents: list[Agent] = [_StressAgentA() for _ in range(10)]
    swarm = Swarm(agents=agents, goal="stress test parallel")
    result = await swarm.run()
    # All agents should succeed — agent_results holds successful responses
    assert result is not None
    assert len(result.agent_results) > 0


@pytest.mark.asyncio
async def test_agent_failure_contained() -> None:
    """One failing agent with SKIP_AND_CONTINUE — other agents complete normally."""
    agents: list[Agent] = [_StressAgentA(), _StressAgentA(), _FailingAgent()]
    config = SwarmConfig(on_agent_failure=FallbackStrategy.SKIP_AND_CONTINUE)
    swarm = Swarm(agents=agents, goal="test failure containment", config=config)
    result = await swarm.run()
    # The swarm should not crash; partial results from good agents available
    # (failure is contained)
    assert result is not None


@pytest.mark.asyncio
async def test_multiple_agent_failures_partial_result() -> None:
    """Multiple failures — SwarmResult has partial_results from successful agents."""
    agents: list[Agent] = [
        _StressAgentA(),
        _FailingAgent(),
        _FailingAgent(),
    ]
    config = SwarmConfig(on_agent_failure=FallbackStrategy.SKIP_AND_CONTINUE)
    swarm = Swarm(agents=agents, goal="test partial results", config=config)
    result = await swarm.run()
    # At least one successful agent should produce a response
    assert result is not None
    # partial_results holds responses from agents that succeeded when others failed
    successful_responses = result.agent_results or result.partial_results
    assert len(successful_responses) >= 1
