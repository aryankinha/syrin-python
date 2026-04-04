"""Phase 1 integration test — Workflow standalone (LLM mocked at Agent boundary).

This test verifies that a complete Workflow runs end-to-end with:
- All four step types exercised
- Lifecycle controls (play/pause/resume/cancel)
- Nested sub-workflow
- Budget tracking
- Hooks firing in the correct order
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from syrin import Agent, Model
from syrin.enums import Hook, WorkflowStatus
from syrin.events import EventContext
from syrin.response import Response
from syrin.workflow import Workflow
from syrin.workflow.exceptions import (
    DynamicFanoutError,
    WorkflowCancelledError,
    WorkflowNotRunnable,
)

# ──────────────────────────────────────────────────────────────────────────────
# Mock agents (LLM boundary mocked via Model.Almock())
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class SearchResults:
    """Structured output from a search agent."""

    sources: list[str]
    summary: str


class PlannerAgent(Agent):
    """Creates a research plan."""

    model = Model.Almock()
    system_prompt = "planner"

    async def arun(self, input_text: str) -> Response[str]:
        """Return a research plan."""
        return Response(content="Plan: research 3 sources", cost=0.05)


class RedditAgent(Agent):
    """Searches Reddit."""

    model = Model.Almock()
    system_prompt = "reddit"

    async def arun(self, input_text: str) -> Response[str]:
        """Return Reddit findings."""
        return Response(content="Reddit: found 5 threads", cost=0.02)


class HNAgent(Agent):
    """Searches Hacker News."""

    model = Model.Almock()
    system_prompt = "hn"

    async def arun(self, input_text: str) -> Response[str]:
        """Return HN findings."""
        return Response(content="HN: found 3 stories", cost=0.02)


class SummarizerAgent(Agent):
    """Summarizes research findings."""

    model = Model.Almock()
    system_prompt = "summarizer"

    async def arun(self, input_text: str) -> Response[str]:
        """Return a summary."""
        return Response(content="Summary: comprehensive analysis complete", cost=0.08)


class FastAgent(Agent):
    """Fast execution path."""

    model = Model.Almock()
    system_prompt = "fast"

    async def arun(self, input_text: str) -> Response[str]:
        """Return fast result."""
        return Response(content="fast path taken", cost=0.01)


class ThoroughAgent(Agent):
    """Thorough execution path."""

    model = Model.Almock()
    system_prompt = "thorough"

    async def arun(self, input_text: str) -> Response[str]:
        """Return thorough result."""
        return Response(content="thorough path taken", cost=0.10)


class SlowAgent(Agent):
    """Agent that takes time to simulate real work."""

    model = Model.Almock()
    system_prompt = "slow"

    async def arun(self, input_text: str) -> Response[str]:
        """Simulate slow work."""
        await asyncio.sleep(0.05)
        return Response(content="slow result", cost=0.03)


# ──────────────────────────────────────────────────────────────────────────────
# Integration tests
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.phase_1
class TestSequentialWorkflowIntegration:
    """End-to-end sequential workflow."""

    async def test_two_step_pipeline(self) -> None:
        """A sequential two-step workflow produces the second step's output."""
        wf = Workflow("seq-integration").step(PlannerAgent).step(SummarizerAgent)
        result = await wf.run("Research AI trends")

        assert result.content == "Summary: comprehensive analysis complete"
        # result.cost reflects the last step's cost (Response is from last agent)
        assert result.cost == pytest.approx(0.08)

    async def test_workflow_passes_content_between_steps(self) -> None:
        """Step 2 receives step 1's output as input."""
        received: list[str] = []

        class CaptureAgent(Agent):
            model = Model.Almock()
            system_prompt = "capture"

            async def arun(self, input_text: str) -> Response[str]:
                received.append(input_text)
                return Response(content="captured", cost=0.01)

        wf = Workflow("passthrough").step(PlannerAgent).step(CaptureAgent)
        await wf.run("start")

        assert "Plan: research 3 sources" in received[0]


