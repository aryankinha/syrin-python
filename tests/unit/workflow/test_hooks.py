"""P1-T15: Workflow lifecycle hooks integration tests."""

from __future__ import annotations

import pytest

from syrin import Agent, Model
from syrin.enums import Hook
from syrin.events import EventContext
from syrin.response import Response
from syrin.workflow import Workflow
from syrin.workflow.exceptions import WorkflowStepError


def _make_agent(content: str, cost: float = 0.01) -> type[Agent]:
    """Create a stub agent returning *content*."""

    class _Stub(Agent):
        model = Model.Almock()
        system_prompt = "stub"

        async def arun(self, input_text: str) -> Response[str]:
            return Response(content=content, cost=cost)

    _Stub.__name__ = f"Stub_{content[:10].replace(' ', '_')}"
    return _Stub


def _make_failing_agent() -> type[Agent]:
    """Create an agent that always raises."""

    class _Fail(Agent):
        model = Model.Almock()
        system_prompt = "fail"

        async def arun(self, input_text: str) -> Response[str]:
            raise RuntimeError("agent exploded")

    return _Fail


@pytest.mark.phase_1
class TestWorkflowStartedHook:
    """Hook.WORKFLOW_STARTED fires at the beginning of a run."""

    async def test_started_fires_once(self) -> None:
        """WORKFLOW_STARTED fires exactly once per run."""
        events: list[EventContext] = []
        A = _make_agent("result")
        wf = Workflow("hook-test").step(A)
        wf.events.on(Hook.WORKFLOW_STARTED, lambda ctx: events.append(ctx))

        await wf.run("input")

        assert len(events) == 1

    async def test_started_has_workflow_name(self) -> None:
        """WORKFLOW_STARTED context includes workflow_name."""
        events: list[EventContext] = []
        A = _make_agent("result")
        wf = Workflow("my-named-wf").step(A)
        wf.events.on(Hook.WORKFLOW_STARTED, lambda ctx: events.append(ctx))

        await wf.run("input")

        ctx = events[0]
        assert getattr(ctx, "workflow_name", None) == "my-named-wf"

    async def test_started_has_run_id(self) -> None:
        """WORKFLOW_STARTED context includes a non-empty run_id."""
        events: list[EventContext] = []
        A = _make_agent("result")
        wf = Workflow("run-id-test").step(A)
        wf.events.on(Hook.WORKFLOW_STARTED, lambda ctx: events.append(ctx))

        await wf.run("input")

        ctx = events[0]
        run_id = getattr(ctx, "run_id", None)
        assert run_id is not None
        assert isinstance(run_id, str)
        assert len(run_id) > 0

    async def test_two_runs_have_different_run_ids(self) -> None:
        """Each run() call produces a unique run_id."""
        run_ids: list[str] = []
        A = _make_agent("result")
        wf = Workflow("unique-ids").step(A)
        wf.events.on(
            Hook.WORKFLOW_STARTED,
            lambda ctx: run_ids.append(getattr(ctx, "run_id", "")),
        )

        await wf.run("input1")
        await wf.run("input2")

        assert len(run_ids) == 2
        assert run_ids[0] != run_ids[1]


@pytest.mark.phase_1
class TestStepStartHook:
    """Hook.WORKFLOW_STEP_START fires before each step."""

    async def test_step_start_fires_per_step(self) -> None:
        """WORKFLOW_STEP_START fires once per sequential step."""
        events: list[EventContext] = []
        A = _make_agent("a")
        B = _make_agent("b")
        wf = Workflow("step-hooks").step(A).step(B)
        wf.events.on(Hook.WORKFLOW_STEP_START, lambda ctx: events.append(ctx))

        await wf.run("go")

        assert len(events) == 2

    async def test_step_start_includes_step_index(self) -> None:
        """WORKFLOW_STEP_START context includes correct step_index."""
        indices: list[int] = []
        A = _make_agent("a")
        B = _make_agent("b")
        wf = Workflow("idx-test").step(A).step(B)
        wf.events.on(
            Hook.WORKFLOW_STEP_START,
            lambda ctx: indices.append(getattr(ctx, "step_index", -1)),
        )

        await wf.run("go")

        assert 0 in indices
        assert 1 in indices


