"""P2-T5: PARALLEL topology — all agents start concurrently."""

from __future__ import annotations

import asyncio
import time

import pytest

from syrin import Agent, Budget, Model
from syrin.enums import FallbackStrategy, Hook, SwarmTopology
from syrin.events import EventContext
from syrin.response import Response
from syrin.swarm import Swarm, SwarmConfig, SwarmResult


def _make_agent(content: str, cost: float = 0.01, delay: float = 0.0) -> Agent:
    """Create a stub agent that optionally sleeps before returning."""
    _delay = delay

    class _Stub(Agent):
        model = Model.Almock()
        system_prompt = "stub"

        async def arun(self, input_text: str) -> Response[str]:
            if _delay > 0:
                await asyncio.sleep(_delay)
            return Response(content=content, cost=cost)

    _Stub.__name__ = f"Stub_{content[:8]}"
    return _Stub()


def _make_failing_agent(name: str = "Fail") -> Agent:
    """Create an agent that always raises RuntimeError."""

    class _Fail(Agent):
        model = Model.Almock()
        system_prompt = "fail"

        async def arun(self, input_text: str) -> Response[str]:
            raise RuntimeError(f"{name} agent exploded")

    _Fail.__name__ = name
    return _Fail()


@pytest.mark.phase_2
class TestParallelTopologyBasic:
    """All agents run concurrently and their outputs are in SwarmResult."""

    async def test_all_agents_outputs_in_result(self) -> None:
        """SwarmResult contains outputs from all agents."""
        a = _make_agent("reddit findings")
        b = _make_agent("hn findings")
        c = _make_agent("arxiv findings")
        swarm = Swarm(
            agents=[a, b, c],
            goal="Research AI trends",
            config=SwarmConfig(topology=SwarmTopology.PARALLEL),
        )
        result = await swarm.run()
        assert "reddit findings" in result.content
        assert "hn findings" in result.content
        assert "arxiv findings" in result.content

    async def test_agent_results_list_length(self) -> None:
        """SwarmResult.agent_results has one entry per agent."""
        agents = [_make_agent(f"out{i}") for i in range(3)]
        swarm = Swarm(
            agents=agents, goal="goal", config=SwarmConfig(topology=SwarmTopology.PARALLEL)
        )
        result = await swarm.run()
        assert len(result.agent_results) == 3

    async def test_parallel_runs_faster_than_sequential(self) -> None:
        """Three agents with 50ms delay each complete in <120ms (not 150ms)."""
        agents = [_make_agent(f"r{i}", delay=0.05) for i in range(3)]
        swarm = Swarm(
            agents=agents, goal="timing test", config=SwarmConfig(topology=SwarmTopology.PARALLEL)
        )
        start = time.monotonic()
        await swarm.run()
        elapsed = time.monotonic() - start
        assert elapsed < 0.12, f"Parallel took {elapsed:.3f}s, expected <0.12s"


@pytest.mark.phase_2
class TestParallelBudget:
    """Budget is tracked per-agent and in aggregate."""

    async def test_budget_report_per_agent(self) -> None:
        """SwarmResult.budget_report.per_agent has an entry for each agent."""
        a = _make_agent("a", cost=0.05)
        b = _make_agent("b", cost=0.03)
        budget = Budget(max_cost=10.00)
        swarm = Swarm(
            agents=[a, b],
            goal="budget test",
            budget=budget,
            config=SwarmConfig(topology=SwarmTopology.PARALLEL),
        )
        result = await swarm.run()
        assert result.budget_report is not None
        assert len(result.budget_report.per_agent) == 2

    async def test_budget_report_total_spent(self) -> None:
        """budget_report.total_spent reflects sum of all agent costs."""
        a = _make_agent("a", cost=0.05)
        b = _make_agent("b", cost=0.03)
        budget = Budget(max_cost=10.00)
        swarm = Swarm(
            agents=[a, b],
            goal="cost test",
            budget=budget,
            config=SwarmConfig(topology=SwarmTopology.PARALLEL),
        )
        result = await swarm.run()
        assert result.budget_report.total_spent == pytest.approx(0.08)


