"""P1-T6: WorkflowExecutor — branch step tests."""

from __future__ import annotations

import pytest

from syrin import Agent, Model
from syrin.response import Response
from syrin.workflow import Workflow
from syrin.workflow.exceptions import WorkflowStepError


def _make_agent(content: str, record: list[str] | None = None) -> type[Agent]:
    """Create an agent stub that records calls and returns *content*."""

    class _Stub(Agent):
        model = Model.Almock()
        system_prompt = "stub"

        async def arun(self, input_text: str) -> Response[str]:
            if record is not None:
                record.append(self.__class__.__name__)
            return Response(content=content, cost=0.01)

    _Stub.__name__ = f"Stub_{content[:8].replace(' ', '_')}"
    return _Stub


@pytest.mark.phase_1
class TestBranchTrueCondition:
    """condition=True → if_true agent runs, if_false does not."""

    async def test_true_runs_if_true_agent(self) -> None:
        """When condition is truthy, if_true_class runs."""
        ran: list[str] = []

        class TrueAgent(Agent):
            model = Model.Almock()
            system_prompt = "true"

            async def arun(self, input_text: str) -> Response[str]:
                ran.append("true")
                return Response(content="true result", cost=0.01)

        class FalseAgent(Agent):
            model = Model.Almock()
            system_prompt = "false"

            async def arun(self, input_text: str) -> Response[str]:
                ran.append("false")
                return Response(content="false result", cost=0.01)

        wf = Workflow("branch-true").branch(
            condition=lambda _ctx: True,
            if_true=TrueAgent,
            if_false=FalseAgent,
        )
        result = await wf.run("task")

        assert "true" in ran
        assert "false" not in ran
        assert result.content == "true result"


@pytest.mark.phase_1
class TestBranchFalseCondition:
    """condition=False → if_false agent runs, if_true does not."""

    async def test_false_runs_if_false_agent(self) -> None:
        """When condition is falsy, if_false_class runs."""
        ran: list[str] = []

        class TrueAgent(Agent):
            model = Model.Almock()
            system_prompt = "true"

            async def arun(self, input_text: str) -> Response[str]:
                ran.append("true")
                return Response(content="true result", cost=0.01)

        class FalseAgent(Agent):
            model = Model.Almock()
            system_prompt = "false"

            async def arun(self, input_text: str) -> Response[str]:
                ran.append("false")
                return Response(content="false result", cost=0.01)

        wf = Workflow("branch-false").branch(
            condition=lambda _ctx: False,
            if_true=TrueAgent,
            if_false=FalseAgent,
        )
        result = await wf.run("task")

        assert "false" in ran
        assert "true" not in ran
        assert result.content == "false result"


@pytest.mark.phase_1
class TestBranchConvergence:
    """After branch, the next .step() receives the branch's output."""

    async def test_post_branch_step_receives_branch_output(self) -> None:
        """Step after branch receives the branch result as input."""
        received: list[str] = []

        class TrueAgent(Agent):
            model = Model.Almock()
            system_prompt = "true"

            async def arun(self, input_text: str) -> Response[str]:
                return Response(content="branch output", cost=0.01)

        class FalseAgent(Agent):
            model = Model.Almock()
            system_prompt = "false"

            async def arun(self, input_text: str) -> Response[str]:
                return Response(content="branch output", cost=0.01)

        class FinalAgent(Agent):
            model = Model.Almock()
            system_prompt = "final"

            async def arun(self, input_text: str) -> Response[str]:
                received.append(input_text)
                return Response(content="final output", cost=0.01)

        wf = (
            Workflow("convergence")
            .branch(condition=lambda _ctx: True, if_true=TrueAgent, if_false=FalseAgent)
            .step(FinalAgent)
        )
        result = await wf.run("initial")

        assert result.content == "final output"
        assert "branch output" in received[0]