@pytest.mark.phase_1
class TestStepEndHook:
    """Hook.WORKFLOW_STEP_END fires after each step completes."""

    async def test_step_end_fires_per_step(self) -> None:
        """WORKFLOW_STEP_END fires once per sequential step."""
        events: list[EventContext] = []
        A = _make_agent("a")
        B = _make_agent("b")
        wf = Workflow("end-hooks").step(A).step(B)
        wf.events.on(Hook.WORKFLOW_STEP_END, lambda ctx: events.append(ctx))

        await wf.run("go")

        assert len(events) == 2

    async def test_step_end_includes_cost(self) -> None:
        """WORKFLOW_STEP_END context includes 'cost' for the step."""
        costs: list[float] = []
        A = _make_agent("a", cost=0.05)
        wf = Workflow("cost-test").step(A)
        wf.events.on(
            Hook.WORKFLOW_STEP_END,
            lambda ctx: costs.append(getattr(ctx, "cost", 0.0)),
        )

        await wf.run("go")

        assert len(costs) == 1
        assert costs[0] == pytest.approx(0.05)


@pytest.mark.phase_1
class TestWorkflowCompletedHook:
    """Hook.WORKFLOW_COMPLETED fires when all steps succeed."""

    async def test_completed_fires_once(self) -> None:
        """WORKFLOW_COMPLETED fires exactly once after run() returns."""
        events: list[EventContext] = []
        A = _make_agent("done")
        wf = Workflow("comp-test").step(A)
        wf.events.on(Hook.WORKFLOW_COMPLETED, lambda ctx: events.append(ctx))

        await wf.run("go")

        assert len(events) == 1

    async def test_completed_has_run_id(self) -> None:
        """WORKFLOW_COMPLETED shares the same run_id as WORKFLOW_STARTED."""
        started_ids: list[str] = []
        completed_ids: list[str] = []
        A = _make_agent("done")
        wf = Workflow("id-match-test").step(A)
        wf.events.on(
            Hook.WORKFLOW_STARTED,
            lambda ctx: started_ids.append(getattr(ctx, "run_id", "")),
        )
        wf.events.on(
            Hook.WORKFLOW_COMPLETED,
            lambda ctx: completed_ids.append(getattr(ctx, "run_id", "")),
        )

        await wf.run("go")

        assert started_ids[0] == completed_ids[0]

    async def test_completed_not_fired_on_failure(self) -> None:
        """WORKFLOW_COMPLETED does not fire when a step fails."""
        completed: list[EventContext] = []
        wf = Workflow("fail-test").step(_make_failing_agent())
        wf.events.on(Hook.WORKFLOW_COMPLETED, lambda ctx: completed.append(ctx))

        with pytest.raises(WorkflowStepError):
            await wf.run("go")

        assert len(completed) == 0


@pytest.mark.phase_1
class TestWorkflowFailedHook:
    """Hook.WORKFLOW_FAILED fires when a step raises an unhandled exception."""

    async def test_failed_fires_on_step_exception(self) -> None:
        """WORKFLOW_FAILED fires when an agent step raises."""
        failed: list[EventContext] = []
        wf = Workflow("fail-hook").step(_make_failing_agent())
        wf.events.on(Hook.WORKFLOW_FAILED, lambda ctx: failed.append(ctx))

        with pytest.raises(WorkflowStepError):
            await wf.run("go")

        assert len(failed) >= 1

    async def test_failed_not_fired_on_success(self) -> None:
        """WORKFLOW_FAILED does not fire on a successful run."""
        failed: list[EventContext] = []
        A = _make_agent("ok")
        wf = Workflow("success-no-fail").step(A)
        wf.events.on(Hook.WORKFLOW_FAILED, lambda ctx: failed.append(ctx))

        await wf.run("go")

        assert len(failed) == 0


@pytest.mark.phase_1
class TestHookRunIdConsistency:
    """All hooks in a single run share the same run_id."""

    async def test_all_hooks_share_run_id(self) -> None:
        """STARTED, STEP_START, STEP_END, and COMPLETED all share the same run_id."""
        run_ids: list[str] = []

        def capture(ctx: EventContext) -> None:
            rid = getattr(ctx, "run_id", None)
            if rid is not None:
                run_ids.append(rid)

        A = _make_agent("a")
        B = _make_agent("b")
        wf = Workflow("shared-id").step(A).step(B)
        wf.events.on(Hook.WORKFLOW_STARTED, capture)
        wf.events.on(Hook.WORKFLOW_STEP_START, capture)
        wf.events.on(Hook.WORKFLOW_STEP_END, capture)
        wf.events.on(Hook.WORKFLOW_COMPLETED, capture)

        await wf.run("go")

        # Should have: 1 STARTED + 2 STEP_START + 2 STEP_END + 1 COMPLETED = 6
        assert len(run_ids) >= 4
        # All run_ids must be the same
        assert len(set(run_ids)) == 1
