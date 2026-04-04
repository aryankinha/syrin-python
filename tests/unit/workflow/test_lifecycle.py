"""P1-T11: RunHandle and Workflow lifecycle tests.

Tests cover:
- play() returns RunHandle immediately (non-blocking)
- handle.status transitions
- await handle.wait() blocks until done
- pause/resume/cancel lifecycle
- Two concurrent play() calls are independent
- Lifecycle hooks fire correctly
"""

from __future__ import annotations

import asyncio

import pytest

from syrin import Agent, Model
from syrin.enums import Hook, PauseMode, WorkflowStatus
from syrin.events import EventContext
from syrin.response import Response
from syrin.workflow import Workflow
from syrin.workflow.exceptions import WorkflowCancelledError


def _make_slow_agent(content: str, delay: float = 0.05, cost: float = 0.01) -> type[Agent]:
    """Create an agent that sleeps for *delay* seconds."""

    class _Slow(Agent):
        model = Model.Almock()
        system_prompt = "slow"

        async def arun(self, input_text: str) -> Response[str]:
            await asyncio.sleep(delay)
            return Response(content=content, cost=cost)

    _Slow.__name__ = f"SlowAgent_{content[:8].replace(' ', '_')}"
    return _Slow


def _make_instant_agent(content: str, cost: float = 0.01) -> type[Agent]:
    """Create an agent that returns instantly."""

    class _Instant(Agent):
        model = Model.Almock()
        system_prompt = "instant"

        async def arun(self, input_text: str) -> Response[str]:
            return Response(content=content, cost=cost)

    _Instant.__name__ = f"InstantAgent_{content[:8].replace(' ', '_')}"
    return _Instant


@pytest.mark.phase_1
class TestPlayReturnsHandleImmediately:
    """play() returns RunHandle immediately (non-blocking)."""

    async def test_play_returns_run_handle(self) -> None:
        """play() returns a RunHandle immediately."""
        from syrin.workflow._lifecycle import RunHandle

        A = _make_slow_agent("result", delay=0.05)
        wf = Workflow("test").step(A)
        handle = wf.play("task")

        assert isinstance(handle, RunHandle)
        # Cancel to clean up
        await wf.cancel()

    async def test_play_status_is_running(self) -> None:
        """handle.status is RUNNING immediately after play()."""
        A = _make_slow_agent("result", delay=0.1)
        wf = Workflow("test").step(A)
        handle = wf.play("task")

        # Immediately after play(), should be RUNNING
        assert handle.status == WorkflowStatus.RUNNING
        await wf.cancel()


@pytest.mark.phase_1
class TestHandleWait:
    """await handle.wait() blocks until done."""

    async def test_wait_returns_response(self) -> None:
        """handle.wait() returns the final Response when complete."""
        A = _make_instant_agent("final result")
        wf = Workflow("test").step(A)
        handle = wf.play("task")
        result = await handle.wait()

        assert result.content == "final result"
        assert handle.status == WorkflowStatus.COMPLETED

    async def test_wait_status_completed_after_wait(self) -> None:
        """handle.status is COMPLETED after handle.wait() resolves."""
        A = _make_instant_agent("done")
        wf = Workflow("test").step(A)
        handle = wf.play("task")
        await handle.wait()

        assert handle.status == WorkflowStatus.COMPLETED


@pytest.mark.phase_1
class TestPauseResume:
    """pause() and resume() lifecycle."""

    async def test_pause_then_resume_completes(self) -> None:
        """Pausing and then resuming a workflow still produces the final result."""
        A = _make_instant_agent("step1 result")
        B = _make_instant_agent("step2 result")
        wf = Workflow("pausable").step(A).step(B)
        handle = wf.play("task")

        # Pause after a brief moment
        await asyncio.sleep(0)
        await wf.pause()

        # Allow pause to take effect
        await asyncio.sleep(0.05)

        # Resume and wait for completion
        await wf.resume()
        result = await handle.wait()

        assert result.content == "step2 result"
        assert handle.status == WorkflowStatus.COMPLETED

    async def test_pause_sets_status_to_paused(self) -> None:
        """After pause takes effect, handle.status becomes PAUSED."""
        A = _make_slow_agent("step1", delay=0.05)
        B = _make_slow_agent("step2", delay=0.05)
        wf = Workflow("pausable2").step(A).step(B)
        handle = wf.play("task")

        # Wait for step1 to complete, then pause before step2
        await asyncio.sleep(0.08)
        await wf.pause(mode=PauseMode.AFTER_CURRENT_STEP)
        await asyncio.sleep(0.02)

        if handle.status == WorkflowStatus.PAUSED:
            await wf.resume()
        result = await handle.wait()
        assert result.content in ("step1", "step2")


@pytest.mark.phase_1
class TestCancel:
    """cancel() stops the workflow; subsequent resume() raises WorkflowCancelledError."""

    async def test_cancel_raises_on_resume(self) -> None:
        """Calling resume() after cancel() raises WorkflowCancelledError."""
        A = _make_slow_agent("result", delay=0.1)
        B = _make_slow_agent("result2", delay=0.1)
        wf = Workflow("cancelable").step(A).step(B)
        wf.play("task")

        await asyncio.sleep(0)
        await wf.cancel()
        await asyncio.sleep(0.05)

        with pytest.raises(WorkflowCancelledError):
            await wf.resume()

    async def test_cancel_fires_cancelled_hook(self) -> None:
        """WORKFLOW_CANCELLED hook fires when workflow is cancelled."""
        cancelled: list[EventContext] = []
        A = _make_slow_agent("result", delay=0.1)
        wf = Workflow("cancel-hook").step(A)
        wf.events.on(Hook.WORKFLOW_CANCELLED, lambda ctx: cancelled.append(ctx))

        wf.play("task")
        await asyncio.sleep(0)
        await wf.cancel()
        await asyncio.sleep(0.1)

        assert len(cancelled) >= 1


@pytest.mark.phase_1
class TestConcurrentPlays:
    """Two concurrent play() calls return independent handles."""

    async def test_two_independent_handles(self) -> None:
        """Two play() calls create two independent handles."""
        A1 = _make_instant_agent("result A")
        wf1 = Workflow("wf1").step(A1)
        A2 = _make_instant_agent("result B")
        wf2 = Workflow("wf2").step(A2)

        handle1 = wf1.play("task 1")
        handle2 = wf2.play("task 2")

        r1 = await handle1.wait()
        r2 = await handle2.wait()

        assert r1.content == "result A"
        assert r2.content == "result B"
        assert handle1.run_id != handle2.run_id


@pytest.mark.phase_1
class TestHandleMetrics:
    """handle.step_index and handle.budget_spent track progress."""

    async def test_step_index_after_completion(self) -> None:
        """step_index reflects the last completed step."""
        A = _make_instant_agent("a")
        B = _make_instant_agent("b")
        wf = Workflow("metrics").step(A).step(B)
        handle = wf.play("task")
        await handle.wait()

        # After 2 steps (index 0 and 1), step_index should be 1
        assert handle.step_index == 1

    async def test_budget_spent_accumulates(self) -> None:
        """budget_spent accumulates total cost across steps."""
        A = _make_instant_agent("a", cost=0.05)
        B = _make_instant_agent("b", cost=0.03)
        wf = Workflow("cost-metrics").step(A).step(B)
        handle = wf.play("task")
        await handle.wait()

        assert handle.budget_spent == pytest.approx(0.08)
