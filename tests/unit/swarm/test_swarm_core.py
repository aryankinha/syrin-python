"""P2-T4: Swarm class skeleton — construction and basic properties."""

from __future__ import annotations

import pytest

from syrin import Agent, Budget, Model
from syrin.enums import SwarmTopology
from syrin.events import EventContext
from syrin.response import Response
from syrin.swarm import Swarm, SwarmConfig


def _make_agent(content: str = "result", cost: float = 0.01) -> Agent:
    """Create a concrete agent instance."""

    class _Stub(Agent):
        model = Model.Almock()
        system_prompt = "stub"

        async def arun(self, input_text: str) -> Response[str]:
            return Response(content=content, cost=cost)

    _Stub.__name__ = f"Stub_{content[:8]}"
    return _Stub()


@pytest.mark.phase_2
class TestSwarmConstruction:
    """Swarm() constructor and attribute access."""

    def test_construct_with_agents_and_goal(self) -> None:
        """Swarm(agents=[...], goal='...') constructs without error."""
        a = _make_agent("r1")
        b = _make_agent("r2")
        swarm = Swarm(agents=[a, b], goal="Do something useful")
        assert swarm is not None

    def test_goal_attribute(self) -> None:
        """swarm.goal returns the provided goal string."""
        a = _make_agent()
        swarm = Swarm(agents=[a], goal="my goal")
        assert swarm.goal == "my goal"

    def test_agent_count(self) -> None:
        """swarm.agent_count returns the number of agents."""
        agents = [_make_agent(f"r{i}") for i in range(3)]
        swarm = Swarm(agents=agents, goal="count test")
        assert swarm.agent_count == 3

    def test_default_topology_is_orchestrator(self) -> None:
        """Default topology is ORCHESTRATOR when no config provided."""
        a = _make_agent()
        swarm = Swarm(agents=[a], goal="goal")
        assert swarm.topology == SwarmTopology.ORCHESTRATOR

    def test_topology_from_config(self) -> None:
        """topology follows SwarmConfig.topology."""
        a = _make_agent()
        config = SwarmConfig(topology=SwarmTopology.ORCHESTRATOR)
        swarm = Swarm(agents=[a], goal="goal", config=config)
        assert swarm.topology == SwarmTopology.ORCHESTRATOR

    def test_budget_attribute(self) -> None:
        """swarm.budget returns the provided Budget."""
        a = _make_agent()
        bgt = Budget(max_cost=5.00)
        swarm = Swarm(agents=[a], goal="goal", budget=bgt)
        assert swarm.budget is bgt

    def test_config_attribute(self) -> None:
        """swarm.config returns the provided SwarmConfig."""
        a = _make_agent()
        config = SwarmConfig(max_parallel_agents=3)
        swarm = Swarm(agents=[a], goal="goal", config=config)
        assert swarm.config is config

    def test_events_accessible(self) -> None:
        """swarm.events is accessible and allows registering hooks."""
        from syrin.enums import Hook

        a = _make_agent()
        swarm = Swarm(agents=[a], goal="goal")
        fired: list[EventContext] = []
        swarm.events.on(Hook.SWARM_STARTED, lambda ctx: fired.append(ctx))
        assert swarm.events is not None


@pytest.mark.phase_2
class TestSwarmConstructionErrors:
    """Swarm raises on invalid construction."""

    def test_empty_agents_raises(self) -> None:
        """Swarm with no agents raises ValueError."""
        with pytest.raises(ValueError):
            Swarm(agents=[], goal="goal")

    def test_empty_goal_raises(self) -> None:
        """Swarm with empty goal string raises ValueError."""
        a = _make_agent()
        with pytest.raises(ValueError):
            Swarm(agents=[a], goal="")

    def test_whitespace_only_goal_raises(self) -> None:
        """Swarm with whitespace-only goal raises ValueError."""
        a = _make_agent()
        with pytest.raises(ValueError):
            Swarm(agents=[a], goal="   ")

    def test_budget_is_optional(self) -> None:
        """Swarm without budget does not raise."""
        a = _make_agent()
        swarm = Swarm(agents=[a], goal="goal")
        assert swarm.budget is None

    def test_config_is_optional(self) -> None:
        """Swarm without config uses defaults."""
        a = _make_agent()
        swarm = Swarm(agents=[a], goal="goal")
        assert swarm.config is not None  # Default config is created


@pytest.mark.phase_2
class TestSwarmRunInterface:
    """Swarm.run() and Swarm.play() basic interface."""

    async def test_run_returns_swarm_result(self) -> None:
        """await swarm.run() returns a SwarmResult."""
        from syrin.swarm import SwarmResult

        a = _make_agent("output")
        swarm = Swarm(agents=[a], goal="test goal")
        result = await swarm.run()
        assert isinstance(result, SwarmResult)

    async def test_run_result_has_content(self) -> None:
        """SwarmResult.content is a non-empty string after run."""
        a = _make_agent("agent output")
        swarm = Swarm(agents=[a], goal="test goal")
        result = await swarm.run()
        assert isinstance(result.content, str)

    async def test_play_returns_run_handle(self) -> None:
        """swarm.play() returns a RunHandle immediately."""
        from syrin.workflow._lifecycle import RunHandle

        a = _make_agent("output")
        swarm = Swarm(agents=[a], goal="test goal")
        handle = swarm.play()
        assert isinstance(handle, RunHandle)
        await swarm.cancel()


class TestSwarmRunSync:
    """Swarm.run_sync() works in non-async contexts."""

    def test_run_sync_returns_swarm_result(self) -> None:
        """run_sync() returns SwarmResult without asyncio.run() boilerplate."""
        from syrin.swarm import SwarmResult

        a = _make_agent("sync output")
        swarm = Swarm(agents=[a], goal="sync test")
        result = swarm.run_sync()
        assert isinstance(result, SwarmResult)
        assert "sync output" in result.content

    def test_run_sync_with_budget(self) -> None:
        """run_sync() respects budget configuration."""
        a = _make_agent("budget sync", cost=0.01)
        budget = Budget(max_cost=5.00)
        swarm = Swarm(
            agents=[a],
            goal="sync budget test",
            budget=budget,
            config=SwarmConfig(topology=SwarmTopology.PARALLEL),
        )
        result = swarm.run_sync()
        assert result.cost_breakdown is not None
        assert sum(result.cost_breakdown.values()) == pytest.approx(0.01)
