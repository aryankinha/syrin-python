"""P1-T5: WorkflowExecutor — parallel step tests."""

from __future__ import annotations

import asyncio
import time

import pytest

from syrin import Agent, Model
from syrin.enums import Hook
from syrin.events import EventContext
from syrin.response import Response
from syrin.workflow import Workflow


def _make_delayed_agent(content: str, delay: float = 0.0, cost: float = 0.01) -> type[Agent]:
    """Create an agent that sleeps for *delay* seconds before responding."""

    class _Delayed(Agent):
        model = Model.Almock()
        system_prompt = f"Delayed agent: {content}"

        async def arun(self, input_text: str) -> Response[str]:
            if delay > 0:
                await asyncio.sleep(delay)
            return Response(content=content, cost=cost)

    _Delayed.__name__ = f"Delayed_{content[:10].replace(' ', '_')}"
    return _Delayed


@pytest.mark.phase_1
class TestParallelConcurrency:
    """All agents in a ParallelStep start concurrently."""

    async def test_parallel_faster_than_sequential(self) -> None:
        """Two 50ms agents run in ~50ms in parallel, not ~100ms sequentially."""
        A = _make_delayed_agent("a output", delay=0.05)
        B = _make_delayed_agent("b output", delay=0.05)

        wf = Workflow("parallel-test").parallel([A, B])
        start = time.monotonic()
        result = await wf.run("go")
        elapsed = time.monotonic() - start

        # Should complete in ~50ms, not ~100ms
        assert elapsed < 0.09, f"Parallel execution was too slow: {elapsed:.3f}s"
        assert "a output" in result.content
        assert "b output" in result.content

    async def test_parallel_merged_content(self) -> None:
        """Next step receives merged outputs from all parallel agents."""
        received_content: list[str] = []

        class Collector(Agent):
            model = Model.Almock()
            system_prompt = "collect"

            async def arun(self, input_text: str) -> Response[str]:
                received_content.append(input_text)
                return Response(content="collected", cost=0.01)

        A = _make_delayed_agent("a result")
        B = _make_delayed_agent("b result")

        wf = Workflow("merge-test").parallel([A, B]).step(Collector)
        await wf.run("input")

        assert len(received_content) == 1
        assert "a result" in received_content[0]
        assert "b result" in received_content[0]


@pytest.mark.phase_1
class TestParallelBudget:
    """Budget decreases by sum of parallel agent costs."""

    async def test_parallel_budget_accumulates(self) -> None:
        """Total cost reflects sum of all parallel agents."""
        A = _make_delayed_agent("a", cost=0.05)
        B = _make_delayed_agent("b", cost=0.07)

        wf = Workflow("budget-test").parallel([A, B])
        result = await wf.run("task")

        # Both agent costs should be present
        assert result.cost == pytest.approx(0.12)

    async def test_three_parallel_agents(self) -> None:
        """Three agents in parallel all run and produce output."""
        A = _make_delayed_agent("alpha")
        B = _make_delayed_agent("beta")
        C = _make_delayed_agent("gamma")

        wf = Workflow("three-parallel").parallel([A, B, C])
        result = await wf.run("task")

        assert "alpha" in result.content
        assert "beta" in result.content
        assert "gamma" in result.content


@pytest.mark.phase_1
class TestParallelHooks:
    """WORKFLOW_STEP_START fires once per parallel group, STEP_END fires when all complete."""

    async def test_step_start_fires_once(self) -> None:
        """WORKFLOW_STEP_START fires once per ParallelStep, not once per agent."""
        step_starts: list[EventContext] = []

        A = _make_delayed_agent("a")
        B = _make_delayed_agent("b")

        wf = Workflow("hook-test").parallel([A, B])
        wf.events.on(Hook.WORKFLOW_STEP_START, lambda ctx: step_starts.append(ctx))

        await wf.run("task")

        # Only 1 WORKFLOW_STEP_START for the parallel step (not 2)
        assert len(step_starts) == 1

    async def test_step_end_fires_once(self) -> None:
        """WORKFLOW_STEP_END fires once after all parallel agents complete."""
        step_ends: list[EventContext] = []

        A = _make_delayed_agent("a")
        B = _make_delayed_agent("b")

        wf = Workflow("hook-end-test").parallel([A, B])
        wf.events.on(Hook.WORKFLOW_STEP_END, lambda ctx: step_ends.append(ctx))

        await wf.run("task")

        assert len(step_ends) == 1