@pytest.mark.phase_1
class TestParallelWorkflowIntegration:
    """End-to-end parallel workflow."""

    async def test_parallel_merges_outputs(self) -> None:
        """Parallel agents produce merged content in the result."""
        wf = Workflow("par-integration").parallel([RedditAgent, HNAgent])
        result = await wf.run("Research AI")

        assert "Reddit" in result.content
        assert "HN" in result.content

    async def test_parallel_runs_faster_than_sequential(self) -> None:
        """Parallel agents run concurrently (total time < sum of individual times)."""
        import time

        wf = Workflow("timing-test").parallel([SlowAgent, SlowAgent])
        start = time.monotonic()
        await wf.run("task")
        elapsed = time.monotonic() - start

        # Two 50ms agents in parallel should take <90ms, not ~100ms
        assert elapsed < 0.09, f"Parallel took {elapsed:.3f}s, expected <0.09s"


@pytest.mark.phase_1
class TestBranchWorkflowIntegration:
    """End-to-end branch workflow."""

    async def test_branch_routes_correctly(self) -> None:
        """Branch selects the correct path based on context."""
        # Condition: content has "urgent" → fast path
        wf = (
            Workflow("branch-integration")
            .step(PlannerAgent)  # outputs "Plan: research 3 sources"
            .branch(
                condition=lambda ctx: "urgent" in ctx.content,
                if_true=FastAgent,
                if_false=ThoroughAgent,
            )
        )
        # "Plan: research 3 sources" does NOT contain "urgent" → thorough path
        result = await wf.run("start")
        assert result.content == "thorough path taken"


@pytest.mark.phase_1
class TestDynamicWorkflowIntegration:
    """End-to-end dynamic workflow."""

    async def test_dynamic_spawns_multiple_agents(self) -> None:
        """Dynamic step spawns N agents based on factory result."""
        wf = Workflow("dyn-integration").dynamic(
            fn=lambda _ctx: [
                (RedditAgent, "search reddit", 1.00),
                (HNAgent, "search hn", 1.00),
            ],
        )
        result = await wf.run("Research task")

        assert "Reddit" in result.content
        assert "HN" in result.content

    async def test_dynamic_empty_raises(self) -> None:
        """Dynamic factory returning empty list raises DynamicFanoutError."""
        wf = Workflow("dyn-empty").dynamic(fn=lambda _ctx: [])
        with pytest.raises(DynamicFanoutError):
            await wf.run("task")


@pytest.mark.phase_1
class TestNestedWorkflowIntegration:
    """Nested sub-workflow integration."""

    async def test_sub_workflow_as_step(self) -> None:
        """Sub-workflow produces output that feeds into parent's next step."""
        received: list[str] = []

        class Collector(Agent):
            model = Model.Almock()
            system_prompt = "collect"

            async def arun(self, input_text: str) -> Response[str]:
                received.append(input_text)
                return Response(content="collected", cost=0.01)

        sub_wf = Workflow("sub").step(PlannerAgent)
        parent_wf = Workflow("parent").step(sub_wf).step(Collector)
        result = await parent_wf.run("start")

        assert result.content == "collected"
        assert "Plan: research 3 sources" in received[0]

    async def test_three_level_nesting(self) -> None:
        """Three levels of workflow nesting all produce results."""
        level3 = Workflow("l3").step(SummarizerAgent)
        level2 = Workflow("l2").step(level3)
        level1 = Workflow("l1").step(level2)

        result = await level1.run("task")
        assert result.content == "Summary: comprehensive analysis complete"


@pytest.mark.phase_1
class TestLifecycleIntegration:
    """Lifecycle (play/pause/resume/cancel) integration."""

    async def test_play_wait_completes(self) -> None:
        """play() + wait() produces the final result."""
        wf = Workflow("play-int").step(PlannerAgent)
        handle = wf.play("task")
        result = await handle.wait()

        assert result.content == "Plan: research 3 sources"
        assert handle.status == WorkflowStatus.COMPLETED

    async def test_cancel_fires_hook(self) -> None:
        """cancel() fires WORKFLOW_CANCELLED hook."""
        cancelled: list[EventContext] = []
        wf = Workflow("cancel-int").step(SlowAgent)
        wf.events.on(Hook.WORKFLOW_CANCELLED, lambda ctx: cancelled.append(ctx))

        wf.play("task")
        await asyncio.sleep(0)
        await wf.cancel()
        await asyncio.sleep(0.1)

        assert len(cancelled) >= 1

    async def test_pause_resume_completes(self) -> None:
        """Pause then resume still completes the workflow."""
        wf = Workflow("pause-int").step(PlannerAgent).step(SummarizerAgent)
        handle = wf.play("task")

        await wf.pause()
        await asyncio.sleep(0.05)
        await wf.resume()
        result = await handle.wait()

        assert result.content == "Summary: comprehensive analysis complete"
        assert handle.status == WorkflowStatus.COMPLETED


