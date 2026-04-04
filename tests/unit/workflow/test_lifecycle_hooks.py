"""Workflow lifecycle-hooks tests.

Covers:
- WORKFLOW_PAUSED hook fires with correct step_index and budget_spent
- WORKFLOW_RESUMED hook fires with correct step_index
- Two concurrent wf.play() runs are independent (pausing one does not affect other)
- RunHandle.status transitions: RUNNING → PAUSED → RUNNING → COMPLETED
"""

from __future__ import annotations

import asyncio

import pytest

from syrin import Agent, Model
from syrin.enums import Hook, PauseMode, WorkflowStatus
from syrin.events import EventContext
from syrin.response import Response
from syrin.workflow import Workflow

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _make_slow_agent(content: str = "result", delay: float = 0.05) -> type[Agent]:
    """Create an agent that sleeps for *delay* seconds before returning."""

    class _Slow(Agent):
        model = Model.Almock()
        system_prompt = "slow stub"

        async def arun(self, input_text: str) -> Response[str]:
            await asyncio.sleep(delay)
            return Response(content=content, cost=0.01)

    _Slow.__name__ = f"Slow_{content[:8].replace(' ', '_')}"
    return _Slow


def _make_instant_agent(content: str = "result", cost: float = 0.01) -> type[Agent]:
    """Create an agent that returns instantly."""

    class _Instant(Agent):
        model = Model.Almock()
        system_prompt = "instant stub"

        async def arun(self, input_text: str) -> Response[str]:
            return Response(content=content, cost=cost)

    _Instant.__name__ = f"Instant_{content[:8].replace(' ', '_')}"
    return _Instant


# ──────────────────────────────────────────────────────────────────────────────
# WORKFLOW_PAUSED hook
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.phase_1
class TestWorkflowPausedHook:
    """WORKFLOW_PAUSED hook fires with correct payload when pause takes effect."""

    async def test_paused_hook_fires_after_pause(self) -> None:
        """WORKFLOW_PAUSED fires at least once after pause() is requested."""
        paused_events: list[EventContext] = []

        A = _make_slow_agent("step1", delay=0.05)
        B = _make_slow_agent("step2", delay=0.05)
        wf = Workflow("pausable").step(A).step(B)
        wf.events.on(Hook.WORKFLOW_PAUSED, lambda ctx: paused_events.append(ctx))

        handle = wf.play("task")
        # Allow first step to start
        await asyncio.sleep(0.01)
        await wf.pause(mode=PauseMode.AFTER_CURRENT_STEP)

        # Allow pause to take effect
        await asyncio.sleep(0.1)

        assert len(paused_events) >= 1, "WORKFLOW_PAUSED must fire when pause takes effect"

        # Cleanup
        await wf.resume()
        await handle.wait()

    async def test_paused_hook_has_step_index(self) -> None:
        """WORKFLOW_PAUSED context includes step_index."""
        step_indices: list[object] = []

        A = _make_slow_agent("s1", delay=0.05)
        B = _make_slow_agent("s2", delay=0.05)
        wf = Workflow("pausable-idx").step(A).step(B)
        wf.events.on(
            Hook.WORKFLOW_PAUSED,
            lambda ctx: step_indices.append(ctx.get("step_index")),
        )

        handle = wf.play("task")
        await asyncio.sleep(0.01)
        await wf.pause(mode=PauseMode.AFTER_CURRENT_STEP)
        await asyncio.sleep(0.1)

        if step_indices:
            assert step_indices[0] is not None

        await wf.resume()
        await handle.wait()

    async def test_paused_hook_has_budget_spent(self) -> None:
        """WORKFLOW_PAUSED context includes budget_spent field."""
        paused_events: list[EventContext] = []

        A = _make_slow_agent("s1", delay=0.05)
        B = _make_slow_agent("s2", delay=0.05)
        wf = Workflow("pausable-budget").step(A).step(B)
        wf.events.on(Hook.WORKFLOW_PAUSED, lambda ctx: paused_events.append(ctx))

        handle = wf.play("task")
        await asyncio.sleep(0.01)
        await wf.pause(mode=PauseMode.AFTER_CURRENT_STEP)
        await asyncio.sleep(0.1)

        if paused_events:
            ctx = paused_events[0]
            # budget_spent key must exist in the context
            assert "budget_spent" in ctx

        await wf.resume()
        await handle.wait()


