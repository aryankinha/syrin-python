"""WorkflowExecutor — the async engine that runs a Workflow step graph.

The executor is an internal implementation detail.  Users interact with it
only through :meth:`~syrin.workflow._core.Workflow.run` and
:meth:`~syrin.workflow._core.Workflow.play`.

Design notes:

- The executor walks the step list sequentially.  Parallel and dynamic steps
  use ``asyncio.gather`` internally.
- Pause/resume uses ``asyncio.Event`` — the executor checks for a pending pause
  *between* steps (after the current step finishes but before the next starts).
- The executor never mutates step objects; it only reads them.
- Every LLM call happens at ``agent.arun()`` — the executor is always async.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import TYPE_CHECKING, TypeVar

from syrin.agent._core import Agent
from syrin.budget import Budget
from syrin.budget._forecast import BudgetForecaster
from syrin.enums import Hook, PauseMode, WorkflowStatus
from syrin.events import EventContext, Events
from syrin.exceptions import ForecastAbortError
from syrin.response import Response
from syrin.workflow._budget import resolve_budget
from syrin.workflow._context import HandoffContext
from syrin.workflow._lifecycle import RunHandle
from syrin.workflow._step import (
    BranchStep,
    DynamicStep,
    ParallelStep,
    SequentialStep,
    WorkflowStep,
)
from syrin.workflow.exceptions import (
    DynamicFanoutError,
    WorkflowCancelledError,
    WorkflowStepError,
)

if TYPE_CHECKING:
    from syrin.checkpoint._core import CheckpointBackendProtocol
    from syrin.swarm._registry import SwarmContext

_log = logging.getLogger(__name__)

T = TypeVar("T")


class WorkflowExecutor:
    """Runs a workflow step sequence and manages the pause/resume lifecycle.

    One :class:`WorkflowExecutor` instance is created per ``play()`` / ``run()``
    call.  It is **not** reusable across runs.

    Attributes:
        run_id: Unique identifier for this execution.
        handle: The :class:`~syrin.workflow._lifecycle.RunHandle` exposed to
            the caller.
    """

    def __init__(
        self,
        steps: list[WorkflowStep],
        workflow_name: str,
        budget: Budget | None,
        events: Events,
        checkpoint_backend: CheckpointBackendProtocol | None = None,
        run_id: str | None = None,
        swarm_context: SwarmContext | None = None,
    ) -> None:
        """Initialise the executor.

        Args:
            steps: Ordered list of workflow steps.
            workflow_name: Human-readable workflow name (for hooks and context).
            budget: Workflow-level budget, or ``None`` for unlimited.
            events: :class:`~syrin.events.Events` instance for hook emission.
            checkpoint_backend: Optional checkpoint backend for persistent step
                state.  When provided, workflow step progress is saved after
                each step and can be resumed across processes.
            run_id: Optional run ID to resume.  When provided together with
                *checkpoint_backend*, the executor attempts to load the last
                saved checkpoint for this run and resumes from that step.
            swarm_context: Optional :class:`~syrin.swarm._registry.SwarmContext`
                injected when the workflow runs inside a Swarm (WORKFLOW topology).
                Gives agents access to the shared pool, MemoryBus, and A2A.
        """
        self._steps = steps
        self._workflow_name = workflow_name
        self._budget = budget
        self._events = events
        self._checkpoint_backend: CheckpointBackendProtocol | None = checkpoint_backend
        self._swarm_context: SwarmContext | None = swarm_context

        self.run_id: str = run_id or f"run-{uuid.uuid4().hex[:12]}"
        self._pause_event = asyncio.Event()
        self._resume_event = asyncio.Event()
        self._cancel_event = asyncio.Event()
        self._pause_mode_ref: list[PauseMode] = [PauseMode.AFTER_CURRENT_STEP]

        self.handle: RunHandle[str] | None = None

    # ──────────────────────────────────────────────────────────────────────────
    # Public entry points
    # ──────────────────────────────────────────────────────────────────────────

    async def run(self, input_text: str) -> Response[str]:
        """Execute the workflow and return the final :class:`~syrin.response.Response`.

        Args:
            input_text: Initial task string passed to the first step.

        Returns:
            Response from the last step.
        """
        return await self._execute(input_text)

    def play(self, input_text: str) -> RunHandle[str]:
        """Start the workflow in a background task and return a :class:`~syrin.workflow._lifecycle.RunHandle`.

        Args:
            input_text: Initial task string passed to the first step.

        Returns:
            A :class:`~syrin.workflow._lifecycle.RunHandle` for lifecycle control.
        """
        task: asyncio.Task[Response[str]] = asyncio.get_event_loop().create_task(
            self._execute(input_text)
        )
        handle: RunHandle[str] = RunHandle(
            task=task,
            run_id=self.run_id,
            pause_event=self._pause_event,
            resume_event=self._resume_event,
            cancel_event=self._cancel_event,
            pause_mode_ref=self._pause_mode_ref,
        )
        self.handle = handle

        def _on_done(fut: asyncio.Future[Response[str]]) -> None:
            exc = fut.exception()
            if exc is not None:
                if isinstance(exc, WorkflowCancelledError):
                    handle._mark_cancelled()
                else:
                    handle._mark_failed()
            else:
                if handle.status != WorkflowStatus.CANCELLED:
                    handle._mark_completed()

        task.add_done_callback(_on_done)
        return handle

    async def request_pause(self, mode: PauseMode = PauseMode.AFTER_CURRENT_STEP) -> None:
        """Signal the executor to pause.

        Args:
            mode: When the pause should take effect.
        """
        self._pause_mode_ref[0] = mode
        self._pause_event.set()

    async def request_resume(self) -> None:
        """Signal the executor to resume from a paused state."""
        self._pause_event.clear()
        self._resume_event.set()

    async def request_cancel(self) -> None:
        """Signal the executor to cancel and stop execution."""
        self._cancel_event.set()
        self._pause_event.clear()
        self._resume_event.set()  # unblock any pending wait

    # ──────────────────────────────────────────────────────────────────────────
    # Core execution loop
    # ──────────────────────────────────────────────────────────────────────────

    async def _execute(self, input_text: str) -> Response[str]:
        """Main execution loop.

        Args:
            input_text: Initial task string.

        Returns:
            Final :class:`~syrin.response.Response`.
        """
        budget_remaining = (
            self._budget.max_cost if (self._budget and self._budget.max_cost) else 0.0
        )

        # Load checkpoint if backend and a saved checkpoint exist for this run
        resume_from_step: int = 0
        total_cost: float = 0.0
        ctx: HandoffContext[object] = HandoffContext(
            content=input_text,
            history=(),
            budget_remaining=budget_remaining,
            step_index=0,
            workflow_name=self._workflow_name,
            run_id=self.run_id,
        )
        if self._checkpoint_backend is not None:
            _ckpt = self._checkpoint_backend.load(f"{self.run_id}:latest")
            if _ckpt is not None and _ckpt.metadata:
                _meta = _ckpt.metadata
                _step_index_raw = _meta.get("step_index", 0)
                resume_from_step = (
                    int(_step_index_raw) if isinstance(_step_index_raw, (int, float)) else 0
                ) + 1
                _total_cost_raw = _meta.get("total_cost", 0.0)
                total_cost = (
                    float(_total_cost_raw) if isinstance(_total_cost_raw, (int, float)) else 0.0
                )
                _budget_remaining_raw = _meta.get("budget_remaining", budget_remaining)
                _saved_budget = (
                    float(_budget_remaining_raw)
                    if isinstance(_budget_remaining_raw, (int, float))
                    else budget_remaining
                )
                _saved_content = str(_meta.get("content", input_text))
                _saved_history_raw = _meta.get("history", [])
                _saved_history: tuple[str, ...] = tuple(
                    str(h)
                    for h in (_saved_history_raw if isinstance(_saved_history_raw, list) else [])
                )
                ctx = HandoffContext(
                    content=_saved_content,
                    history=_saved_history,
                    budget_remaining=_saved_budget,
                    step_index=resume_from_step,
                    workflow_name=self._workflow_name,
                    run_id=self.run_id,
                )

        self._emit(
            Hook.WORKFLOW_STARTED,
            EventContext(
                run_id=self.run_id,
                workflow_name=self._workflow_name,
                input=input_text,
                step_count=len(self._steps),
                budget_total=budget_remaining,
            ),
        )

        last_response: Response[str] = Response(content=ctx.content, cost=0.0)

        # Set up real-time forecaster when budget is configured
        forecaster: BudgetForecaster | None = None
        if self._budget and self._budget.max_cost and self._budget.max_cost > 0:
            _max = self._budget.max_cost
            forecaster = BudgetForecaster(total_p50=_max * 0.7, total_p95=_max * 0.95)

        try:
            for step_idx, step in enumerate(self._steps):
                # ── Skip already-completed steps on checkpoint resume ────────
                if step_idx < resume_from_step:
                    continue

                # ── Cancel check ────────────────────────────────────────────
                if self._cancel_event.is_set():
                    raise WorkflowCancelledError("Workflow was cancelled.")

                # ── Pause check ─────────────────────────────────────────────
                if self._pause_event.is_set():
                    await self._do_pause(step_idx, total_cost)
                    # After resume, re-check cancel
                    if self._cancel_event.is_set():
                        raise WorkflowCancelledError("Workflow was cancelled.")

                self._emit(
                    Hook.WORKFLOW_STEP_START,
                    EventContext(
                        run_id=self.run_id,
                        workflow_name=self._workflow_name,
                        step_index=step_idx,
                        step_type=type(step).__name__,
                    ),
                )

                import time as _time  # noqa: PLC0415

                step_start = _time.monotonic()
                response, step_cost = await self._run_step(step, ctx)
                step_duration = _time.monotonic() - step_start

                total_cost += step_cost
                budget_remaining = max(0.0, budget_remaining - step_cost)

                self._emit(
                    Hook.WORKFLOW_STEP_END,
                    EventContext(
                        run_id=self.run_id,
                        workflow_name=self._workflow_name,
                        step_index=step_idx,
                        cost=step_cost,
                        duration_s=step_duration,
                    ),
                )

                last_response = response
                if self.handle:
                    self.handle._update_step(step_idx)
                    self.handle._add_cost(step_cost)

                # ── Checkpoint save ──────────────────────────────────────────
                if self._checkpoint_backend is not None:
                    from syrin.checkpoint._core import CheckpointState  # noqa: PLC0415

                    _ckpt_state = CheckpointState(
                        agent_name=self._workflow_name,
                        checkpoint_id=f"{self.run_id}:latest",
                        metadata={
                            "step_index": step_idx,
                            "total_cost": total_cost,
                            "budget_remaining": budget_remaining,
                            "content": response.content,
                            "history": [*ctx.history, ctx.content],
                            "run_id": self.run_id,
                        },
                    )
                    self._checkpoint_backend.save(_ckpt_state)

                # ── Cancel check (after step) ────────────────────────────────
                # Needed to detect cancellation for single-step workflows or
                # when cancel() was called while the step was executing.
                if self._cancel_event.is_set():
                    raise WorkflowCancelledError("Workflow was cancelled.")

                # ── Budget forecast ──────────────────────────────────────────
                if forecaster is not None:
                    steps_remaining = len(self._steps) - step_idx - 1
                    forecaster.update(step_index=step_idx, actual_spent=total_cost)
                    forecaster.fire_hook(
                        lambda hook, data: self._emit(hook, EventContext(**dict(data.items()))),
                        spent=total_cost,
                        steps_remaining=steps_remaining,
                    )
                    # Abort if forecast exceeds budget * multiplier
                    if (
                        self._budget is not None
                        and getattr(self._budget, "abort_on_forecast_exceeded", False)
                        and self._budget.max_cost
                        and steps_remaining > 0
                    ):
                        _multiplier = getattr(self._budget, "abort_forecast_multiplier", 1.0)
                        _threshold = self._budget.max_cost * _multiplier
                        _result = forecaster.forecast(steps_remaining=steps_remaining)
                        if _result.forecast_p50 > _threshold:
                            raise ForecastAbortError(
                                f"Forecast (${_result.forecast_p50:.4f}) exceeds budget "
                                f"${self._budget.max_cost:.2f} × {_multiplier} = ${_threshold:.4f}. Aborting.",
                                forecast_p50=_result.forecast_p50,
                                max_cost=self._budget.max_cost,
                                multiplier=_multiplier,
                            )

                # Build the HandoffContext for the next step
                ctx = ctx.evolve(
                    content=response.content,
                    data=response.structured if hasattr(response, "structured") else None,
                    history=(*ctx.history, ctx.content),
                    budget_remaining=budget_remaining,
                    step_index=step_idx + 1,
                )

        except WorkflowCancelledError:
            self._emit(
                Hook.WORKFLOW_CANCELLED,
                EventContext(
                    run_id=self.run_id,
                    workflow_name=self._workflow_name,
                    reason="cancel requested",
                    cost=total_cost,
                ),
            )
            if self.handle:
                self.handle._mark_cancelled()
            raise

        except Exception as exc:
            self._emit(
                Hook.WORKFLOW_FAILED,
                EventContext(
                    run_id=self.run_id,
                    workflow_name=self._workflow_name,
                    error=str(exc),
                    error_type=type(exc).__name__,
                    cost=total_cost,
                ),
            )
            if self.handle:
                self.handle._mark_failed()
            raise

        import time as _time  # noqa: PLC0415

        self._emit(
            Hook.WORKFLOW_COMPLETED,
            EventContext(
                run_id=self.run_id,
                workflow_name=self._workflow_name,
                cost=total_cost,
                steps_completed=len(self._steps),
            ),
        )

        if self.handle:
            self.handle._mark_completed()

        return last_response

    # ──────────────────────────────────────────────────────────────────────────
    # Step dispatch
    # ──────────────────────────────────────────────────────────────────────────

    async def _run_step(
        self,
        step: WorkflowStep,
        ctx: HandoffContext[object],
    ) -> tuple[Response[str], float]:
        """Dispatch to the correct step runner.

        Args:
            step: The step to execute.
            ctx: Current :class:`~syrin.workflow._context.HandoffContext`.

        Returns:
            Tuple of ``(response, cost_usd)``.

        Raises:
            WorkflowStepError: If the step raises an unhandled exception.
        """
        try:
            match step:
                case SequentialStep():
                    return await self._run_sequential(step, ctx)
                case ParallelStep():
                    return await self._run_parallel(step, ctx)
                case BranchStep():
                    return await self._run_branch(step, ctx)
                case DynamicStep():
                    return await self._run_dynamic(step, ctx)
        except (WorkflowStepError, DynamicFanoutError):
            raise
        except Exception as exc:
            raise WorkflowStepError(step_index=ctx.step_index, cause=exc) from exc

    async def _run_sequential(
        self,
        step: SequentialStep,
        ctx: HandoffContext[object],
    ) -> tuple[Response[str], float]:
        """Execute a single agent.

        Args:
            step: The :class:`~syrin.workflow._step.SequentialStep`.
            ctx: Incoming context.

        Returns:
            Tuple of ``(response, cost_usd)``.
        """
        effective_budget = resolve_budget(step=step.budget, workflow=self._budget)
        # `step.agent_class` may be a Workflow instance (duck-typed agent) rather
        # than a class.  Detect this by checking whether it is callable as a
        # constructor — a plain instance already has `arun` and must not be
        # re-instantiated.
        if isinstance(step.agent_class, type):
            agent: Agent = step.agent_class(budget=effective_budget)
            if self._swarm_context is not None:
                object.__setattr__(agent, "_swarm_context", self._swarm_context)
        else:
            # Workflow (or any duck-typed servable) passed as a step instance
            agent = step.agent_class  # duck-typed Workflow instance
        task_text = step.task if step.task is not None else ctx.content
        response = await agent.arun(task_text)
        return response, response.cost

    async def _run_parallel(
        self,
        step: ParallelStep,
        ctx: HandoffContext[object],
    ) -> tuple[Response[str], float]:
        """Execute multiple agents concurrently and merge their outputs.

        Args:
            step: The :class:`~syrin.workflow._step.ParallelStep`.
            ctx: Incoming context.

        Returns:
            Tuple of ``(merged_response, total_cost_usd)``.
        """
        effective_budget = resolve_budget(step=step.budget, workflow=self._budget)

        async def _run_one(agent_class: type[Agent]) -> Response[str]:
            agent = agent_class(budget=effective_budget)
            if self._swarm_context is not None:
                object.__setattr__(agent, "_swarm_context", self._swarm_context)
            return await agent.arun(ctx.content)

        responses: list[Response[str]] = await asyncio.gather(
            *[_run_one(cls) for cls in step.agent_classes]
        )

        combined = "\n\n".join(r.content for r in responses if r.content)
        total_cost = sum(r.cost for r in responses)

        merged = Response(
            content=combined,
            cost=total_cost,
            raw="\n\n".join(r.raw for r in responses if hasattr(r, "raw") and r.raw),
        )

        # Store individual responses so history captures all of them
        merged._parallel_responses = responses  # type: ignore[attr-defined]

        return merged, total_cost

    async def _run_branch(
        self,
        step: BranchStep,
        ctx: HandoffContext[object],
    ) -> tuple[Response[str], float]:
        """Evaluate predicate and run the chosen agent.

        Args:
            step: The :class:`~syrin.workflow._step.BranchStep`.
            ctx: Incoming context.

        Returns:
            Tuple of ``(response, cost_usd)``.

        Raises:
            WorkflowStepError: If the condition callable raises.
        """
        try:
            condition_result = step.condition(ctx)
        except Exception as exc:
            raise WorkflowStepError(step_index=ctx.step_index, cause=exc) from exc

        effective_budget = resolve_budget(step=step.budget, workflow=self._budget)
        chosen_class = step.if_true_class if condition_result else step.if_false_class
        agent = chosen_class(budget=effective_budget)
        response = await agent.arun(ctx.content)
        return response, response.cost

    async def _run_dynamic(
        self,
        step: DynamicStep,
        ctx: HandoffContext[object],
    ) -> tuple[Response[str], float]:
        """Spawn N agents determined by the factory lambda.

        Args:
            step: The :class:`~syrin.workflow._step.DynamicStep`.
            ctx: Incoming context.

        Returns:
            Tuple of ``(merged_response, total_cost_usd)``.

        Raises:
            DynamicFanoutError: If factory returns zero or too many agents.
        """
        agent_specs = step.fn(ctx)

        if len(agent_specs) == 0:
            raise DynamicFanoutError(actual=0)

        if step.max_agents is not None and len(agent_specs) > step.max_agents:
            raise DynamicFanoutError(actual=len(agent_specs), maximum=step.max_agents)

        async def _run_one(agent_class: type[Agent], task: str, budget_usd: float) -> Response[str]:
            agent_budget = (
                Budget(max_cost=budget_usd)
                if budget_usd > 0
                else resolve_budget(workflow=self._budget)
            )
            agent = agent_class(budget=agent_budget)
            return await agent.arun(task)

        responses: list[Response[str]] = await asyncio.gather(
            *[_run_one(cls, task, bgt) for cls, task, bgt in agent_specs]
        )

        combined = "\n\n".join(r.content for r in responses if r.content)
        total_cost = sum(r.cost for r in responses)

        return Response(content=combined, cost=total_cost), total_cost

    # ──────────────────────────────────────────────────────────────────────────
    # Pause / resume helpers
    # ──────────────────────────────────────────────────────────────────────────

    async def _do_pause(self, step_idx: int, total_cost: float) -> None:
        """Block execution until resume or cancel is requested.

        Args:
            step_idx: Current step index (for hook payload).
            total_cost: Total cost spent so far (for hook payload).
        """
        if self.handle:
            self.handle._mark_paused()

        self._emit(
            Hook.WORKFLOW_PAUSED,
            EventContext(
                run_id=self.run_id,
                workflow_name=self._workflow_name,
                step_index=step_idx,
                budget_spent=total_cost,
            ),
        )

        self._resume_event.clear()
        # Wait for resume signal
        await self._resume_event.wait()
        self._resume_event.clear()

        if self.handle and not self._cancel_event.is_set():
            self.handle._mark_running()
            self._emit(
                Hook.WORKFLOW_RESUMED,
                EventContext(
                    run_id=self.run_id,
                    workflow_name=self._workflow_name,
                    step_index=step_idx,
                ),
            )

    # ──────────────────────────────────────────────────────────────────────────
    # Hook emission
    # ──────────────────────────────────────────────────────────────────────────

    def _emit(self, hook: Hook, ctx: EventContext) -> None:
        """Emit a hook via the events system.

        Args:
            hook: Hook to emit.
            ctx: Event context payload.
        """
        import time as _time  # noqa: PLC0415

        ctx["timestamp"] = _time.time()
        self._events._trigger_before(hook, ctx)
        self._events._trigger(hook, ctx)
        self._events._trigger_after(hook, ctx)
