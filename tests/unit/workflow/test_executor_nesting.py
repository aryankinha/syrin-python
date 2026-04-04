"""P1-T8: WorkflowExecutor — nested workflow tests."""

from __future__ import annotations

import pytest

from syrin import Agent, Budget, Model
from syrin.response import Response
from syrin.workflow import Workflow


def _make_agent(content: str, cost: float = 0.01) -> type[Agent]:
    """Create a stub agent."""

    class _Stub(Agent):
        model = Model.Almock()
        system_prompt = "stub"

        async def arun(self, input_text: str) -> Response[str]:
            return Response(content=content, cost=cost)

    _Stub.__name__ = f"Stub_{content[:10].replace(' ', '_')}"
    return _Stub


@pytest.mark.phase_1
class TestSubWorkflowAsStep:
    """Sub-workflow used as a step: output flows to parent's next step."""

    async def test_sub_workflow_output_flows_to_parent(self) -> None:
        """Sub-workflow result is passed as input to the next parent step."""
        received: list[str] = []

        A = _make_agent("sub result")

        class ParentStep(Agent):
            model = Model.Almock()
            system_prompt = "parent step"

            async def arun(self, input_text: str) -> Response[str]:
                received.append(input_text)
                return Response(content="parent result", cost=0.01)

        sub_wf = Workflow("sub-workflow").step(A)

        parent_wf = Workflow("parent").step(sub_wf).step(ParentStep)
        result = await parent_wf.run("initial input")

        assert result.content == "parent result"
        assert "sub result" in received[0]

    async def test_sub_workflow_runs_its_own_steps(self) -> None:
        """Sub-workflow executes all its own steps independently."""
        A = _make_agent("step 1 of sub")
        B = _make_agent("step 2 of sub")

        sub_wf = Workflow("sub").step(A).step(B)
        parent_wf = Workflow("parent").step(sub_wf)

        result = await parent_wf.run("start")
        assert result.content == "step 2 of sub"


@pytest.mark.phase_1
class TestNestedWorkflowBudget:
    """Sub-workflow budget is bounded by parent's remaining budget."""

    async def test_sub_workflow_with_smaller_budget(self) -> None:
        """Sub-workflow executes within a tighter budget than parent."""
        A = _make_agent("sub result")
        sub_wf = Workflow("sub", budget=Budget(max_cost=0.50)).step(A)
        parent_wf = Workflow("parent", budget=Budget(max_cost=10.00)).step(sub_wf)

        result = await parent_wf.run("task")
        assert result.content == "sub result"


@pytest.mark.phase_1
class TestDeeplyNestedWorkflow:
    """Nested 3 levels deep: works without infinite recursion."""

    async def test_three_level_nesting(self) -> None:
        """Three levels of workflow nesting all produce results correctly."""
        A = _make_agent("deep result")

        level3 = Workflow("level3").step(A)
        level2 = Workflow("level2").step(level3)
        level1 = Workflow("level1").step(level2)

        result = await level1.run("task")
        assert result.content == "deep result"


@pytest.mark.phase_1
class TestWorkflowAsServable:
    """Workflow satisfies Agent interface: has run(), arun(), budget property."""

    async def test_workflow_has_run_method(self) -> None:
        """Workflow.run() is a coroutine."""
        import inspect

        A = _make_agent("result")
        wf = Workflow("test").step(A)
        assert inspect.iscoroutinefunction(wf.run)

    async def test_workflow_has_arun_method(self) -> None:
        """Workflow.arun() is a coroutine and is identical to run()."""
        import inspect

        A = _make_agent("result")
        wf = Workflow("test").step(A)
        assert inspect.iscoroutinefunction(wf.arun)

    async def test_workflow_has_budget_property(self) -> None:
        """Workflow exposes a budget property."""
        bgt = Budget(max_cost=5.00)
        wf = Workflow("test", budget=bgt).step(_make_agent("x"))
        assert wf.budget is bgt

    async def test_workflow_as_step_in_another_workflow(self) -> None:
        """Workflow can be used as a step in a parent Workflow."""
        A = _make_agent("inner result")
        inner = Workflow("inner").step(A)

        outer = Workflow("outer").step(inner)
        result = await outer.run("task")
        assert result.content == "inner result"