@pytest.mark.phase_2
class TestParallelHooks:
    """PARALLEL topology fires lifecycle hooks correctly."""

    async def test_swarm_started_fires(self) -> None:
        """Hook.SWARM_STARTED fires before any agent starts."""
        fired: list[EventContext] = []
        a = _make_agent("output")
        swarm = Swarm(
            agents=[a], goal="hook test", config=SwarmConfig(topology=SwarmTopology.PARALLEL)
        )
        swarm.events.on(Hook.SWARM_STARTED, lambda ctx: fired.append(ctx))
        await swarm.run()
        assert len(fired) == 1

    async def test_agent_joined_fires_per_agent(self) -> None:
        """Hook.AGENT_JOINED_SWARM fires once per agent."""
        joined: list[EventContext] = []
        agents = [_make_agent(f"r{i}") for i in range(3)]
        swarm = Swarm(
            agents=agents, goal="join hooks", config=SwarmConfig(topology=SwarmTopology.PARALLEL)
        )
        swarm.events.on(Hook.AGENT_JOINED_SWARM, lambda ctx: joined.append(ctx))
        await swarm.run()
        assert len(joined) == 3

    async def test_agent_left_fires_per_agent(self) -> None:
        """Hook.AGENT_LEFT_SWARM fires once per agent when it completes."""
        left: list[EventContext] = []
        agents = [_make_agent(f"r{i}") for i in range(2)]
        swarm = Swarm(
            agents=agents, goal="leave hooks", config=SwarmConfig(topology=SwarmTopology.PARALLEL)
        )
        swarm.events.on(Hook.AGENT_LEFT_SWARM, lambda ctx: left.append(ctx))
        await swarm.run()
        assert len(left) == 2

    async def test_swarm_ended_fires_once(self) -> None:
        """Hook.SWARM_ENDED fires exactly once after all agents complete."""
        ended: list[EventContext] = []
        agents = [_make_agent(f"r{i}") for i in range(2)]
        swarm = Swarm(
            agents=agents, goal="end hook", config=SwarmConfig(topology=SwarmTopology.PARALLEL)
        )
        swarm.events.on(Hook.SWARM_ENDED, lambda ctx: ended.append(ctx))
        await swarm.run()
        assert len(ended) == 1

    async def test_started_fires_before_agent_joined(self) -> None:
        """SWARM_STARTED fires before any AGENT_JOINED_SWARM."""
        order: list[str] = []
        a = _make_agent("r")
        swarm = Swarm(
            agents=[a], goal="order test", config=SwarmConfig(topology=SwarmTopology.PARALLEL)
        )
        swarm.events.on(Hook.SWARM_STARTED, lambda _ctx: order.append("STARTED"))
        swarm.events.on(Hook.AGENT_JOINED_SWARM, lambda _ctx: order.append("JOINED"))
        swarm.events.on(Hook.SWARM_ENDED, lambda _ctx: order.append("ENDED"))
        await swarm.run()
        assert order[0] == "STARTED"
        assert order[-1] == "ENDED"


@pytest.mark.phase_2
class TestParallelFallback:
    """PARALLEL topology applies FallbackStrategy on agent failure."""

    async def test_skip_and_continue_returns_partial_result(self) -> None:
        """With SKIP_AND_CONTINUE, failed agent is skipped and others' output is returned."""
        a = _make_agent("good output")
        bad = _make_failing_agent("BadAgent")
        swarm = Swarm(
            agents=[a, bad],
            goal="fail test",
            config=SwarmConfig(
                topology=SwarmTopology.PARALLEL, on_agent_failure=FallbackStrategy.SKIP_AND_CONTINUE
            ),
        )
        result = await swarm.run()
        assert "good output" in result.content
        assert isinstance(result, SwarmResult)

    async def test_abort_swarm_raises_or_returns_partial(self) -> None:
        """With ABORT_SWARM, one failure terminates the swarm."""
        a = _make_agent("good")
        bad = _make_failing_agent("Bomb")
        swarm = Swarm(
            agents=[a, bad],
            goal="abort test",
            config=SwarmConfig(
                topology=SwarmTopology.PARALLEL, on_agent_failure=FallbackStrategy.ABORT_SWARM
            ),
        )
        with pytest.raises((RuntimeError, ValueError)):
            await swarm.run()

    async def test_agent_failed_hook_fires_on_failure(self) -> None:
        """Hook.AGENT_FAILED fires when an agent raises."""
        failed: list[EventContext] = []
        bad = _make_failing_agent("Exploder")
        swarm = Swarm(
            agents=[bad],
            goal="failure hook test",
            config=SwarmConfig(
                topology=SwarmTopology.PARALLEL, on_agent_failure=FallbackStrategy.SKIP_AND_CONTINUE
            ),
        )
        swarm.events.on(Hook.AGENT_FAILED, lambda ctx: failed.append(ctx))
        await swarm.run()
        assert len(failed) >= 1

    async def test_partial_results_preserved_in_swarm_result(self) -> None:
        """SwarmResult.partial_results contains outputs of successful agents."""
        a = _make_agent("good partial")
        bad = _make_failing_agent()
        swarm = Swarm(
            agents=[a, bad],
            goal="partial results",
            config=SwarmConfig(
                topology=SwarmTopology.PARALLEL, on_agent_failure=FallbackStrategy.SKIP_AND_CONTINUE
            ),
        )
        result = await swarm.run()
        assert len(result.partial_results) >= 1
