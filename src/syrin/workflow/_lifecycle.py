"""RunHandle, PauseMode, and WorkflowStatus — workflow lifecycle primitives.

A :class:`RunHandle` is returned immediately by :meth:`~syrin.workflow.Workflow.play`.
The workflow execution runs in a background ``asyncio.Task``.  Use
``await handle.wait()`` to block until the workflow completes.

:class:`PauseMode` controls *when* a requested pause takes effect:

- :attr:`PauseMode.AFTER_CURRENT_STEP` (default): wait for the current step to
  finish, then pause.
- :attr:`PauseMode.IMMEDIATE`: cancel the current step and pause now.
  **Note**: the in-flight step's output is lost; use with care.
"""

from __future__ import annotations

import asyncio
from typing import Generic, TypeVar

from syrin.enums import PauseMode, WorkflowStatus  # noqa: F401 (re-exported)
from syrin.response import Response
from syrin.workflow.exceptions import WorkflowCancelledError

T = TypeVar("T")


class RunHandle(Generic[T]):
    """Handle to a running (or paused) workflow execution.

    Created by :meth:`~syrin.workflow.Workflow.play`.  The workflow runs in a
    background ``asyncio.Task``; this handle exposes lifecycle controls and
    live state.

    Attributes:
        status: Current :class:`WorkflowStatus`.
        step_index: Index of the last completed step (``-1`` before any step
            finishes).
        budget_spent: Total cost accumulated so far in USD.
        run_id: Unique identifier for this run, matching the ``run_id`` field
            in emitted hooks.

    Example::

        handle = wf.play("Research AI trends")
        print(handle.status)          # WorkflowStatus.RUNNING
        result = await handle.wait()  # blocks until done
        print(result.content)
    """

    def __init__(
        self,
        task: asyncio.Task[Response[T]],
        run_id: str,
        pause_event: asyncio.Event,
        resume_event: asyncio.Event,
        cancel_event: asyncio.Event,
        pause_mode_ref: list[PauseMode],
    ) -> None:
        """Initialise RunHandle.

        Args:
            task: Background asyncio task running the workflow.
            run_id: Unique run identifier.
            pause_event: Event set when a pause is requested.
            resume_event: Event set when resume is requested.
            cancel_event: Event set when cancel is requested.
            pause_mode_ref: Single-element list holding the current
                :class:`PauseMode` (mutable via list so the executor can update
                it without replacing the handle).
        """
        self._task = task
        self._run_id = run_id
        self._pause_event = pause_event
        self._resume_event = resume_event
        self._cancel_event = cancel_event
        self._pause_mode_ref = pause_mode_ref
        self._status: WorkflowStatus = WorkflowStatus.RUNNING
        self._step_index: int = -1
        self._budget_spent: float = 0.0

    # ──────────────────────────────────────────────────────────────────────────
    # Read-only properties
    # ──────────────────────────────────────────────────────────────────────────

    @property
    def status(self) -> WorkflowStatus:
        """Current lifecycle status of this run."""
        return self._status

    @property
    def step_index(self) -> int:
        """Zero-based index of the last completed step.

        Returns ``-1`` before any step has finished.
        """
        return self._step_index

    @property
    def budget_spent(self) -> float:
        """Total cost accumulated so far (in USD)."""
        return self._budget_spent

    @property
    def run_id(self) -> str:
        """Unique identifier for this run."""
        return self._run_id

    # ──────────────────────────────────────────────────────────────────────────
    # Lifecycle controls (used internally by the executor)
    # ──────────────────────────────────────────────────────────────────────────

    def _mark_paused(self) -> None:
        """Mark the run as PAUSED (called by executor after step completes)."""
        self._status = WorkflowStatus.PAUSED

    def _mark_running(self) -> None:
        """Mark the run as RUNNING (called by executor on resume)."""
        self._status = WorkflowStatus.RUNNING

    def _mark_completed(self) -> None:
        """Mark the run as COMPLETED."""
        self._status = WorkflowStatus.COMPLETED

    def _mark_failed(self) -> None:
        """Mark the run as FAILED."""
        self._status = WorkflowStatus.FAILED

    def _mark_cancelled(self) -> None:
        """Mark the run as CANCELLED."""
        self._status = WorkflowStatus.CANCELLED

    def _update_step(self, step_index: int) -> None:
        """Update the last-completed step index.

        Args:
            step_index: New step index.
        """
        self._step_index = step_index

    def _add_cost(self, cost: float) -> None:
        """Accumulate cost.

        Args:
            cost: Cost in USD to add to the running total.
        """
        self._budget_spent += cost

    # ──────────────────────────────────────────────────────────────────────────
    # Public async interface
    # ──────────────────────────────────────────────────────────────────────────

    async def wait(self) -> Response[T]:
        """Await workflow completion and return the final :class:`~syrin.response.Response`.

        Blocks until the workflow reaches COMPLETED, FAILED, or CANCELLED.

        Returns:
            Final response from the last workflow step.

        Raises:
            WorkflowCancelledError: If the workflow was cancelled before
                completing.
            Exception: Re-raises any unhandled step exception.
        """
        result = await self._task
        if self._status == WorkflowStatus.CANCELLED:
            raise WorkflowCancelledError("Workflow was cancelled.")
        return result


__all__ = ["RunHandle"]
