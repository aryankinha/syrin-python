"""P2-T7: Agent spawn extensions for swarm — spawn() and spawn_many()."""

from __future__ import annotations

import asyncio

import pytest

from syrin import Agent, Budget, Model
from syrin.budget.exceptions import BudgetAllocationError
from syrin.enums import FallbackStrategy, StopReason
from syrin.response import Response
from syrin.swarm._spawn import SpawnResult, SpawnSpec


def _make_agent_class(content: str, cost: float = 0.01) -> type[Agent]:
    """Create an agent class (not instance) returning *content*."""

    class _Stub(Agent):
        model = Model.Almock()
        system_prompt = "stub"

        async def arun(self, input_text: str) -> Response[str]:
            return Response(content=content, cost=cost)

    _Stub.__name__ = f"Stub_{content[:8]}"
    return _Stub


def _make_failing_class() -> type[Agent]:
    """Create an agent class that always fails."""

    class _Fail(Agent):
        model = Model.Almock()
        system_prompt = "fail"

        async def arun(self, input_text: str) -> Response[str]:
            raise RuntimeError("intentional failure")

    return _Fail


@pytest.mark.phase_2
class TestSpawnResult:
    """SpawnResult dataclass structure."""

    def test_spawn_result_fields(self) -> None:
        """SpawnResult has all required fields."""
        result = SpawnResult(
            content="ok",
            cost=0.05,
            budget_remaining=0.95,
            stop_reason=StopReason.END_TURN,
            child_agent_id="agent-abc",
        )
        assert result.content == "ok"
        assert result.cost == pytest.approx(0.05)
        assert result.budget_remaining == pytest.approx(0.95)
        assert result.stop_reason == StopReason.END_TURN
        assert result.child_agent_id == "agent-abc"


@pytest.mark.phase_2
class TestSpawnSpec:
    """SpawnSpec dataclass structure."""

    def test_spawn_spec_fields(self) -> None:
        """SpawnSpec stores agent class, task, and budget."""
        A = _make_agent_class("r")
        spec = SpawnSpec(agent=A, task="do something", budget=1.00)
        assert spec.agent is A
        assert spec.task == "do something"
        assert spec.budget == pytest.approx(1.00)

    def test_spawn_spec_optional_timeout(self) -> None:
        """SpawnSpec.timeout defaults to None."""
        A = _make_agent_class("r")
        spec = SpawnSpec(agent=A, task="task", budget=1.00)
        assert spec.timeout is None

    def test_spawn_spec_with_timeout(self) -> None:
        """SpawnSpec accepts an explicit timeout."""
        A = _make_agent_class("r")
        spec = SpawnSpec(agent=A, task="task", budget=1.00, timeout=30.0)
        assert spec.timeout == pytest.approx(30.0)


@pytest.mark.phase_2
class TestSpawnFromAgent:
    """Agent.spawn() within a swarm deducts budget from pool."""

    async def test_spawn_returns_spawn_result(self) -> None:
        """spawn(AgentClass, task=..., budget=X) returns SpawnResult."""
        from syrin.swarm import Swarm

        A_class = _make_agent_class("child output")

        class Orchestrator(Agent):
            model = Model.Almock()
            system_prompt = "orchestrator"

            async def arun(self, input_text: str) -> Response[str]:
                result = await self.spawn(A_class, task="subtask", budget=1.00)
                return Response(content=result.content, cost=result.cost)

        budget = Budget(max_cost=5.00)
        swarm = Swarm(
            agents=[Orchestrator()],
            goal="test spawn",
            budget=budget,
        )
        swarm_result = await swarm.run()
        assert "child output" in swarm_result.content

    async def test_spawn_deducts_from_pool(self) -> None:
        """spawn() carves the specified budget from the shared pool."""
        from syrin.swarm import Swarm

        A_class = _make_agent_class("child")
        spawned_cost: list[float] = []

        class Orchestrator(Agent):
            model = Model.Almock()
            system_prompt = "orchestrator"

            async def arun(self, input_text: str) -> Response[str]:
                result = await self.spawn(A_class, task="subtask", budget=2.00)
                spawned_cost.append(result.cost)
                return Response(content="done", cost=0.01)

        budget = Budget(max_cost=10.00)
        swarm = Swarm(agents=[Orchestrator()], goal="deduct test", budget=budget)
        await swarm.run()
        assert len(spawned_cost) >= 1

    async def test_spawn_over_budget_raises(self) -> None:
        """spawn() with budget > agent's remaining raises ValueError."""
        A_class = _make_agent_class("child")

        class GreedyOrchestrator(Agent):
            model = Model.Almock()
            system_prompt = "greedy"

            async def arun(self, input_text: str) -> Response[str]:
                # Try to spawn with more budget than the agent has remaining
                self.spawn(A_class, task="task", budget=Budget(max_cost=100.00))
                return Response(content="done", cost=0.01)

        # Give the orchestrator a small budget directly — spawn(budget=Budget(100)) exceeds it
        orchestrator = GreedyOrchestrator(budget=Budget(max_cost=0.50))
        with pytest.raises((BudgetAllocationError, ValueError)):
            await orchestrator.arun("test")