@pytest.mark.phase_1
class TestBranchConditionWithContext:
    """ctx in condition is the HandoffContext from the step before the branch."""

    async def test_condition_receives_correct_context(self) -> None:
        """Condition callable is given the HandoffContext from the previous step."""
        ctx_received: list[object] = []

        class FirstAgent(Agent):
            model = Model.Almock()
            system_prompt = "first"

            async def arun(self, input_text: str) -> Response[str]:
                return Response(content="urgent: do this fast", cost=0.01)

        class FastAgent(Agent):
            model = Model.Almock()
            system_prompt = "fast"

            async def arun(self, input_text: str) -> Response[str]:
                return Response(content="fast result", cost=0.01)

        class SlowAgent(Agent):
            model = Model.Almock()
            system_prompt = "slow"

            async def arun(self, input_text: str) -> Response[str]:
                return Response(content="slow result", cost=0.01)

        def condition(ctx: object) -> bool:
            ctx_received.append(ctx)
            return "urgent" in getattr(ctx, "content", "")

        wf = (
            Workflow("ctx-branch")
            .step(FirstAgent)
            .branch(condition=condition, if_true=FastAgent, if_false=SlowAgent)
        )
        result = await wf.run("go")

        assert len(ctx_received) == 1
        assert result.content == "fast result"


@pytest.mark.phase_1
class TestBranchTruthyFalsy:
    """Branch condition returning non-bool (truthy/falsy) works correctly."""

    async def test_truthy_non_bool(self) -> None:
        """A non-empty string is truthy → if_true runs."""

        class TrueAgent(Agent):
            model = Model.Almock()
            system_prompt = "t"

            async def arun(self, input_text: str) -> Response[str]:
                return Response(content="true", cost=0.01)

        class FalseAgent(Agent):
            model = Model.Almock()
            system_prompt = "f"

            async def arun(self, input_text: str) -> Response[str]:
                return Response(content="false", cost=0.01)

        wf = Workflow("truthy").branch(
            condition=lambda _ctx: "truthy string",  # truthy non-bool
            if_true=TrueAgent,
            if_false=FalseAgent,
        )
        result = await wf.run("task")
        assert result.content == "true"

    async def test_falsy_non_bool(self) -> None:
        """Empty string is falsy → if_false runs."""

        class TrueAgent(Agent):
            model = Model.Almock()
            system_prompt = "t"

            async def arun(self, input_text: str) -> Response[str]:
                return Response(content="true", cost=0.01)

        class FalseAgent(Agent):
            model = Model.Almock()
            system_prompt = "f"

            async def arun(self, input_text: str) -> Response[str]:
                return Response(content="false", cost=0.01)

        wf = Workflow("falsy").branch(
            condition=lambda _ctx: "",  # falsy non-bool
            if_true=TrueAgent,
            if_false=FalseAgent,
        )
        result = await wf.run("task")
        assert result.content == "false"


@pytest.mark.phase_1
class TestBranchConditionException:
    """Branch condition raising an exception → WorkflowStepError."""

    async def test_condition_exception_raises_step_error(self) -> None:
        """When the condition callable raises, WorkflowStepError is raised."""

        class TrueAgent(Agent):
            model = Model.Almock()
            system_prompt = "t"

            async def arun(self, input_text: str) -> Response[str]:
                return Response(content="t", cost=0.01)

        class FalseAgent(Agent):
            model = Model.Almock()
            system_prompt = "f"

            async def arun(self, input_text: str) -> Response[str]:
                return Response(content="f", cost=0.01)

        def bad_condition(ctx: object) -> bool:
            raise ValueError("condition exploded")

        wf = Workflow("bad-branch").branch(
            condition=bad_condition,
            if_true=TrueAgent,
            if_false=FalseAgent,
        )
        with pytest.raises(WorkflowStepError) as exc_info:
            await wf.run("task")

        assert isinstance(exc_info.value.cause, ValueError)