@pytest.mark.phase_1
class TestHooksIntegration:
    """Lifecycle hooks fire in the correct order."""

    async def test_hooks_fire_in_order(self) -> None:
        """STARTED → STEP_START×N → STEP_END×N → COMPLETED fires in order."""
        hook_order: list[str] = []

        wf = Workflow("hooks-order").step(PlannerAgent).step(SummarizerAgent)
        wf.events.on(Hook.WORKFLOW_STARTED, lambda _ctx: hook_order.append("STARTED"))
        wf.events.on(Hook.WORKFLOW_STEP_START, lambda _ctx: hook_order.append("STEP_START"))
        wf.events.on(Hook.WORKFLOW_STEP_END, lambda _ctx: hook_order.append("STEP_END"))
        wf.events.on(Hook.WORKFLOW_COMPLETED, lambda _ctx: hook_order.append("COMPLETED"))

        await wf.run("task")

        assert hook_order[0] == "STARTED"
        assert hook_order[-1] == "COMPLETED"
        assert hook_order.count("STEP_START") == 2
        assert hook_order.count("STEP_END") == 2

    async def test_budget_tracking_across_steps(self) -> None:
        """handle.budget_spent accumulates cost from all steps."""
        wf = Workflow("budget-int").step(PlannerAgent).step(SummarizerAgent)
        handle = wf.play("task")
        await handle.wait()

        # PlannerAgent: 0.05 + SummarizerAgent: 0.08 = 0.13
        assert handle.budget_spent == pytest.approx(0.13)


@pytest.mark.phase_1
class TestWorkflowRunnableIntegration:
    """Error handling for invalid workflow states."""

    async def test_empty_workflow_raises(self) -> None:
        """Empty workflow raises WorkflowNotRunnable."""
        wf = Workflow("empty-int")
        with pytest.raises(WorkflowNotRunnable):
            await wf.run("task")

    async def test_cancel_then_resume_raises(self) -> None:
        """Resuming a cancelled workflow raises WorkflowCancelledError."""
        wf = Workflow("cancel-resume-int").step(SlowAgent)
        wf.play("task")

        await asyncio.sleep(0)
        await wf.cancel()
        await asyncio.sleep(0.05)

        with pytest.raises(WorkflowCancelledError):
            await wf.resume()


@pytest.mark.phase_1
class TestVisualizationIntegration:
    """Visualization methods work without error on real workflows."""

    def test_to_mermaid_on_complex_workflow(self) -> None:
        """to_mermaid() returns valid Mermaid for a multi-step workflow."""
        wf = (
            Workflow("viz-int")
            .step(PlannerAgent)
            .parallel([RedditAgent, HNAgent])
            .branch(condition=lambda _ctx: True, if_true=FastAgent, if_false=ThoroughAgent)
            .step(SummarizerAgent)
        )
        mermaid = wf.to_mermaid()
        assert mermaid.startswith("graph ")
        assert "PlannerAgent" in mermaid

    def test_to_dict_on_complex_workflow(self) -> None:
        """to_dict() returns a dict with nodes and edges for all step types."""
        wf = (
            Workflow("dict-int")
            .step(PlannerAgent)
            .parallel([RedditAgent, HNAgent])
            .branch(condition=lambda _ctx: True, if_true=FastAgent, if_false=ThoroughAgent)
            .dynamic(fn=lambda _ctx: [])
        )
        result = wf.to_dict()
        assert "nodes" in result
        assert "edges" in result
        assert len(result["nodes"]) >= 4
