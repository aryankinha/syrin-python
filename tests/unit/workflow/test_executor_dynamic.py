"""P1-T7: WorkflowExecutor — dynamic step tests."""

from __future__ import annotations

import pytest

from syrin import Agent, Model
from syrin.response import Response
from syrin.workflow import Workflow
from syrin.workflow.exceptions import DynamicFanoutError


def _make_agent(content: str, cost: float = 0.01) -> type[Agent]:
    """Create an agent that returns *content*."""

    class _Stub(Agent):
        model = Model.Almock()
        system_prompt = "stub"

        async def arun(self, input_text: str) -> Response[str]:
            return Response(content=content, cost=cost)

    _Stub.__name__ = f"Stub_{content[:8].replace(' ', '_')}"
    return _Stub


@pytest.mark.phase_1
class TestDynamicThreeAgents:
    """Lambda returning 3 tuples → 3 agents spawn in parallel."""

    async def test_three_agents_spawned(self) -> None:
        """Three agents run and their outputs are combined."""
        A = _make_agent("reddit findings")
        B = _make_agent("hn findings")
        C = _make_agent("arxiv findings")

        wf = Workflow("dynamic-three").dynamic(
            fn=lambda _ctx: [
                (A, "search reddit", 0.50),
                (B, "search hn", 0.50),
                (C, "search arxiv", 0.50),
            ],
        )
        result = await wf.run("research AI trends")

        assert "reddit findings" in result.content
        assert "hn findings" in result.content
        assert "arxiv findings" in result.content


@pytest.mark.phase_1
class TestDynamicOneAgent:
    """Lambda returning 1 tuple → 1 agent runs."""

    async def test_single_agent_runs(self) -> None:
        """Single agent from dynamic step runs correctly."""
        A = _make_agent("single result")

        wf = Workflow("dynamic-one").dynamic(
            fn=lambda _ctx: [(A, "do one thing", 1.00)],
        )
        result = await wf.run("task")
        assert result.content == "single result"


@pytest.mark.phase_1
class TestDynamicEmptyList:
    """Lambda returning empty list → DynamicFanoutError (zero agents is invalid)."""

    async def test_empty_list_raises_fanout_error(self) -> None:
        """Zero agents from dynamic factory raises DynamicFanoutError."""
        wf = Workflow("dynamic-empty").dynamic(fn=lambda _ctx: [])

        with pytest.raises(DynamicFanoutError) as exc_info:
            await wf.run("task")

        assert exc_info.value.actual == 0


@pytest.mark.phase_1
class TestDynamicMaxAgents:
    """max_agents=5, lambda returns 6 → DynamicFanoutError before any agent starts."""

    async def test_exceeding_max_agents_raises(self) -> None:
        """Exceeding max_agents raises DynamicFanoutError."""
        A = _make_agent("result")

        def too_many_fn(ctx: object) -> list[tuple[type[Agent], str, float]]:
            return [(A, f"task {i}", 0.1) for i in range(6)]

        wf = Workflow("too-many").dynamic(fn=too_many_fn, max_agents=5)

        with pytest.raises(DynamicFanoutError) as exc_info:
            await wf.run("task")

        assert exc_info.value.actual == 6
        assert exc_info.value.maximum == 5

    async def test_exactly_max_agents_is_allowed(self) -> None:
        """Returning exactly max_agents agents is valid."""
        A = _make_agent("ok")

        def exactly_five(ctx: object) -> list[tuple[type[Agent], str, float]]:
            return [(A, f"task {i}", 0.1) for i in range(5)]

        wf = Workflow("exactly-max").dynamic(fn=exactly_five, max_agents=5)
        result = await wf.run("task")
        assert result.content  # should have content


@pytest.mark.phase_1
class TestDynamicCtxData:
    """ctx.data is passed to the lambda from the previous step."""

    async def test_ctx_data_from_previous_step(self) -> None:
        """Lambda receives HandoffContext; can access ctx.content."""
        received_contexts: list[object] = []
        A = _make_agent("dynamic result")

        def fn(ctx: object) -> list[tuple[type[Agent], str, float]]:
            received_contexts.append(ctx)
            return [(A, "task", 0.10)]

        class PrevStep(Agent):
            model = Model.Almock()
            system_prompt = "prev"

            async def arun(self, input_text: str) -> Response[str]:
                return Response(content="previous output", cost=0.01)

        wf = Workflow("ctx-data").step(PrevStep).dynamic(fn=fn)
        await wf.run("input")

        assert len(received_contexts) == 1
        ctx = received_contexts[0]
        assert hasattr(ctx, "content")
        assert ctx.content == "previous output"


@pytest.mark.phase_1
class TestDynamicCtxDataNone:
    """ctx.data is None when previous step has no output_type."""

    async def test_ctx_data_none_without_output_type(self) -> None:
        """Lambda receives context with data=None for plain text steps."""
        received_data: list[object] = [object()]  # sentinel

        class PrevStep(Agent):
            model = Model.Almock()
            system_prompt = "prev"

            async def arun(self, input_text: str) -> Response[str]:
                return Response(content="plain text", cost=0.01)

        A = _make_agent("result")

        def fn(ctx: object) -> list[tuple[type[Agent], str, float]]:
            received_data[0] = getattr(ctx, "data", "NOT_SET")
            return [(A, "task", 0.10)]

        wf = Workflow("ctx-none-data").step(PrevStep).dynamic(fn=fn)
        await wf.run("input")

        assert received_data[0] is None


@pytest.mark.phase_1
class TestDynamicBudgetPerAgent:
    """Each spawned agent gets exactly the budget from its tuple."""

    async def test_agent_receives_correct_budget(self) -> None:
        """The budget in each tuple is used to create the agent's Budget."""
        budgets_used: list[float | None] = []

        class BudgetCapture(Agent):
            model = Model.Almock()
            system_prompt = "capture budget"

            def __init__(self, **kwargs: object) -> None:
                super().__init__(**kwargs)
                b = self._budget
                if b is not None:
                    budgets_used.append(b.max_cost)
                else:
                    budgets_used.append(None)

            async def arun(self, input_text: str) -> Response[str]:
                return Response(content="ok", cost=0.01)

        wf = Workflow("budget-check").dynamic(
            fn=lambda _ctx: [
                (BudgetCapture, "task1", 1.00),
                (BudgetCapture, "task2", 2.00),
            ],
        )
        await wf.run("go")

        assert len(budgets_used) == 2
        assert 1.00 in budgets_used
        assert 2.00 in budgets_used
