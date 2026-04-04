"""P1-T10: Workflow run interface tests."""

from __future__ import annotations

import inspect

import pytest

from syrin import Agent, Budget, Model
from syrin.response import Response
from syrin.workflow import Workflow


def _make_agent(content: str, cost: float = 0.01) -> type[Agent]:
    """Create an agent returning *content*."""

    class _Stub(Agent):
        model = Model.Almock()
        system_prompt = "stub"

        async def arun(self, input_text: str) -> Response[str]:
            return Response(content=content, cost=cost)

    _Stub.__name__ = f"Stub_{content[:10].replace(' ', '_')}"
    return _Stub


@pytest.mark.phase_1
class TestRunReturnsResponse:
    """await wf.run() returns Response with expected content."""

    async def test_run_returns_response(self) -> None:
        """run() resolves to the final step's Response."""
        A = _make_agent("hello world")
        wf = Workflow("test").step(A)
        result = await wf.run("go")

        assert isinstance(result, Response)
        assert result.content == "hello world"

    async def test_run_with_multistep(self) -> None:
        """run() with two steps returns the second step's output."""
        A = _make_agent("step one")
        B = _make_agent("step two")
        wf = Workflow("two-step").step(A).step(B)
        result = await wf.run("start")

        assert result.content == "step two"


@pytest.mark.phase_1
class TestArunIdenticalToRun:
    """arun() is identical to run()."""

    async def test_arun_returns_same_content(self) -> None:
        """arun() and run() return the same Response content."""
        A = _make_agent("same result")
        wf1 = Workflow("run-wf").step(A)
        wf2 = Workflow("arun-wf").step(A)

        r1 = await wf1.run("task")
        r2 = await wf2.arun("task")

        assert r1.content == r2.content

    async def test_arun_is_coroutine(self) -> None:
        """arun() is a coroutine function."""
        A = _make_agent("ok")
        wf = Workflow("test").step(A)
        assert inspect.iscoroutinefunction(wf.arun)

    async def test_run_is_coroutine(self) -> None:
        """run() is a coroutine function."""
        A = _make_agent("ok")
        wf = Workflow("test").step(A)
        assert inspect.iscoroutinefunction(wf.run)


@pytest.mark.phase_1
class TestWorkflowAgentInterface:
    """Workflow satisfies the Agent interface (run, arun, budget)."""

    async def test_workflow_has_budget_property(self) -> None:
        """Workflow exposes a budget property."""
        bgt = Budget(max_cost=5.00)
        A = _make_agent("x")
        wf = Workflow("budgeted", budget=bgt).step(A)
        assert wf.budget is bgt

    async def test_workflow_default_budget_is_none_or_unlimited(self) -> None:
        """Workflow without explicit budget returns None or an unlimited Budget."""
        A = _make_agent("x")
        wf = Workflow("no-budget").step(A)
        # budget is either None or a Budget with no cap — run must not raise
        result = await wf.run("task")
        assert result.content == "x"

    async def test_workflow_arun_accepts_input(self) -> None:
        """arun() accepts an input string (same signature as Agent.arun)."""
        received: list[str] = []

        class Capture(Agent):
            model = Model.Almock()
            system_prompt = "capture"

            async def arun(self, input_text: str) -> Response[str]:
                received.append(input_text)
                return Response(content="captured", cost=0.0)

        wf = Workflow("capture-wf").step(Capture)
        await wf.arun("my input")

        assert received[0] == "my input"


@pytest.mark.phase_1
class TestWorkflowNestable:
    """Workflow can be used as a step in another Workflow."""

    async def test_nested_workflow_as_step(self) -> None:
        """A Workflow used as a step produces output flowing to the next step."""
        A = _make_agent("inner output")
        inner = Workflow("inner").step(A)

        outer = Workflow("outer").step(inner)
        result = await outer.run("task")
        assert result.content == "inner output"

    async def test_nested_workflow_output_used_by_next_step(self) -> None:
        """Sub-workflow output is passed as input to the next parent step."""
        received: list[str] = []
        A = _make_agent("from sub")

        class NextStep(Agent):
            model = Model.Almock()
            system_prompt = "next"

            async def arun(self, input_text: str) -> Response[str]:
                received.append(input_text)
                return Response(content="parent done", cost=0.01)

        inner = Workflow("inner").step(A)
        outer = Workflow("outer").step(inner).step(NextStep)
        result = await outer.run("start")

        assert result.content == "parent done"
        assert "from sub" in received[0]


class TestWorkflowRunSync:
    """Workflow.run_sync() works in non-async contexts."""

    def test_run_sync_returns_response(self) -> None:
        """run_sync() returns Response without asyncio boilerplate."""
        A = _make_agent("sync result")
        wf = Workflow("sync-test").step(A)
        result = wf.run_sync("input")
        assert result.content == "sync result"
        assert isinstance(result.cost, float)

    def test_run_sync_chains_steps(self) -> None:
        """run_sync() chains multiple sequential steps correctly."""
        A = _make_agent("step one")
        B = _make_agent("step two")
        wf = Workflow("chain").step(A).step(B)
        result = wf.run_sync("start")
        assert result.content == "step two"