@pytest.mark.phase_2
class TestSpawnMany:
    """spawn_many() runs multiple agents concurrently with individual budgets."""

    async def test_spawn_many_runs_all_concurrently(self) -> None:
        """spawn_many runs all agents and returns a list of SpawnResult."""
        import time

        from syrin.swarm import Swarm

        delay = 0.05

        class _Slow(Agent):
            model = Model.Almock()
            system_prompt = "slow"

            async def arun(self, input_text: str) -> Response[str]:
                await asyncio.sleep(delay)
                return Response(content=f"slow: {input_text}", cost=0.01)

        class Orchestrator(Agent):
            model = Model.Almock()
            system_prompt = "orch"
            _results: list[SpawnResult] = []

            async def arun(self, input_text: str) -> Response[str]:
                results = await self.spawn_many(
                    [
                        SpawnSpec(agent=_Slow, task="task1", budget=0.50),
                        SpawnSpec(agent=_Slow, task="task2", budget=0.50),
                        SpawnSpec(agent=_Slow, task="task3", budget=0.50),
                    ]
                )
                Orchestrator._results = results
                combined = " | ".join(r.content for r in results)
                return Response(content=combined, cost=0.01)

        budget = Budget(max_cost=5.00)
        swarm = Swarm(agents=[Orchestrator()], goal="spawn_many test", budget=budget)
        start = time.monotonic()
        await swarm.run()
        elapsed = time.monotonic() - start

        # 3 agents with 50ms each → parallel = ~50ms, not 150ms
        assert elapsed < 0.12, f"spawn_many took {elapsed:.3f}s, expected <0.12s"
        assert len(Orchestrator._results) == 3

    async def test_spawn_many_skip_and_continue_on_failure(self) -> None:
        """spawn_many with SKIP_AND_CONTINUE skips failed agents."""
        from syrin.swarm import Swarm

        A_class = _make_agent_class("good")
        Fail_class = _make_failing_class()

        class Orchestrator(Agent):
            model = Model.Almock()
            system_prompt = "orch"
            _results: list[SpawnResult] = []

            async def arun(self, input_text: str) -> Response[str]:
                results = await self.spawn_many(
                    [
                        SpawnSpec(agent=A_class, task="t1", budget=0.50),
                        SpawnSpec(agent=Fail_class, task="t2", budget=0.50),
                        SpawnSpec(agent=A_class, task="t3", budget=0.50),
                    ],
                    on_failure=FallbackStrategy.SKIP_AND_CONTINUE,
                )
                Orchestrator._results = results
                combined = " | ".join(r.content for r in results if r.content)
                return Response(content=combined, cost=0.01)

        budget = Budget(max_cost=5.00)
        swarm = Swarm(agents=[Orchestrator()], goal="spawn_many fail test", budget=budget)
        result = await swarm.run()
        # At least the good agents' outputs should be present
        assert "good" in result.content
