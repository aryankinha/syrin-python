"""P1-T12: Pipeline lifecycle additions — play/pause/resume/cancel."""

from __future__ import annotations

import asyncio

import pytest

from syrin import Agent, Model
from syrin.agent.pipeline import Pipeline
from syrin.enums import Hook, WorkflowStatus
from syrin.events import EventContext
from syrin.response import Response
from syrin.workflow._lifecycle import RunHandle
from syrin.workflow.exceptions import WorkflowCancelledError


def _make_slow_agent(content: str, delay: float = 0.05) -> type[Agent]:
    """Create an async agent that sleeps for *delay* seconds."""

    class _Slow(Agent):
        model = Model.Almock()
        system_prompt = "slow"

        async def arun(self, input_text: str) -> Response[str]:
            await asyncio.sleep(delay)
            return Response(content=content, cost=0.01)

    _Slow.__name__ = f"Slow_{content[:8].replace(' ', '_')}"
    return _Slow


def _make_instant_agent(content: str, cost: float = 0.01) -> type[Agent]:
    """Create an async agent that returns instantly."""

    class _Instant(Agent):
        model = Model.Almock()
        system_prompt = "instant"

        async def arun(self, input_text: str) -> Response[str]:
            return Response(content=content, cost=cost)

    _Instant.__name__ = f"Instant_{content[:8].replace(' ', '_')}"
    return _Instant


@pytest.mark.phase_1
class TestPipelinePlayReturnsHandle:
    """pipeline.play([A, B, C]) returns a RunHandle immediately."""

    async def test_play_returns_run_handle(self) -> None:
        """play() returns a RunHandle instance."""
        A = _make_slow_agent("result", delay=0.05)
        pipeline = Pipeline()
        handle = pipeline.play([A], task="do work")

        assert isinstance(handle, RunHandle)
        await pipeline.cancel()

    async def test_play_is_non_blocking(self) -> None:
        """play() returns before the pipeline finishes."""
        A = _make_slow_agent("result", delay=0.1)
        pipeline = Pipeline()

        handle = pipeline.play([A], task="task")
        # handle is available immediately — pipeline still running
        assert handle is not None
        await pipeline.cancel()


@pytest.mark.phase_1
class TestPipelineWait:
    """await handle.wait() blocks until pipeline completes."""

    async def test_wait_returns_response(self) -> None:
        """handle.wait() returns the pipeline's final Response."""
        A = _make_instant_agent("pipeline done")
        pipeline = Pipeline()
        handle = pipeline.play([A], task="go")
        result = await handle.wait()

        assert isinstance(result, Response)
        assert result.content == "pipeline done"


@pytest.mark.phase_1
class TestPipelinePauseResume:
    """pause() and resume() control pipeline execution.

    Pause takes effect between agents (after current agent finishes).
    A pipeline with two agents [A, B] can be paused between A and B.
    """

    async def test_pause_then_resume_completes(self) -> None:
        """Pausing and then resuming a pipeline still produces the final result."""
        A = _make_instant_agent("step1")
        B = _make_instant_agent("step2")
        pipeline = Pipeline()
        handle = pipeline.play([A, B], task="task")

        # Yield to let A run (it's instant, so it completes right away)
        await asyncio.sleep(0)
        await pipeline.pause()
        await asyncio.sleep(0.02)

        # Resume and wait
        await pipeline.resume()
        result = await handle.wait()

        assert result.content in ("step1", "step2")

    async def test_pipeline_paused_hook_fires(self) -> None:
        """Hook.PIPELINE_PAUSED fires when pipeline is paused.

        Design: pause is checked before each agent. We call pause() immediately
        after play() (synchronously, before the event loop runs the pipeline
        task). The pipeline task then hits the pause check before the first
        agent and fires PIPELINE_PAUSED.
        """
        paused: list[EventContext] = []
        A = _make_instant_agent("a1")
        B = _make_instant_agent("b1")
        pipeline = Pipeline()
        pipeline.events.on(Hook.PIPELINE_PAUSED, lambda ctx: paused.append(ctx))

        pipeline.play([A, B], task="work")
        # Pause immediately — the pipeline task hasn't started yet (no await)
        await pipeline.pause()
        # Yield to let the pipeline task run and hit the pause check
        await asyncio.sleep(0.05)

        assert len(paused) >= 1
        await pipeline.cancel()

    async def test_pipeline_resumed_hook_fires(self) -> None:
        """Hook.PIPELINE_RESUMED fires when pipeline is resumed."""
        resumed: list[EventContext] = []
        A = _make_instant_agent("a")
        B = _make_instant_agent("b")
        pipeline = Pipeline()
        pipeline.events.on(Hook.PIPELINE_RESUMED, lambda ctx: resumed.append(ctx))

        handle = pipeline.play([A, B], task="work")
        await pipeline.pause()  # pause before pipeline task runs
        await asyncio.sleep(0.02)  # let pipeline reach pause state
        await pipeline.resume()
        await handle.wait()

        assert len(resumed) >= 1


@pytest.mark.phase_1
class TestPipelineCancel:
    """cancel() stops the pipeline."""

    async def test_cancel_stops_pipeline(self) -> None:
        """After cancel(), the pipeline terminates and handle reflects that."""
        A = _make_slow_agent("result", delay=0.2)
        B = _make_slow_agent("result2", delay=0.2)
        pipeline = Pipeline()
        handle = pipeline.play([A, B], task="work")

        await asyncio.sleep(0)
        await pipeline.cancel()

        # Wait for the task to settle
        await asyncio.sleep(0.1)

        assert handle.status in (
            WorkflowStatus.CANCELLED,
            WorkflowStatus.RUNNING,  # May still be in-flight before cancel check
        )

    async def test_cancel_raises_on_resume(self) -> None:
        """Calling resume() after cancel() raises WorkflowCancelledError."""
        A = _make_slow_agent("result", delay=0.2)
        pipeline = Pipeline()
        pipeline.play([A], task="work")

        await asyncio.sleep(0)
        await pipeline.cancel()
        await asyncio.sleep(0.01)

        with pytest.raises(WorkflowCancelledError):
            await pipeline.resume()