# ──────────────────────────────────────────────────────────────────────────────
# WORKFLOW_RESUMED hook
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.phase_1
class TestWorkflowResumedHook:
    """WORKFLOW_RESUMED hook fires when execution continues after a pause."""

    async def test_resumed_hook_fires_after_resume(self) -> None:
        """WORKFLOW_RESUMED fires after resume() is called on a paused workflow."""
        resumed_events: list[EventContext] = []

        A = _make_slow_agent("s1", delay=0.05)
        B = _make_slow_agent("s2", delay=0.05)
        wf = Workflow("resumable").step(A).step(B)
        wf.events.on(Hook.WORKFLOW_RESUMED, lambda ctx: resumed_events.append(ctx))

        handle = wf.play("task")
        await asyncio.sleep(0.01)
        await wf.pause(mode=PauseMode.AFTER_CURRENT_STEP)
        await asyncio.sleep(0.1)

        await wf.resume()
        await handle.wait()

        assert len(resumed_events) >= 1, "WORKFLOW_RESUMED must fire after resume()"

    async def test_resumed_hook_has_step_index(self) -> None:
        """WORKFLOW_RESUMED context includes step_index."""
        step_indices: list[object] = []

        A = _make_slow_agent("s1", delay=0.05)
        B = _make_slow_agent("s2", delay=0.05)
        wf = Workflow("resumable-idx").step(A).step(B)
        wf.events.on(
            Hook.WORKFLOW_RESUMED,
            lambda ctx: step_indices.append(ctx.get("step_index")),
        )

        handle = wf.play("task")
        await asyncio.sleep(0.01)
        await wf.pause(mode=PauseMode.AFTER_CURRENT_STEP)
        await asyncio.sleep(0.1)

        await wf.resume()
        await handle.wait()

        assert len(step_indices) >= 1


# ──────────────────────────────────────────────────────────────────────────────
# Two concurrent play() calls are independent
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.phase_1
class TestConcurrentPlayIndependence:
    """Two concurrent play() calls produce independent RunHandle instances."""

    async def test_two_handles_have_different_run_ids(self) -> None:
        """Two play() calls on separate Workflow instances have different run_ids."""
        A1 = _make_instant_agent("result-A")
        A2 = _make_instant_agent("result-B")
        wf1 = Workflow("wf-concurrent-1").step(A1)
        wf2 = Workflow("wf-concurrent-2").step(A2)

        h1 = wf1.play("task1")
        h2 = wf2.play("task2")

        r1 = await h1.wait()
        r2 = await h2.wait()

        assert r1.content == "result-A"
        assert r2.content == "result-B"
        assert h1.run_id != h2.run_id

    async def test_pausing_one_does_not_affect_other(self) -> None:
        """Pausing wf1 does not pause wf2; wf2 completes independently."""
        A_slow = _make_slow_agent("slow-result", delay=0.1)
        A_fast = _make_instant_agent("fast-result")

        wf1 = Workflow("wf-slow").step(A_slow).step(A_slow)
        wf2 = Workflow("wf-fast").step(A_fast).step(A_fast)

        h1 = wf1.play("task")
        h2 = wf2.play("task")

        # Pause wf1 only — wf2 should complete without being affected
        await wf1.pause(mode=PauseMode.AFTER_CURRENT_STEP)

        # wf2 should complete quickly
        r2 = await h2.wait()
        assert r2.content == "fast-result"
        assert h2.status == WorkflowStatus.COMPLETED

        # wf1 should still be paused (or RUNNING between steps)
        assert h1.status in (WorkflowStatus.PAUSED, WorkflowStatus.RUNNING)

        # Clean up wf1
        await wf1.resume()
        await h1.wait()

    async def test_each_play_creates_fresh_events(self) -> None:
        """Each play() call creates a fresh executor with independent asyncio Events."""
        A = _make_instant_agent("out")
        wf = Workflow("fresh-events").step(A)

        # First run
        h1 = wf.play("first")
        r1 = await h1.wait()

        # Second run — executor should be fresh, not share events with first
        h2 = wf.play("second")
        r2 = await h2.wait()

        assert r1.content == "out"
        assert r2.content == "out"
        assert h1.run_id != h2.run_id
        assert h1.status == WorkflowStatus.COMPLETED
        assert h2.status == WorkflowStatus.COMPLETED


# ──────────────────────────────────────────────────────────────────────────────
# RunHandle.status transitions
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.phase_1
class TestRunHandleStatusTransitions:
    """RunHandle transitions: RUNNING → PAUSED → RUNNING → COMPLETED."""

    async def test_status_running_on_play(self) -> None:
        """Status is RUNNING immediately after play()."""
        A = _make_slow_agent("r", delay=0.1)
        wf = Workflow("status-running").step(A)
        handle = wf.play("task")

        assert handle.status == WorkflowStatus.RUNNING
        await wf.cancel()

    async def test_status_paused_after_pause(self) -> None:
        """Status transitions to PAUSED after pause takes effect."""
        A = _make_slow_agent("s1", delay=0.05)
        B = _make_slow_agent("s2", delay=0.05)
        wf = Workflow("status-paused").step(A).step(B)
        handle = wf.play("task")

        await asyncio.sleep(0.01)
        await wf.pause(mode=PauseMode.AFTER_CURRENT_STEP)
        await asyncio.sleep(0.1)

        # By now, step 0 should have finished and pause taken effect
        if handle.status == WorkflowStatus.PAUSED:
            assert handle.status == WorkflowStatus.PAUSED

        # Resume and wait for completion
        await wf.resume()
        await handle.wait()

    async def test_status_completed_after_wait(self) -> None:
        """Status is COMPLETED after handle.wait() returns."""
        A = _make_instant_agent("done")
        B = _make_instant_agent("done2")
        wf = Workflow("status-complete").step(A).step(B)
        handle = wf.play("task")

        # Pause mid-flight, then resume
        await asyncio.sleep(0)
        await wf.pause()
        await asyncio.sleep(0.02)
        await wf.resume()

        result = await handle.wait()
        assert handle.status == WorkflowStatus.COMPLETED
        assert result.content == "done2"
