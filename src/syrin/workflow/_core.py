"""Workflow — declarative multi-agent execution graph.

:class:`Workflow` is the public entry point for building typed multi-step
agent pipelines.  It uses a fluent builder API and supports four step kinds:

- ``.step(AgentClass)`` — one agent (sequential)
- ``.parallel([A, B, C])`` — multiple agents concurrently
- ``.branch(condition, if_true, if_false)`` — conditional routing
- ``.dynamic(fn)`` — N agents spawned at runtime

**Workflow vs. Pipeline vs. AgentRouter — when to use which:**

Use :class:`~syrin.agent.pipeline.Pipeline` when:
  * You have a fixed, flat sequence of 1–3 agents with no branching.
  * You only need sequential (A→B→C) or parallel (A‖B‖C) execution.

Use :class:`Workflow` when:
  * You need conditional branching (``branch``).
  * You have more than ~3 agents, or a non-linear dependency graph.
  * You need step-level checkpointing / resume across processes.
  * You want runtime play/pause/resume lifecycle control.

Use :class:`~syrin.agent.agent_router.AgentRouter` when:
  * The LLM should decide which agents are needed at runtime.

Example::

    wf = (
        Workflow("research-pipeline")
        .step(PlannerAgent)
        .parallel([RedditAgent, HNAgent])
        .step(SummarizerAgent)
    )
    result = await wf.run("AI trends in 2026")
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from syrin.budget._estimate import EstimationReport
    from syrin.budget._history import CostStats
    from syrin.checkpoint._core import CheckpointBackendProtocol
    from syrin.swarm._registry import SwarmContext

from syrin.budget import Budget
from syrin.enums import Hook, PauseMode, WorkflowStatus
from syrin.events import EventContext, Events
from syrin.response import Response
from syrin.workflow._executor import WorkflowExecutor
from syrin.workflow._lifecycle import RunHandle
from syrin.workflow._step import (
    BranchStep,
    DynamicStep,
    ParallelStep,
    SequentialStep,
    WorkflowStep,
)
from syrin.workflow._visualize import to_dict, to_mermaid, visualize
from syrin.workflow.exceptions import WorkflowCancelledError, WorkflowNotRunnable

T = TypeVar("T")


class WorkflowCostStats:
    """Aggregated and per-step cost statistics for a workflow.

    Attributes:
        per_step: List of :class:`~syrin.budget._history.CostStats`, one per
            agent step in the workflow (parallel steps contribute one entry each).
        total_mean: Sum of mean costs across all steps (USD).
        total_p95: Sum of p95 costs across all steps — conservative total estimate (USD).
    """

    def __init__(
        self,
        *,
        per_step: list[CostStats],
        total_mean: float,
        total_p95: float,
    ) -> None:
        self.per_step = per_step
        self.total_mean = total_mean
        self.total_p95 = total_p95


class Workflow:
    """Declarative multi-agent workflow with lifecycle control.

    Build the workflow with the fluent API, then call :meth:`run` (blocking)
    or :meth:`play` (non-blocking, returns a :class:`~syrin.workflow._lifecycle.RunHandle`).

    Workflow instances do not share mutable state — creating two instances with
    the same steps is safe.

    Attributes:
        name: Human-readable workflow identifier.
        events: Lifecycle event hooks (WORKFLOW_STARTED, WORKFLOW_STEP_START, etc.).

    Example::

        from syrin.workflow import Workflow
        from syrin import Budget

        wf = (
            Workflow("summariser", budget=Budget(max_cost=2.00))
            .step(ResearchAgent, task="Find recent papers on LLMs")
            .step(SummarizerAgent)
        )
        result = await wf.run("Summarise LLM research")
        print(result.content)
    """

    def __init__(
        self,
        name: str = "workflow",
        budget: Budget | None = None,
        pry: bool = False,
        checkpoint_backend: CheckpointBackendProtocol | None = None,
        resume_run_id: str | None = None,
    ) -> None:
        """Initialise a Workflow.

        Args:
            name: Human-readable workflow identifier shown in hooks and visualisations.
            budget: Optional workflow-level budget.  Step-level budgets take
                precedence via :func:`~syrin.workflow._budget.resolve_budget`.
            pry: Enable the Pry debugger for this workflow.  When ``True``,
                the workflow pauses at ``.debugpoint()`` markers and at the
                breakpoints configured in :class:`~syrin.debug._breakpoints.PryConfig`.
            checkpoint_backend: Persistent backend for workflow step state.
                When provided, step progress is saved after each step and can
                be resumed across processes using ``resume_run_id``.
            resume_run_id: Run ID to resume from a prior checkpoint.  Pass the
                ``run_id`` from a previous :meth:`run` or :meth:`play` call.
        """
        self._name = name
        self._budget = budget
        self._pry = pry
        self._checkpoint_backend: CheckpointBackendProtocol | None = checkpoint_backend
        self._resume_run_id: str | None = resume_run_id
        self._swarm_context: SwarmContext | None = None  # injected by WORKFLOW topology
        self._steps: list[WorkflowStep] = []
        self._debug_points: list[int] = []  # step indices where debugpoints are inserted
        self._events: Events = Events(self._emit)
        self._executor: WorkflowExecutor | None = None

    # ──────────────────────────────────────────────────────────────────────────
    # Properties
    # ──────────────────────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        """Human-readable workflow identifier."""
        return self._name

    @property
    def step_count(self) -> int:
        """Number of steps in the workflow."""
        return len(self._steps)

    @property
    def budget(self) -> Budget | None:
        """Workflow-level budget, or ``None`` if not configured."""
        return self._budget

    @property
    def events(self) -> Events:
        """Lifecycle event hooks.

        Example::

            wf.events.on(Hook.WORKFLOW_STEP_END, lambda ctx: print(ctx))
        """
        return self._events

    # ──────────────────────────────────────────────────────────────────────────
    # Builder API (fluent, returns self)
    # ──────────────────────────────────────────────────────────────────────────

    def step(
        self,
        agent_class: type[object],  # type[Agent] — avoid circular import
        task: str | None = None,
        budget: Budget | None = None,
    ) -> Workflow:
        """Add a sequential agent step.

        Args:
            agent_class: Agent class to instantiate and run.
            task: Optional task override.  When omitted the step receives
                ``HandoffContext.content`` from the previous step.
            budget: Optional per-step budget override.

        Returns:
            ``self`` (fluent interface).

        Example::

            wf.step(PlannerAgent, task="Create a research plan")
        """

        self._steps.append(
            SequentialStep(
                agent_class=agent_class,  # type: ignore[arg-type]
                task=task,
                budget=budget,
            )
        )
        return self

    def parallel(
        self,
        agent_classes: list[type[object]],  # type[Agent]
        budget: Budget | None = None,
    ) -> Workflow:
        """Add a parallel step that runs multiple agents concurrently.

        Args:
            agent_classes: Two or more agent classes to run simultaneously.
            budget: Optional per-step budget override applied to all agents.

        Returns:
            ``self`` (fluent interface).

        Raises:
            ValueError: If fewer than two classes are provided.

        Example::

            wf.parallel([RedditAgent, HNAgent, ArxivAgent])
        """
        self._steps.append(
            ParallelStep(
                agent_classes=tuple(agent_classes),  # type: ignore[arg-type]
                budget=budget,
            )
        )
        return self

    def branch(
        self,
        condition: Callable[[object], object],
        if_true: type[object],  # type[Agent]
        if_false: type[object],  # type[Agent]
        budget: Budget | None = None,
    ) -> Workflow:
        """Add a conditional branch step.

        Args:
            condition: Predicate receiving the incoming
                :class:`~syrin.workflow._context.HandoffContext`.  Truthy
                value → ``if_true`` agent; falsy → ``if_false`` agent.
            if_true: Agent class to run when condition is truthy.
            if_false: Agent class to run when condition is falsy.
            budget: Optional per-step budget override.

        Returns:
            ``self`` (fluent interface).

        Example::

            wf.branch(
                condition=lambda ctx: "urgent" in ctx.content.lower(),
                if_true=FastAgent,
                if_false=ThoroughAgent,
            )
        """
        from typing import cast  # noqa: PLC0415

        from syrin.agent._core import Agent as _Agent  # noqa: PLC0415

        self._steps.append(
            BranchStep(
                condition=condition,
                if_true_class=cast("type[_Agent]", if_true),
                if_false_class=cast("type[_Agent]", if_false),
                budget=budget,
            )
        )
        return self

    def dynamic(
        self,
        fn: Callable[[object], list[tuple[type[object], str, float]]],
        max_agents: int | None = None,
        label: str = "dynamic",
    ) -> Workflow:
        """Add a dynamic step: spawn N agents determined at runtime.

        Args:
            fn: Factory callable ``(HandoffContext) → [(agent_class, task, budget_usd), ...]``.
            max_agents: Optional upper bound.  Raises
                :class:`~syrin.workflow.exceptions.DynamicFanoutError` if exceeded.
            label: Human-readable label shown in visualisations.

        Returns:
            ``self`` (fluent interface).

        Example::

            wf.dynamic(
                lambda ctx: [
                    (ResearchAgent, section, 0.50)
                    for section in ctx.data.sections
                ],
                max_agents=10,
            )
        """
        self._steps.append(
            DynamicStep(
                fn=fn,  # type: ignore[arg-type]
                max_agents=max_agents,
                label=label,
            )
        )
        return self

    def debugpoint(
        self,
        on: str | None = None,
    ) -> Workflow:
        """Insert a Pry debugpoint before the next step.

        Has no effect unless ``pry=True`` was set at construction time.

        Args:
            on: Optional :class:`~syrin.enums.DebugPoint` value.  When omitted
                defaults to ``DebugPoint.ON_HANDOFF``.

        Returns:
            ``self`` (fluent interface).
        """
        # Record the index of the step that will follow this debugpoint
        self._debug_points.append(len(self._steps))
        return self

    # ──────────────────────────────────────────────────────────────────────────
    # Execution
    # ──────────────────────────────────────────────────────────────────────────

    async def run(
        self,
        input_text: str,
        show_graph: bool = False,
    ) -> Response[str]:
        """Execute the workflow and return the final response.

        Args:
            input_text: Initial task string fed to the first step.
            show_graph: Render a live graph to the terminal during execution.

        Returns:
            :class:`~syrin.response.Response` from the last step.

        Raises:
            WorkflowNotRunnable: If no steps have been added.

        Example::

            result = await wf.run("Summarise LLM research")
        """
        self._check_runnable()
        executor = self._make_executor()
        self._executor = executor
        if not show_graph:
            return await executor.run(input_text)
        return await self._run_with_graph(executor, input_text)

    async def _run_with_graph(self, executor: WorkflowExecutor, input_text: str) -> Response[str]:
        """Run the workflow with a live Rich progress display.

        Shows each step as PENDING → RUNNING → COMPLETE with elapsed time and
        cost.  Failed steps show FAILED in red; steps that did not run show
        SKIPPED.

        Args:
            executor: Fresh :class:`~syrin.workflow._executor.WorkflowExecutor`.
            input_text: Initial task string.

        Returns:
            :class:`~syrin.response.Response` from the last step.
        """
        import time as _time  # noqa: PLC0415

        try:
            from rich.console import Console  # noqa: PLC0415
            from rich.table import Table  # noqa: PLC0415

            console = Console()
        except ImportError:
            return await executor.run(input_text)

        step_names: list[str] = []
        for step in self._steps:
            match step:
                case SequentialStep(agent_class=cls):
                    _step_name: str = (
                        getattr(cls, "__name__", None) or getattr(cls, "name", None) or str(cls)
                    )
                    step_names.append(_step_name)
                case ParallelStep(agent_classes=classes):
                    step_names.append(f"parallel({', '.join(c.__name__ for c in classes)})")
                case BranchStep():
                    step_names.append("branch")
                case DynamicStep(label=lbl):
                    step_names.append(f"dynamic:{lbl}")

        num_steps = len(step_names)
        step_status: list[str] = ["PENDING"] * num_steps
        step_cost: list[float] = [0.0] * num_steps
        step_start: list[float] = [0.0] * num_steps
        step_elapsed: list[float] = [0.0] * num_steps
        failed_at: list[int] = []

        def _render() -> None:
            table = Table(title=f"Workflow: {self._name}", show_lines=True)
            table.add_column("#", style="dim", width=4)
            table.add_column("Step")
            table.add_column("Status", width=12)
            table.add_column("Cost", width=12)
            table.add_column("Elapsed", width=10)
            for i, name in enumerate(step_names):
                status = step_status[i]
                if status == "RUNNING":
                    status_str = "[yellow]RUNNING[/yellow]"
                elif status == "COMPLETE":
                    status_str = "[green]COMPLETE[/green]"
                elif status == "FAILED":
                    status_str = "[red]FAILED[/red]"
                elif status == "SKIPPED":
                    status_str = "[dim]SKIPPED[/dim]"
                else:
                    status_str = "[dim]PENDING[/dim]"
                cost_str = f"${step_cost[i]:.6f}" if step_cost[i] else "-"
                elapsed_str = f"{step_elapsed[i]:.2f}s" if step_elapsed[i] else "-"
                table.add_row(str(i), name, status_str, cost_str, elapsed_str)
            console.print(table)

        def _on_step_start(ctx: EventContext) -> None:
            idx = int(getattr(ctx, "step_index", -1))
            if 0 <= idx < num_steps:
                step_status[idx] = "RUNNING"
                step_start[idx] = _time.monotonic()

        def _on_step_end(ctx: EventContext) -> None:
            idx = int(getattr(ctx, "step_index", -1))
            if 0 <= idx < num_steps:
                step_status[idx] = "COMPLETE"
                step_cost[idx] = float(getattr(ctx, "cost", 0.0))
                step_elapsed[idx] = _time.monotonic() - step_start[idx]

        def _on_failed(ctx: EventContext) -> None:
            for i, s in enumerate(step_status):
                if s == "RUNNING":
                    step_status[i] = "FAILED"
                    step_elapsed[i] = _time.monotonic() - step_start[i]
                    failed_at.append(i)
            # Mark remaining PENDING steps as SKIPPED
            for i, s in enumerate(step_status):
                if s == "PENDING":
                    step_status[i] = "SKIPPED"

        self.events.on(Hook.WORKFLOW_STEP_START, _on_step_start)
        self.events.on(Hook.WORKFLOW_STEP_END, _on_step_end)
        self.events.on(Hook.WORKFLOW_FAILED, _on_failed)

        try:
            result = await executor.run(input_text)
        except Exception:
            _render()
            raise

        _render()
        return result

    async def arun(self, input_text: str) -> Response[str]:
        """Alias for :meth:`run` (both are async).

        Args:
            input_text: Initial task string.

        Returns:
            :class:`~syrin.response.Response` from the last step.
        """
        return await self.run(input_text)

    def estimate(self, input_text: str) -> EstimationReport:
        """Estimate the cost of running this workflow without making any LLM calls.

        Walks the workflow steps, calls :meth:`~syrin.budget.CostEstimator.estimate_agent`
        for each agent class, and aggregates the results into an
        :class:`~syrin.budget._estimate.EstimationReport`.

        Args:
            input_text: The input that would be passed to :meth:`run`. Currently
                not used in estimation (reserved for future prompt-length estimation).

        Returns:
            :class:`~syrin.budget._estimate.EstimationReport` with ``total_p50``,
            ``total_p95``, ``budget_sufficient``, ``per_step``, and ``low_confidence``.

        Raises:
            WorkflowNotRunnable: If the workflow has no steps.

        Example::

            report = wf.estimate("Summarise AI trends")
            if not report.budget_sufficient:
                print(f"Budget may be insufficient; p95=${report.total_p95:.4f}")
        """
        from syrin.budget._estimate import (  # noqa: PLC0415
            CostEstimate,
            CostEstimator,
            EstimationReport,
        )

        self._check_runnable()
        estimator = CostEstimator()
        per_step: list[CostEstimate] = []

        for step in self._steps:
            if isinstance(step, SequentialStep):
                est = estimator.estimate_agent(step.agent_class)
                per_step.append(est)
            elif isinstance(step, ParallelStep):
                for cls in step.agent_classes:
                    est = estimator.estimate_agent(cls)
                    per_step.append(est)
            elif isinstance(step, BranchStep):
                # Estimate both branches and use the max (conservative)
                est_true = estimator.estimate_agent(step.if_true_class)
                est_false = estimator.estimate_agent(step.if_false_class)
                # Use the more expensive branch as the estimate
                combined = CostEstimate(
                    p50=max(est_true.p50, est_false.p50),
                    p95=max(est_true.p95, est_false.p95),
                    sufficient=True,
                    low_confidence=est_true.low_confidence or est_false.low_confidence,
                )
                per_step.append(combined)
            # DynamicStep: cannot estimate without runtime data; skip

        total_p50 = sum(e.p50 for e in per_step)
        total_p95 = sum(e.p95 for e in per_step)
        any_low_confidence = any(e.low_confidence for e in per_step)

        max_cost: float | None = self._budget.max_cost if self._budget is not None else None
        budget_sufficient = True if max_cost is None else float(max_cost) >= total_p95

        return EstimationReport(
            total_p50=total_p50,
            total_p95=total_p95,
            budget_sufficient=budget_sufficient,
            per_step=per_step,
            low_confidence=any_low_confidence,
        )

    def cost_stats(self) -> WorkflowCostStats:
        """Return historical cost statistics per step for this workflow.

        Queries the default :class:`~syrin.budget._history.RollingBudgetStore`
        for each agent class in the workflow's steps. Requires runs with
        ``estimation=True`` on the ``Budget`` to have history data.

        Returns:
            :class:`WorkflowCostStats` with ``per_step`` (list of
            :class:`~syrin.budget._history.CostStats`) and aggregated
            ``total_mean`` / ``total_p95``.

        Example::

            wf_stats = wf.cost_stats()
            for step_stats in wf_stats.per_step:
                print(f"{step_stats.agent_name}: p95=${step_stats.p95_cost:.3f}")
        """
        from syrin.budget._history import _get_default_store  # noqa: PLC0415

        store = _get_default_store()
        per_step: list[CostStats] = []

        for step in self._steps:
            if isinstance(step, SequentialStep):
                per_step.append(store.stats(step.agent_class.__name__))
            elif isinstance(step, ParallelStep):
                for cls in step.agent_classes:
                    per_step.append(store.stats(cls.__name__))
            elif isinstance(step, BranchStep):
                per_step.append(store.stats(step.if_true_class.__name__))
                per_step.append(store.stats(step.if_false_class.__name__))
            # DynamicStep: agent classes unknown until runtime; skip

        total_mean = sum(s.mean for s in per_step)
        total_p95 = sum(s.p95_cost for s in per_step)
        return WorkflowCostStats(per_step=per_step, total_mean=total_mean, total_p95=total_p95)

    def play(self, input_text: str) -> RunHandle[str]:
        """Start execution in a background task and return immediately.

        Args:
            input_text: Initial task string fed to the first step.

        Returns:
            :class:`~syrin.workflow._lifecycle.RunHandle` for pause/resume/cancel
            and final result retrieval.

        Raises:
            WorkflowNotRunnable: If no steps have been added.

        Example::

            handle = wf.play("Research AI trends")
            # ... do other things ...
            result = await handle.wait()
        """
        self._check_runnable()
        executor = self._make_executor()
        self._executor = executor
        return executor.play(input_text)

    # ──────────────────────────────────────────────────────────────────────────
    # Lifecycle controls
    # ──────────────────────────────────────────────────────────────────────────

    async def pause(self, mode: PauseMode = PauseMode.AFTER_CURRENT_STEP) -> None:
        """Request the workflow to pause.

        Args:
            mode: When the pause takes effect.  Defaults to
                :attr:`~syrin.enums.PauseMode.AFTER_CURRENT_STEP`.

        Raises:
            RuntimeError: If no run is in progress (``play()`` was not called).
        """
        if self._executor is None:
            raise RuntimeError("No workflow run in progress. Call play() first.")
        await self._executor.request_pause(mode)

    async def resume(self) -> None:
        """Resume a paused workflow.

        Raises:
            RuntimeError: If no run is in progress.
            WorkflowCancelledError: If the workflow was cancelled (cannot resume).
        """
        if self._executor is None:
            raise RuntimeError("No workflow run in progress.")
        handle = self._executor.handle
        # Check both the handle status (for completed runs) and the cancel
        # event (for in-flight tasks where status hasn't propagated yet).
        if handle and handle.status == WorkflowStatus.CANCELLED:
            raise WorkflowCancelledError("Cannot resume a cancelled workflow.")
        if self._executor._cancel_event.is_set():
            raise WorkflowCancelledError("Cannot resume a cancelled workflow.")
        await self._executor.request_resume()

    async def cancel(self) -> None:
        """Cancel the running workflow.

        Subsequent calls to :meth:`resume` will raise
        :class:`~syrin.workflow.exceptions.WorkflowCancelledError`.

        Raises:
            RuntimeError: If no run is in progress.
        """
        if self._executor is None:
            raise RuntimeError("No workflow run in progress.")
        await self._executor.request_cancel()

    # ──────────────────────────────────────────────────────────────────────────
    # Visualisation
    # ──────────────────────────────────────────────────────────────────────────

    def visualize(self, expand_nested: bool = False) -> None:
        """Print a rich ASCII tree of the workflow to stdout.

        Args:
            expand_nested: When ``True``, nested sub-workflows are rendered
                inline with all their steps visible.  When ``False`` (default)
                they appear as a collapsed ``[SubWorkflow]`` block.

        Example::

            wf.visualize()
            wf.visualize(expand_nested=True)
        """
        visualize(self._steps, name=self._name, expand_nested=expand_nested)

    def to_mermaid(self, direction: str = "TD") -> str:
        """Render the workflow graph as a Mermaid diagram string.

        Args:
            direction: ``"TD"`` (top-down, default) or ``"LR"`` (left-right).

        Returns:
            Mermaid ``graph`` block string.

        Example::

            print(wf.to_mermaid())
        """
        return to_mermaid(self._steps, direction=direction)

    def to_dict(self) -> dict[str, object]:
        """Serialise the workflow graph to a plain dictionary.

        Returns:
            Dict with ``"nodes"`` and ``"edges"`` keys.

        Example::

            graph = wf.to_dict()
            for node in graph["nodes"]:
                print(node)
        """
        return to_dict(self._steps)

    def serve(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
        **kwargs: object,
    ) -> None:
        """Serve this workflow as an HTTP endpoint. Blocks until stopped.

        Exposes:

        - ``POST /chat`` — accepts ``{"message": "..."}`` and returns the
          workflow result as JSON.
        - ``GET /graph`` — returns the Mermaid graph string for this workflow.

        Args:
            host: Bind address (default ``"0.0.0.0"``).
            port: HTTP port (default ``8000``).
            **kwargs: Reserved for future options (ignored).

        Raises:
            ImportError: If ``uvicorn`` or ``fastapi`` is not installed.

        Example::

            wf.serve(port=8080)
        """
        try:
            import uvicorn
            from fastapi import FastAPI
            from fastapi.responses import JSONResponse
        except ImportError as exc:
            raise ImportError(
                "Workflow.serve() requires fastapi and uvicorn. "
                "Install with: uv pip install syrin[serve]"
            ) from exc

        wf_ref = self
        app = FastAPI(title=f"Syrin Workflow: {self._name}")

        @app.post("/chat")
        async def _chat(body: dict[str, object]) -> JSONResponse:
            message = str(body.get("message", ""))
            result = await wf_ref.run(message)
            return JSONResponse({"content": result.content, "cost": result.cost})

        @app.get("/graph")
        async def _graph() -> JSONResponse:
            return JSONResponse({"graph": wf_ref.to_mermaid()})

        uvicorn.run(app, host=host, port=port, workers=1)

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _check_runnable(self) -> None:
        """Raise :class:`~syrin.workflow.exceptions.WorkflowNotRunnable` if no steps."""
        if not self._steps:
            raise WorkflowNotRunnable(
                f"Workflow '{self._name}' has no steps. "
                "Add steps with .step(), .parallel(), .branch(), or .dynamic()."
            )

    def _make_executor(self) -> WorkflowExecutor:
        """Create a fresh :class:`~syrin.workflow._executor.WorkflowExecutor` for a new run.

        Returns:
            A new executor instance bound to this workflow's steps and events.
        """
        return WorkflowExecutor(
            steps=list(self._steps),
            workflow_name=self._name,
            budget=self._budget,
            events=self._events,
            checkpoint_backend=self._checkpoint_backend,
            run_id=self._resume_run_id,
            swarm_context=self._swarm_context,
        )

    def _emit(self, hook: Hook, ctx: EventContext) -> None:
        """Emit a hook via the events system (used as Events callback).

        Args:
            hook: Hook to emit.
            ctx: Event context payload.
        """
        import time  # noqa: PLC0415

        ctx["timestamp"] = time.time()
        self._events._trigger_before(hook, ctx)
        self._events._trigger(hook, ctx)
        self._events._trigger_after(hook, ctx)

    def __repr__(self) -> str:
        """Return a debug representation.

        Returns:
            String like ``Workflow('research-pipeline', steps=3)``.
        """
        return f"Workflow({self._name!r}, steps={len(self._steps)})"
