"""Pipeline — static multi-agent execution (sequential or parallel).

Extracted from ``syrin.agent.multi_agent`` in v0.11.0.  This is now the
canonical home for :class:`Pipeline`.  The old import path
``from syrin.agent.multi_agent import Pipeline`` still works via a
backward-compatibility re-export.

**Pipeline vs. Workflow — when to use which:**

Use :class:`Pipeline` when:
  * You have a fixed, flat sequence of 1–3 agents.
  * You only need sequential (A→B→C) or parallel (A‖B‖C) execution.
  * You don't need branching, conditional logic, or step-level checkpoints.

Use :class:`~syrin.workflow._core.Workflow` when:
  * You need branching (``if score > 0.8: use WriterA else WriterB``).
  * You have more than ~3 agents or a non-linear dependency graph.
  * You need step-level checkpointing / resume.
  * You want play/pause/resume lifecycle control at runtime.

Use :class:`~syrin.agent.agent_router.AgentRouter` when:
  * You don't know which agents are needed until the LLM sees the task.

Quick reference::

    # Flat, known agents → Pipeline
    result = Pipeline().run([ResearchAgent, WriterAgent]).sequential()

    # DAG with branching → Workflow
    result = await Workflow("report").step(PlannerAgent).branch([...]).run(task)

    # Dynamic agent selection → AgentRouter
    result = AgentRouter(agents=[...]).run(task)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Unpack

if TYPE_CHECKING:
    from syrin.workflow._lifecycle import RunHandle

from syrin.agent._core import Agent
from syrin.audit import AuditHookHandler, AuditLog
from syrin.budget import Budget
from syrin.enums import Hook, StopReason
from syrin.events import EventContext, Events
from syrin.response import Response
from syrin.serve.config import ServeConfig, ServeConfigKwargs
from syrin.serve.servable import Servable
from syrin.types import TokenUsage
from syrin.watch import Watchable

_log = logging.getLogger(__name__)


class PipelineBuilder:
    """Builder for pipeline execution.  Executes sequentially by default.

    Returned by :meth:`Pipeline.run`. Access ``.content`` / ``.cost`` for the
    sequential result or call ``.parallel()`` for parallel execution.

    Example::

        result = pipeline.run([ResearchAgent, WriterAgent])
        print(result.content)           # sequential
        results = pipeline.run([...]).parallel()  # parallel
    """

    def __init__(
        self,
        pipeline: Pipeline,
        agents: list[type[Agent] | tuple[type[Agent], str]],
    ) -> None:
        """Initialise the builder.

        Args:
            pipeline: Parent :class:`Pipeline` instance.
            agents: Agent classes or ``(agent_class, task)`` tuples to run.
        """
        self._pipeline = pipeline
        self._agents = agents

    def __call__(self) -> Response[str]:
        """Execute sequentially (default behaviour).

        Returns:
            Response from the last agent in the pipeline.
        """
        return self._pipeline.run_sequential(self._agents)

    @property
    def content(self) -> str:
        """Content of the sequential execution result."""
        return self._pipeline.run_sequential(self._agents).content

    @property
    def cost(self) -> float:
        """Total cost of the sequential execution."""
        return self._pipeline.run_sequential(self._agents).cost

    @property
    def budget(self) -> object:
        """Budget from the sequential execution result."""
        return self._pipeline.run_sequential(self._agents).budget

    def sequential(self) -> Response[str]:
        """Run agents sequentially (explicit).

        Returns:
            Response from the last agent.
        """
        return self._pipeline.run_sequential(self._agents)

    def parallel(self) -> list[Response[str]]:
        """Run agents in parallel.

        Returns:
            List of responses from all agents.
        """
        return self._pipeline.run_parallel(self._agents)


class PipelineRun:
    """Builder for pipeline execution with fluent API.

    Provides chaining methods to specify execution mode::

        pipeline.run(agents)               # sequential (default)
        pipeline.run(agents).sequential()  # sequential (explicit)
        pipeline.run(agents).parallel()    # parallel

    Attributes:
        _pipeline: Parent pipeline instance.
        _agents: List of agents to run.
    """

    def __init__(
        self,
        pipeline: Pipeline,
        agents: list[type[Agent] | tuple[type[Agent], str]],
    ) -> None:
        """Initialise pipeline run.

        Args:
            pipeline: Parent pipeline instance.
            agents: List of agent classes or ``(agent_class, task)`` tuples.
        """
        self._pipeline = pipeline
        self._agents = agents

    def __call__(self) -> Response[str]:
        """Execute pipeline sequentially (default behaviour).

        Returns:
            Response from the last agent.
        """
        return self.sequential()

    def sequential(self) -> Response[str]:
        """Run agents sequentially, passing output of each as input to next.

        Returns:
            Response from the last agent.
        """
        if not self._agents:
            return _empty_response()

        pipeline = self._pipeline
        pipeline._emit_pipeline_hook(
            Hook.PIPELINE_START,
            EventContext(agents=len(self._agents)),
        )

        result: Response[str] | None = None
        budget = pipeline._budget
        total_cost = 0.0

        for idx, item in enumerate(self._agents):
            if isinstance(item, tuple):
                agent_class, task = item
            else:
                agent_class = item
                task = ""

            agent_name = agent_class.__name__
            pipeline._emit_pipeline_hook(
                Hook.PIPELINE_AGENT_START,
                EventContext(agent_type=agent_name, task=task, index=idx),
            )

            agent = agent_class(budget=budget) if budget else agent_class()

            if result and task:
                combined_input = f"{task}\n\nPrevious context: {result.content}"
                result = agent.run(combined_input)
            elif task:
                result = agent.run(task)

            if result:
                total_cost += result.cost
            pipeline._emit_pipeline_hook(
                Hook.PIPELINE_AGENT_COMPLETE,
                EventContext(
                    agent_type=agent_name,
                    cost=result.cost if result else 0.0,
                    content_preview=(result.content[:200] if result and result.content else ""),
                ),
            )

        pipeline._emit_pipeline_hook(
            Hook.PIPELINE_END,
            EventContext(total_cost=total_cost),
        )

        return result or _empty_response()

    def parallel(self) -> list[Response[str]]:
        """Run agents in parallel.

        Returns:
            List of responses from all agents.
        """
        if not self._agents:
            return []

        pipeline = self._pipeline
        pipeline._emit_pipeline_hook(
            Hook.PIPELINE_START,
            EventContext(agents=len(self._agents)),
        )

        results: list[Response[str]] = []
        budget = pipeline._budget

        for idx, item in enumerate(self._agents):
            if isinstance(item, tuple):
                agent_class, task = item
            else:
                agent_class = item
                task = ""

            agent_name = agent_class.__name__
            pipeline._emit_pipeline_hook(
                Hook.PIPELINE_AGENT_START,
                EventContext(agent_type=agent_name, task=task, index=idx),
            )

            agent = agent_class(budget=budget) if budget else agent_class()

            if task:
                result = agent.run(task)
            else:
                result = _empty_response(
                    model=(agent_class.model.model_id if hasattr(agent_class, "model") else ""),
                )

            results.append(result)
            pipeline._emit_pipeline_hook(
                Hook.PIPELINE_AGENT_COMPLETE,
                EventContext(
                    agent_type=agent_name,
                    cost=result.cost,
                    content_preview=(result.content[:200] if result.content else ""),
                ),
            )

        total_cost = sum(r.cost for r in results)
        pipeline._emit_pipeline_hook(
            Hook.PIPELINE_END,
            EventContext(total_cost=total_cost),
        )

        return results

    async def sequential_async(self) -> Response[str]:
        """Run agents sequentially with async support.

        Returns:
            Response from the last agent.
        """
        if not self._agents:
            return _empty_response()

        pipeline = self._pipeline
        pipeline._emit_pipeline_hook(
            Hook.PIPELINE_START,
            EventContext(agents=len(self._agents)),
        )

        result: Response[str] | None = None
        budget = pipeline._budget
        total_cost = 0.0

        for idx, item in enumerate(self._agents):
            if isinstance(item, tuple):
                agent_class, task = item
            else:
                agent_class = item
                task = ""

            agent_name = agent_class.__name__
            pipeline._emit_pipeline_hook(
                Hook.PIPELINE_AGENT_START,
                EventContext(agent_type=agent_name, task=task, index=idx),
            )

            agent = agent_class(budget=budget) if budget else agent_class()

            if result and task:
                combined_input = f"{task}\n\nPrevious context: {result.content}"
                result = await agent.arun(combined_input)
            elif task:
                result = await agent.arun(task)

            if result:
                total_cost += result.cost
            pipeline._emit_pipeline_hook(
                Hook.PIPELINE_AGENT_COMPLETE,
                EventContext(
                    agent_type=agent_name,
                    cost=result.cost if result else 0.0,
                    content_preview=(result.content[:200] if result and result.content else ""),
                ),
            )

        pipeline._emit_pipeline_hook(
            Hook.PIPELINE_END,
            EventContext(total_cost=total_cost),
        )

        return result or _empty_response()

    async def parallel_async(self) -> list[Response[str]]:
        """Run agents in parallel with async support.

        Returns:
            List of responses from all agents.
        """
        if not self._agents:
            return []

        pipeline = self._pipeline
        pipeline._emit_pipeline_hook(
            Hook.PIPELINE_START,
            EventContext(agents=len(self._agents)),
        )

        async def run_one(
            item: type[Agent] | tuple[type[Agent], str],
            idx: int,
        ) -> tuple[Response[str], str]:
            if isinstance(item, tuple):
                agent_class, task = item
            else:
                agent_class = item
                task = ""

            agent_name = agent_class.__name__
            pipeline._emit_pipeline_hook(
                Hook.PIPELINE_AGENT_START,
                EventContext(agent_type=agent_name, task=task, index=idx),
            )

            budget = pipeline._budget
            agent = agent_class(budget=budget) if budget else agent_class()

            if task:
                result = await agent.arun(task)
            else:
                result = _empty_response()

            pipeline._emit_pipeline_hook(
                Hook.PIPELINE_AGENT_COMPLETE,
                EventContext(
                    agent_type=agent_name,
                    cost=result.cost,
                    content_preview=(result.content[:200] if result.content else ""),
                ),
            )

            return result, agent_name

        gathered = await asyncio.gather(
            *[run_one(item, idx) for idx, item in enumerate(self._agents)]
        )
        results = [r[0] for r in gathered]

        total_cost = sum(r.cost for r in results)
        pipeline._emit_pipeline_hook(
            Hook.PIPELINE_END,
            EventContext(total_cost=total_cost),
        )

        return results


class Pipeline(Watchable, Servable):
    """Pipeline for running multiple agents sequentially or in parallel.

    Static pipeline: fixed list of agents. Each agent receives output of the
    previous (sequential) or runs independently (parallel).
    Inherits :class:`~syrin.serve.servable.Servable` — use ``.serve()``.

    Fluent API::

        pipeline.run(agents).sequential()  # one after another (default)
        pipeline.run(agents).parallel()    # simultaneously

    Traditional API::

        pipeline.run_sequential(agents)
        pipeline.run_parallel(agents)

    Attributes:
        events: Pipeline lifecycle hooks (PIPELINE_START, PIPELINE_AGENT_START, etc.).
        agents: List of agent classes or ``(agent_class, task)`` tuples (if set at init).
    """

    def __init__(
        self,
        budget: Budget | None = None,
        timeout: float | None = None,
        agents: list[type[Agent] | tuple[type[Agent], str]] | None = None,
        sequential: bool = True,
        debug: bool = False,
        audit: AuditLog | None = None,
    ) -> None:
        """Initialise pipeline.

        Args:
            budget: Optional shared budget for all agents.
            timeout: Optional timeout in seconds per agent run. ``None`` = no limit.
            agents: Optional pre-configured list of agent classes or
                ``(agent_class, task)`` tuples.
            sequential: Default execution mode. ``True`` = sequential.
            debug: Enable debug logging to console.
            audit: Optional :class:`~syrin.audit.AuditLog` for pipeline events.
        """
        self._budget = budget
        self._timeout = timeout
        self._agents = agents
        self._sequential = sequential
        self._debug = debug
        self._audit = audit
        self._events = Events(self._emit_pipeline_hook)
        if audit is not None:
            if not isinstance(audit, AuditLog):
                raise TypeError(f"audit must be AuditLog or None, got {type(audit).__name__}.")
            audit_handler = AuditHookHandler(source="Pipeline", config=audit)
            self._events.on_all(audit_handler)
        Watchable.__init__(self)

    def _emit_pipeline_hook(self, hook: Hook, ctx: EventContext) -> None:
        """Emit a pipeline lifecycle hook.

        Args:
            hook: The hook to emit.
            ctx: Event context payload.
        """
        ctx["timestamp"] = time.time()
        self._events._trigger_before(hook, ctx)
        self._events._trigger(hook, ctx)
        self._events._trigger_after(hook, ctx)

    @property
    def events(self) -> Events:
        """Pipeline events for hooks (PIPELINE_START, PIPELINE_END, etc.)."""
        return self._events

    @property
    def agents(self) -> list[type[Agent] | tuple[type[Agent], str]] | None:
        """Pre-configured agents in the pipeline."""
        return self._agents

    @property
    def estimated_cost(self) -> object | None:
        """Pre-flight cost estimate for all agents configured on this pipeline.

        Returns ``None`` when ``estimation=False`` on the budget, when no budget
        is set, or when no agents are pre-configured.  Access is synchronous.

        Example::

            pipeline = Pipeline(
                budget=Budget(max_cost=5.0, estimation=True),
                agents=[(ResearchAgent, "research"), (WriterAgent, "write")],
            )
            est = pipeline.estimated_cost
            if est is not None:
                print(f"p50=${est.p50:.4f}  p95=${est.p95:.4f}")
        """
        import logging

        from syrin.budget._estimate import CostEstimate
        from syrin.budget._preflight import InsufficientBudgetError
        from syrin.enums import EstimationPolicy

        budget = self._budget
        if budget is None or not budget.estimation:
            return None

        if not self._agents:
            return None

        # Extract agent classes from (class, task) tuples if needed
        agent_classes: list[type[Agent]] = []
        for entry in self._agents:
            if isinstance(entry, tuple):
                agent_classes.append(entry[0])
            else:
                agent_classes.append(entry)

        estimator = budget._effective_estimator()
        result: CostEstimate = estimator.estimate_many(agent_classes, budget)

        policy = budget.estimation_policy
        if not result.sufficient:
            if policy == EstimationPolicy.RAISE:
                max_cost = budget.max_cost or 0.0
                raise InsufficientBudgetError(
                    total_p50=result.p50,
                    total_p95=result.p95,
                    budget_configured=max_cost,
                    policy=budget.estimation_policy,
                )
            elif policy == EstimationPolicy.WARN_ONLY:
                logging.getLogger(__name__).warning(
                    "Pipeline pre-flight estimation: budget $%.4f may be insufficient "
                    "(p50=$%.4f, p95=$%.4f). Run may exceed budget.",
                    budget.max_cost or 0.0,
                    result.p50,
                    result.p95,
                )

        return result

    def run(
        self,
        agents: list[type[Agent] | tuple[type[Agent], str]],
    ) -> PipelineBuilder:
        """Run agents. Use ``.parallel()`` for parallel execution.

        Args:
            agents: List of agent classes or ``(agent_class, task)`` tuples.

        Returns:
            :class:`PipelineBuilder` — access ``.content``/``.cost`` for the
            sequential result, or call ``.parallel()`` for parallel execution.

        Example::

            result = pipeline.run([
                (ResearcherAgent, "Research topic"),
                (WriterAgent, "Write article"),
            ])
            print(result.content)

            results = pipeline.run([
                (Agent1, "Task 1"),
                (Agent2, "Task 2"),
            ]).parallel()
        """
        return PipelineBuilder(self, agents)

    def run_sequential(
        self,
        agents: list[type[Agent] | tuple[type[Agent], str]],
    ) -> Response[str]:
        """Run agents sequentially (traditional API).

        Args:
            agents: List of agent classes or ``(agent_class, task)`` tuples.

        Returns:
            Response from the last agent.
        """
        return PipelineRun(self, agents).sequential()

    def run_parallel(
        self,
        agents: list[type[Agent] | tuple[type[Agent], str]],
    ) -> list[Response[str]]:
        """Run agents in parallel (traditional API).

        Args:
            agents: List of agent classes or ``(agent_class, task)`` tuples.

        Returns:
            List of responses from all agents.
        """
        return PipelineRun(self, agents).parallel()

    async def run_sequential_async(
        self,
        agents: list[type[Agent] | tuple[type[Agent], str]],
    ) -> Response[str]:
        """Run agents sequentially with async support (traditional API).

        Args:
            agents: List of agent classes or ``(agent_class, task)`` tuples.

        Returns:
            Response from the last agent.
        """
        return await PipelineRun(self, agents).sequential_async()

    async def run_parallel_async(
        self,
        agents: list[type[Agent] | tuple[type[Agent], str]],
    ) -> list[Response[str]]:
        """Run agents in parallel with async support (traditional API).

        Args:
            agents: List of agent classes or ``(agent_class, task)`` tuples.

        Returns:
            List of responses from all agents.
        """
        return await PipelineRun(self, agents).parallel_async()

    def as_router(
        self,
        config: ServeConfig | None = None,
        **config_kwargs: Unpack[ServeConfigKwargs],
    ) -> object:
        """Return a FastAPI ``APIRouter`` for this pipeline. Mount on your app.

        Args:
            config: Optional :class:`~syrin.serve.config.ServeConfig`.
            **config_kwargs: Keyword args forwarded to :class:`ServeConfig`.

        Returns:
            FastAPI ``APIRouter`` instance.
        """
        from typing import cast  # noqa: PLC0415

        from syrin.agent.multi_agent import Pipeline as _Pipeline  # noqa: PLC0415
        from syrin.serve.config import ServeConfig  # noqa: PLC0415
        from syrin.serve.http import build_router  # noqa: PLC0415

        cfg = config if isinstance(config, ServeConfig) else ServeConfig(**config_kwargs)
        return build_router(cast(_Pipeline, self), cfg)

    # ──────────────────────────────────────────────────────────────────────────
    # Lifecycle control — play / pause / resume / cancel
    # ──────────────────────────────────────────────────────────────────────────

    def play(
        self,
        agents: list[type[Agent] | tuple[type[Agent], str]],
        task: str = "",
    ) -> RunHandle[str]:
        """Start pipeline execution in a background task and return immediately.

        Args:
            agents: Agent classes or ``(agent_class, task)`` tuples to run sequentially.
            task: Default task string passed to agents that have no individual task.

        Returns:
            :class:`~syrin.workflow._lifecycle.RunHandle` for lifecycle control.

        Example::

            handle = pipeline.play([PlannerAgent, WriterAgent], task="Research AI")
            result = await handle.wait()
        """
        from syrin.workflow._lifecycle import RunHandle  # noqa: PLC0415
        from syrin.workflow.exceptions import WorkflowCancelledError  # noqa: PLC0415

        self._pipeline_cancel_event = asyncio.Event()
        self._pipeline_pause_event = asyncio.Event()
        self._pipeline_resume_event = asyncio.Event()
        cancel_event = self._pipeline_cancel_event
        pause_event = self._pipeline_pause_event
        resume_event = self._pipeline_resume_event

        import uuid  # noqa: PLC0415

        run_id = f"pipeline-{uuid.uuid4().hex[:12]}"

        async def _run() -> Response[str]:
            result: Response[str] | None = None
            for item in agents:
                # Cancel check before each agent
                if cancel_event.is_set():
                    raise WorkflowCancelledError("Pipeline was cancelled.")

                # Pause check before each agent
                if pause_event.is_set():
                    self._emit_pipeline_hook(
                        Hook.PIPELINE_PAUSED,
                        EventContext(run_id=run_id),
                    )
                    if loop_handle:
                        loop_handle._mark_paused()
                    pause_event.clear()
                    resume_event.clear()
                    await resume_event.wait()
                    if cancel_event.is_set():
                        raise WorkflowCancelledError("Pipeline was cancelled.")
                    self._emit_pipeline_hook(
                        Hook.PIPELINE_RESUMED,
                        EventContext(run_id=run_id),
                    )

                if isinstance(item, tuple):
                    agent_class, agent_task = item
                else:
                    agent_class = item
                    agent_task = task

                agent_instance = agent_class(budget=self._budget) if self._budget else agent_class()
                result = await agent_instance.arun(agent_task)

                # Cancel check after each agent (for single-agent pipelines)
                if cancel_event.is_set():
                    raise WorkflowCancelledError("Pipeline was cancelled.")

            return result or _empty_response()

        loop_handle: RunHandle[str] | None = None

        task_obj: asyncio.Task[Response[str]] = asyncio.get_event_loop().create_task(_run())

        from syrin.workflow._lifecycle import RunHandle  # noqa: PLC0415, F811

        handle: RunHandle[str] = RunHandle(
            task=task_obj,
            run_id=run_id,
            pause_event=pause_event,
            resume_event=resume_event,
            cancel_event=cancel_event,
            pause_mode_ref=[],
        )
        loop_handle = handle
        self._pipeline_handle = handle

        def _on_done(fut: asyncio.Future[Response[str]]) -> None:
            from syrin.enums import WorkflowStatus as _WS  # noqa: PLC0415
            from syrin.workflow.exceptions import WorkflowCancelledError as _WCE  # noqa: PLC0415

            try:
                exc = fut.exception()
            except (asyncio.CancelledError, Exception):
                handle._mark_cancelled()
                return
            if exc is not None:
                if isinstance(exc, _WCE):
                    handle._mark_cancelled()
                else:
                    handle._mark_failed()
            elif handle.status != _WS.CANCELLED:
                handle._mark_completed()

        task_obj.add_done_callback(_on_done)
        return handle

    async def pause(self) -> None:
        """Request the pipeline to pause after the current agent completes.

        Raises:
            RuntimeError: If no pipeline run is in progress.
        """
        if not hasattr(self, "_pipeline_pause_event"):
            raise RuntimeError("No pipeline run in progress. Call play() first.")
        self._pipeline_pause_event.set()

    async def resume(self) -> None:
        """Resume a paused pipeline.

        Raises:
            RuntimeError: If no pipeline run is in progress.
            WorkflowCancelledError: If the pipeline was cancelled.
        """
        from syrin.workflow.exceptions import WorkflowCancelledError  # noqa: PLC0415

        if not hasattr(self, "_pipeline_cancel_event"):
            raise RuntimeError("No pipeline run in progress.")
        if self._pipeline_cancel_event.is_set():
            raise WorkflowCancelledError("Cannot resume a cancelled pipeline.")
        handle = getattr(self, "_pipeline_handle", None)
        if handle is not None:
            from syrin.enums import WorkflowStatus  # noqa: PLC0415

            if handle.status == WorkflowStatus.CANCELLED:
                raise WorkflowCancelledError("Cannot resume a cancelled pipeline.")
        self._pipeline_pause_event.clear()
        self._pipeline_resume_event.set()

    async def cancel(self) -> None:
        """Cancel the running pipeline.

        Subsequent calls to :meth:`resume` will raise
        :class:`~syrin.workflow.exceptions.WorkflowCancelledError`.

        Raises:
            RuntimeError: If no pipeline run is in progress.
        """
        if not hasattr(self, "_pipeline_cancel_event"):
            return  # Nothing to cancel
        self._pipeline_cancel_event.set()
        self._pipeline_pause_event.clear()
        self._pipeline_resume_event.set()  # unblock any waiting resume

    def visualize(self) -> None:
        """Print a rich agent chain for this pipeline to stdout.

        Renders the pipeline's pre-configured agents (if any) as a left-to-right
        chain: ``Agent1 → Agent2 → Agent3``.  When no agents are pre-configured
        the pipeline simply says so.

        Example::

            pipeline.visualize()
            # Pipeline: ResearchAgent → WriterAgent → EditorAgent
        """
        try:
            from rich import print as rprint  # noqa: PLC0415

            agents = self._agents or []
            if not agents:
                rprint("[bold cyan]Pipeline[/bold cyan] — [dim]no agents configured[/dim]")
                return

            parts: list[str] = []
            for item in agents:
                if isinstance(item, tuple):
                    agent_class, _ = item
                else:
                    agent_class = item
                parts.append(f"[green]{agent_class.__name__}[/green]")

            chain = " [bold]→[/bold] ".join(parts)
            rprint(f"[bold cyan]Pipeline[/bold cyan]: {chain}")

        except ImportError:
            agents = self._agents or []
            if not agents:
                print("Pipeline — no agents configured")
                return
            parts_plain: list[str] = []
            for item in agents:
                if isinstance(item, tuple):
                    agent_class_plain, _ = item
                else:
                    agent_class_plain = item
                parts_plain.append(agent_class_plain.__name__)
            print("Pipeline: " + " → ".join(parts_plain))

    async def _arun_for_trigger(self, input: str) -> object:  # noqa: A002
        """Run the pipeline with a trigger input string.

        Args:
            input: Task string from the trigger.

        Returns:
            Response object from sequential execution.
        """
        agents = self._agents or []
        if not agents:
            raise RuntimeError(
                "pipeline.watch() requires agents to be pre-configured. "
                "Pass agents=[MyAgent, ...] to Pipeline() constructor."
            )
        return await self.run_sequential_async(
            [(cls, input) if isinstance(cls, type) else cls for cls in agents]
        )


async def parallel(
    agents: list[tuple[Agent, str]],
) -> list[Response[str]]:
    """Run multiple agent tasks in parallel.

    Args:
        agents: List of ``(agent, task)`` tuples.

    Returns:
        List of responses, one per agent.

    Example::

        results = await parallel([
            (researcher, "Find AI trends"),
            (analyst, "Analyse findings"),
        ])
    """

    async def _run_one(agent: Agent, task: str) -> Response[str]:
        return await agent.arun(task)

    task_coroutines = [_run_one(agent, task) for agent, task in agents]
    return await asyncio.gather(*task_coroutines)


def sequential(
    agents: list[tuple[Agent, str]],
    pass_previous: bool = True,
) -> Response[str]:
    """Run multiple agent tasks sequentially.

    Args:
        agents: List of ``(agent, task)`` tuples.
        pass_previous: Whether to append the previous agent's output as context
            to the next agent's task. Defaults to ``True``.

    Returns:
        Response from the last agent.

    Example::

        result = sequential([
            (researcher, "Find AI trends"),
            (writer, "Write a report"),
        ])
        print(result.content)
    """
    if not agents:
        return _empty_response()

    result: Response[str] | None = None
    for agent, task in agents:
        if pass_previous and result and result.content:
            full_task = f"{task}\n\nPrevious results:\n{result.content}"
        else:
            full_task = task
        result = agent.run(full_task)

    return result or _empty_response()


def _empty_response(model: str = "") -> Response[str]:
    """Return an empty Response with zero cost/tokens.

    Args:
        model: Optional model identifier to embed in the response.

    Returns:
        An empty :class:`~syrin.response.Response`.
    """
    return Response(
        content="",
        raw="",
        cost=0.0,
        tokens=TokenUsage(),
        model=model,
        stop_reason=StopReason.END_TURN,
        trace=[],
    )


__all__ = [
    "Pipeline",
    "PipelineBuilder",
    "PipelineRun",
    "parallel",
    "sequential",
]
