"""Serve adapter — converts Pipeline and DynamicPipeline to agent-like interface.

Enables build_router() and AgentRouter to serve pipelines directly without
requiring users to write a wrapper agent.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, cast

from syrin.budget import BudgetState
from syrin.events import EventContext, Events
from syrin.response import Response, StreamChunk
from syrin.types import TokenUsage

if TYPE_CHECKING:
    from syrin.agent import Agent
    from syrin.agent.multi_agent import DynamicPipeline, Pipeline


def to_serveable(obj: Agent | Pipeline | DynamicPipeline) -> Agent:
    """Convert Agent, Pipeline, or DynamicPipeline to a serveable Agent.

    Used internally by build_router() and AgentRouter. Agent is returned as-is.
    Pipeline and DynamicPipeline are wrapped in adapters that implement arun,
    astream, events, budget_state, etc., so they can be served via HTTP/CLI/STDIO.

    Args:
        obj: Agent, Pipeline, or DynamicPipeline to convert.

    Returns:
        Agent-compatible object (same interface as Agent).

    Raises:
        TypeError: If obj is not Agent, Pipeline, or DynamicPipeline.
    """
    from syrin.agent import Agent
    from syrin.agent.multi_agent import DynamicPipeline, Pipeline

    if isinstance(obj, Agent):
        return obj
    if isinstance(obj, DynamicPipeline):
        return cast(Agent, _DynamicPipelineAdapter(obj))
    if isinstance(obj, Pipeline):
        return cast(Agent, _PipelineAdapter(obj))
    raise TypeError(f"Expected Agent, Pipeline, or DynamicPipeline, got {type(obj).__name__}")


def _budget_state_from_budget(budget: object) -> BudgetState | None:
    """Build BudgetState from a Budget object."""
    if budget is None or getattr(budget, "max_cost", None) is None:
        return None
    effective = budget.max_cost - getattr(budget, "reserve", 0)  # type: ignore[attr-defined]
    if effective <= 0:
        effective = budget.max_cost  # type: ignore[attr-defined]
    spent = getattr(budget, "_spent", 0.0)
    remaining = max(0.0, effective - spent)
    percent = (spent / effective * 100.0) if effective > 0 else 0.0
    return BudgetState(
        limit=effective,
        remaining=remaining,
        spent=spent,
        percent_used=round(percent, 2),
    )


class _PipelineAdapter:
    """Internal adapter: Pipeline -> agent-like interface for HTTP serving."""

    def __init__(self, pipeline: Pipeline) -> None:

        self._pipeline = pipeline
        self.name = "pipeline"
        self.description = "Sequential agent pipeline"
        self.tools: list[object] = []
        self._events = Events(lambda _h, _c: None)
        pipeline.events.on_all(lambda h, c: self._forward_event(h, c))

    def _forward_event(self, hook: object, ctx: EventContext) -> None:
        self._events._trigger_before(hook, ctx)  # type: ignore[arg-type]
        self._events._trigger(hook, ctx)  # type: ignore[arg-type]
        self._events._trigger_after(hook, ctx)  # type: ignore[arg-type]

    @property
    def events(self) -> Events:
        return self._events

    @property
    def budget_state(self) -> BudgetState | None:
        return _budget_state_from_budget(getattr(self._pipeline, "_budget", None))

    async def arun(
        self,
        user_input: str,
        context: object = None,
        template_variables: dict[str, object] | None = None,
    ) -> Response[str]:
        del context, template_variables
        agents = getattr(self._pipeline, "_agents", None)
        if not agents:
            return Response(content="Pipeline has no default agents", cost=0, tokens=TokenUsage())
        first_item = agents[0]
        first_class, first_task = (
            (first_item[0], first_item[1]) if isinstance(first_item, tuple) else (first_item, "")
        )
        from syrin.agent import Agent as _AgentType

        run_agents: list[tuple[type[_AgentType], str]] = [
            (first_class, user_input),
        ]
        for item in agents[1:]:
            ac, task = (item[0], item[1]) if isinstance(item, tuple) else (item, "")
            run_agents.append((ac, task or "Process the previous output"))
        result = await asyncio.to_thread(
            self._pipeline.run_sequential,
            cast(list[type[_AgentType] | tuple[type[_AgentType], str]], run_agents),
        )
        return result

    def run(self, user_input: str) -> Response[str]:
        """Sync run for CLI/STDIO. Blocks until complete."""
        return asyncio.run(self.arun(user_input))

    async def astream(
        self,
        user_input: str,
        context: object = None,
        template_variables: dict[str, object] | None = None,
    ) -> object:
        result = await self.arun(user_input, context, template_variables)
        yield StreamChunk(
            index=0,
            text=result.content,
            accumulated_text=result.content,
            cost_so_far=result.cost,
            tokens_so_far=result.tokens or TokenUsage(),
            is_final=True,
            response=result,
        )


class _DynamicPipelineAdapter:
    """Internal adapter: DynamicPipeline -> agent-like interface for HTTP serving."""

    def __init__(self, pipeline: DynamicPipeline) -> None:

        self._pipeline = pipeline
        self.name = "dynamic-pipeline"
        self.description = "Dynamic pipeline — LLM plans which agents to spawn"
        self.internal_agents = list(getattr(pipeline, "_agent_names", {}).keys())
        self.tools: list[object] = []
        self._events = Events(lambda _h, _c: None)
        pipeline.events.on_all(lambda h, c: self._forward_event(h, c))

    def _forward_event(self, hook: object, ctx: EventContext) -> None:
        self._events._trigger_before(hook, ctx)  # type: ignore[arg-type]
        self._events._trigger(hook, ctx)  # type: ignore[arg-type]
        self._events._trigger_after(hook, ctx)  # type: ignore[arg-type]

    @property
    def events(self) -> Events:
        return self._events

    @property
    def budget_state(self) -> BudgetState | None:
        return _budget_state_from_budget(getattr(self._pipeline, "_budget", None))

    async def arun(
        self,
        user_input: str,
        context: object = None,
        template_variables: dict[str, object] | None = None,
    ) -> Response[str]:
        del context, template_variables
        return await asyncio.to_thread(self._pipeline.run, user_input, "parallel")

    def run(self, user_input: str) -> Response[str]:
        """Sync run for CLI/STDIO. Blocks until complete."""
        return asyncio.run(self.arun(user_input))

    async def astream(
        self,
        user_input: str,
        context: object = None,
        template_variables: dict[str, object] | None = None,
    ) -> object:
        del context, template_variables

        # Queue for hooks emitted during pipeline run (enables real-time streaming)
        hook_queue: asyncio.Queue[tuple[str, dict[str, object]]] = asyncio.Queue()

        def on_hook(h: object, c: object) -> None:
            h_val = getattr(h, "value", str(h))
            c_dict: dict[str, object] = dict(c) if hasattr(c, "items") else {}  # type: ignore[call-overload]
            with contextlib.suppress(asyncio.QueueFull):
                hook_queue.put_nowait((h_val, c_dict))

        self._pipeline.events.on_all(on_hook)
        result_container: list[Response[str]] = []

        async def run_pipeline() -> None:
            result_container.append(
                await asyncio.to_thread(self._pipeline.run, user_input, "parallel")
            )

        task = asyncio.create_task(run_pipeline())

        # Yield hooks as they arrive, until pipeline completes
        while not task.done():
            try:
                h, c = await asyncio.wait_for(hook_queue.get(), timeout=0.05)
                chunk = StreamChunk()
                object.__setattr__(chunk, "_hook", (h, c))
                yield chunk
            except asyncio.TimeoutError:
                continue

        # Drain any remaining hooks
        while not hook_queue.empty():
            try:
                h, c = hook_queue.get_nowait()
                chunk = StreamChunk()
                object.__setattr__(chunk, "_hook", (h, c))
                yield chunk
            except asyncio.QueueEmpty:
                break

        result = result_container[0]
        yield StreamChunk(
            index=0,
            text=result.content,
            accumulated_text=result.content,
            cost_so_far=result.cost,
            tokens_so_far=result.tokens or TokenUsage(),
            is_final=True,
            response=result,
        )
