"""P1-T9: Workflow class — builder API tests."""

from __future__ import annotations

import pytest

from syrin import Agent, Budget, Model
from syrin.response import Response
from syrin.workflow import Workflow
from syrin.workflow._step import BranchStep, DynamicStep, ParallelStep, SequentialStep
from syrin.workflow.exceptions import WorkflowNotRunnable


class AgentA(Agent):
    """Stub agent A."""

    model = Model.Almock()
    system_prompt = "A"


class AgentB(Agent):
    """Stub agent B."""

    model = Model.Almock()
    system_prompt = "B"


class AgentC(Agent):
    """Stub agent C."""

    model = Model.Almock()
    system_prompt = "C"


class AgentD(Agent):
    """Stub agent D."""

    model = Model.Almock()
    system_prompt = "D"


@pytest.mark.phase_1
class TestWorkflowConstruction:
    """Workflow() creates a workflow with no steps."""

    def test_empty_workflow_has_zero_steps(self) -> None:
        """A freshly constructed Workflow has no steps."""
        wf = Workflow("test")
        assert wf.step_count == 0

    def test_workflow_has_name(self) -> None:
        """Workflow stores the provided name."""
        wf = Workflow("my-workflow")
        assert wf.name == "my-workflow"

    def test_default_name(self) -> None:
        """Workflow defaults to 'workflow' when no name provided."""
        wf = Workflow()
        assert wf.name == "workflow"

    def test_two_instances_dont_share_steps(self) -> None:
        """Two Workflow instances do not share step lists."""
        wf1 = Workflow("wf1")
        wf2 = Workflow("wf2")
        wf1.step(AgentA)
        assert wf2.step_count == 0
        assert wf1.step_count == 1


@pytest.mark.phase_1
class TestStepBuilderMethod:
    """.step(A) adds a SequentialStep, returns self (fluent interface)."""

    def test_step_adds_sequential_step(self) -> None:
        """.step() appends a SequentialStep."""
        wf = Workflow("test")
        wf.step(AgentA)
        assert wf.step_count == 1
        assert isinstance(wf._steps[0], SequentialStep)

    def test_step_returns_self(self) -> None:
        """.step() returns the Workflow for chaining."""
        wf = Workflow("test")
        result = wf.step(AgentA)
        assert result is wf

    def test_step_with_task_override(self) -> None:
        """.step(A, task=...) stores the task override."""
        wf = Workflow("test").step(AgentA, task="override task")
        step = wf._steps[0]
        assert isinstance(step, SequentialStep)
        assert step.task == "override task"

    def test_step_with_budget_override(self) -> None:
        """.step(A, budget=...) stores the budget override."""
        bgt = Budget(max_cost=0.50)
        wf = Workflow("test").step(AgentA, budget=bgt)
        step = wf._steps[0]
        assert isinstance(step, SequentialStep)
        assert step.budget is bgt


@pytest.mark.phase_1
class TestParallelBuilderMethod:
    """.parallel([A, B]) adds a ParallelStep, returns self."""

    def test_parallel_adds_parallel_step(self) -> None:
        """.parallel() appends a ParallelStep."""
        wf = Workflow("test").parallel([AgentA, AgentB])
        assert wf.step_count == 1
        assert isinstance(wf._steps[0], ParallelStep)

    def test_parallel_returns_self(self) -> None:
        """.parallel() returns the Workflow for chaining."""
        wf = Workflow("test")
        result = wf.parallel([AgentA, AgentB])
        assert result is wf

    def test_parallel_stores_agent_classes(self) -> None:
        """.parallel() stores all provided agent classes."""
        wf = Workflow("test").parallel([AgentA, AgentB, AgentC])
        step = wf._steps[0]
        assert isinstance(step, ParallelStep)
        assert AgentA in step.agent_classes
        assert AgentB in step.agent_classes
        assert AgentC in step.agent_classes


@pytest.mark.phase_1
class TestBranchBuilderMethod:
    """.branch(condition, if_true, if_false) adds a BranchStep, returns self."""

    def test_branch_adds_branch_step(self) -> None:
        """.branch() appends a BranchStep."""
        wf = Workflow("test").branch(
            condition=lambda _ctx: True,
            if_true=AgentA,
            if_false=AgentB,
        )
        assert wf.step_count == 1
        assert isinstance(wf._steps[0], BranchStep)

    def test_branch_returns_self(self) -> None:
        """.branch() returns the Workflow for chaining."""
        wf = Workflow("test")
        result = wf.branch(condition=lambda _ctx: True, if_true=AgentA, if_false=AgentB)
        assert result is wf


@pytest.mark.phase_1
class TestDynamicBuilderMethod:
    """.dynamic(fn) adds a DynamicStep, returns self."""

    def test_dynamic_adds_dynamic_step(self) -> None:
        """.dynamic() appends a DynamicStep."""
        wf = Workflow("test").dynamic(fn=lambda _ctx: [])
        assert wf.step_count == 1
        assert isinstance(wf._steps[0], DynamicStep)

    def test_dynamic_returns_self(self) -> None:
        """.dynamic() returns the Workflow for chaining."""
        wf = Workflow("test")
        result = wf.dynamic(fn=lambda _ctx: [])
        assert result is wf

    def test_dynamic_with_max_agents(self) -> None:
        """.dynamic(fn, max_agents=N) stores the cap."""
        wf = Workflow("test").dynamic(fn=lambda _ctx: [], max_agents=10)
        step = wf._steps[0]
        assert isinstance(step, DynamicStep)
        assert step.max_agents == 10


@pytest.mark.phase_1
class TestMethodChaining:
    """Chaining all four builder methods builds a 4-step graph."""

    def test_chain_all_step_types(self) -> None:
        """Chaining .step().parallel().branch().step() builds 4 steps."""
        wf = (
            Workflow("chain")
            .step(AgentA)
            .parallel([AgentB, AgentC])
            .branch(condition=lambda _ctx: True, if_true=AgentA, if_false=AgentB)
            .step(AgentD)
        )
        assert wf.step_count == 4

    def test_step_count_increments_with_each_method(self) -> None:
        """step_count reflects the exact number of calls."""
        wf = Workflow("count")
        assert wf.step_count == 0
        wf.step(AgentA)
        assert wf.step_count == 1
        wf.step(AgentB)
        assert wf.step_count == 2
        wf.parallel([AgentA, AgentB])
        assert wf.step_count == 3


@pytest.mark.phase_1
class TestWorkflowRunnable:
    """Workflow.run() raises WorkflowNotRunnable if no steps added."""

    async def test_empty_workflow_raises(self) -> None:
        """run() on an empty workflow raises WorkflowNotRunnable."""
        wf = Workflow("empty")
        with pytest.raises(WorkflowNotRunnable):
            await wf.run("task")

    async def test_workflow_with_steps_does_not_raise(self) -> None:
        """run() on a non-empty workflow works correctly."""

        class SimpleAgent(Agent):
            model = Model.Almock()
            system_prompt = "simple"

            async def arun(self, input_text: str) -> Response[str]:
                return Response(content="ok", cost=0.01)

        wf = Workflow("has-steps").step(SimpleAgent)
        result = await wf.run("task")
        assert result.content == "ok"
