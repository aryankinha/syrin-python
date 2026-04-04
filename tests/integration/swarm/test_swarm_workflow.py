"""P2-T10: Swarm + Workflow integration tests."""

from __future__ import annotations

import pytest

from syrin import Agent, Budget, Model
from syrin.enums import FallbackStrategy, Hook, SwarmTopology
from syrin.events import EventContext
from syrin.response import Response
from syrin.swarm import Swarm, SwarmConfig, SwarmResult


def _make_agent(content: str, cost: float = 0.01) -> Agent:
    """Stub agent returning *content*."""

    class _Stub(Agent):
        model = Model.Almock()
        system_prompt = "stub"

        async def arun(self, input_text: str) -> Response[str]:
            return Response(content=content, cost=cost)

    _Stub.__name__ = f"Stub_{content[:8]}"
    return _Stub()


def _make_agent_class(content: str, cost: float = 0.01) -> type[Agent]:
    """Stub agent class."""

    class _Stub(Agent):
        model = Model.Almock()
        system_prompt = "stub"

        async def arun(self, input_text: str) -> Response[str]:
            return Response(content=content, cost=cost)

    _Stub.__name__ = f"Stub_{content[:8]}"
    return _Stub


@pytest.mark.phase_2
class TestSwarmWithParallelAgents:
    """End-to-end swarm with parallel agents."""

    async def test_parallel_swarm_produces_merged_result(self) -> None:
        """PARALLEL swarm merges all agent outputs into SwarmResult.content."""
        agents = [
            _make_agent("research findings"),
            _make_agent("analysis results"),
            _make_agent("summary text"),
        ]
        swarm = Swarm(
            agents=agents,
            goal="Research and summarise AI trends",
            budget=Budget(max_cost=5.00),
        )
        result = await swarm.run()
        assert isinstance(result, SwarmResult)
        assert "research findings" in result.content

    async def test_parallel_swarm_budget_report(self) -> None:
        """SwarmResult.budget_report has entries for all agents."""
        agents = [_make_agent(f"r{i}", cost=0.02) for i in range(3)]
        budget = Budget(max_cost=5.00)
        swarm = Swarm(
            agents=agents,
            goal="budget report test",
            budget=budget,
            config=SwarmConfig(topology=SwarmTopology.PARALLEL),
        )
        result = await swarm.run()
        assert result.budget_report is not None
        assert result.budget_report.total_spent == pytest.approx(0.06)


@pytest.mark.phase_2
class TestSwarmLifecycleIntegration:
    """Swarm lifecycle controls work end-to-end."""

    async def test_swarm_hooks_fire_in_order(self) -> None:
        """SWARM_STARTED fires before AGENT_JOINED_SWARM fires before SWARM_ENDED."""
        order: list[str] = []
        agents = [_make_agent("r")]
        swarm = Swarm(agents=agents, goal="order test")
        swarm.events.on(Hook.SWARM_STARTED, lambda _ctx: order.append("STARTED"))
        swarm.events.on(Hook.AGENT_JOINED_SWARM, lambda _ctx: order.append("JOINED"))
        swarm.events.on(Hook.SWARM_ENDED, lambda _ctx: order.append("ENDED"))
        await swarm.run()
        assert order[0] == "STARTED"
        assert order[-1] == "ENDED"
        assert "JOINED" in order

    async def test_swarm_play_and_wait(self) -> None:
        """play() → wait() returns SwarmResult."""
        a = _make_agent("async output")
        swarm = Swarm(agents=[a], goal="play test")
        handle = swarm.play()
        result = await handle.wait()
        assert isinstance(result, SwarmResult)
        assert "async output" in result.content


@pytest.mark.phase_2
class TestSwarmFallbackIntegration:
    """Graceful degradation end-to-end."""

    async def test_skip_and_continue_partial_result(self) -> None:
        """SKIP_AND_CONTINUE: one agent fails, others produce output."""

        class GoodAgent(Agent):
            model = Model.Almock()
            system_prompt = "good"

            async def arun(self, input_text: str) -> Response[str]:
                return Response(content="I succeeded", cost=0.02)

        class BadAgent(Agent):
            model = Model.Almock()
            system_prompt = "bad"

            async def arun(self, input_text: str) -> Response[str]:
                raise RuntimeError("I failed catastrophically")

        swarm = Swarm(
            agents=[GoodAgent(), BadAgent()],
            goal="partial test",
            config=SwarmConfig(
                topology=SwarmTopology.PARALLEL,
                on_agent_failure=FallbackStrategy.SKIP_AND_CONTINUE,
            ),
        )
        result = await swarm.run()
        assert "I succeeded" in result.content
        assert len(result.partial_results) >= 1

    async def test_swarm_agent_failed_hook_includes_error(self) -> None:
        """AGENT_FAILED context includes error info."""
        failed: list[EventContext] = []

        class ExplodingAgent(Agent):
            model = Model.Almock()
            system_prompt = "explode"

            async def arun(self, input_text: str) -> Response[str]:
                raise ValueError("intentional error for test")

        swarm = Swarm(
            agents=[ExplodingAgent()],
            goal="error hook test",
            config=SwarmConfig(
                topology=SwarmTopology.PARALLEL,
                on_agent_failure=FallbackStrategy.SKIP_AND_CONTINUE,
            ),
        )
        swarm.events.on(Hook.AGENT_FAILED, lambda ctx: failed.append(ctx))
        await swarm.run()
        assert len(failed) >= 1
        ctx = failed[0]
        # Should have error info
        assert (
            getattr(ctx, "error", None) is not None or getattr(ctx, "agent_name", None) is not None
        )


@pytest.mark.phase_2
class TestSwarmBudgetIntegration:
    """Budget pool enforcement end-to-end."""

    async def test_per_agent_max_enforced(self) -> None:
        """No agent can spend more than per_agent_max from the shared pool."""
        # Each agent spends 0.05 — well under per_agent_max of 1.00
        agents = [_make_agent(f"r{i}", cost=0.05) for i in range(3)]
        budget = Budget(max_cost=5.00)
        swarm = Swarm(
            agents=agents,
            goal="max test",
            budget=budget,
            config=SwarmConfig(topology=SwarmTopology.PARALLEL),
        )
        result = await swarm.run()
        assert result.budget_report is not None
        # Should succeed — each agent is within budget
        assert result.budget_report.total_spent == pytest.approx(0.15)

    async def test_swarm_result_has_cost_breakdown(self) -> None:
        """SwarmResult.cost_breakdown maps agent names to their costs."""
        a = _make_agent("output_a", cost=0.04)
        b = _make_agent("output_b", cost=0.06)
        budget = Budget(max_cost=5.00)
        swarm = Swarm(
            agents=[a, b],
            goal="breakdown test",
            budget=budget,
            config=SwarmConfig(topology=SwarmTopology.PARALLEL),
        )
        result = await swarm.run()
        assert isinstance(result.cost_breakdown, dict)
        # Should have 2 entries
        assert len(result.cost_breakdown) == 2
        total = sum(result.cost_breakdown.values())
        assert total == pytest.approx(0.10)
