"""WorkflowStep — sealed union of the four step types.

A :class:`WorkflowStep` is an immutable value object that describes a single
node in the workflow execution graph.  The four concrete types are:

- :class:`SequentialStep` — run one agent
- :class:`ParallelStep` — run multiple agents concurrently
- :class:`BranchStep` — run one of two agents based on a predicate
- :class:`DynamicStep` — run N agents determined at runtime by a lambda

The union alias ``WorkflowStep`` enables exhaustive ``match`` dispatch::

    match step:
        case SequentialStep():  ...
        case ParallelStep():    ...
        case BranchStep():      ...
        case DynamicStep():     ...
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from syrin.agent._core import Agent
    from syrin.budget import Budget
    from syrin.workflow._context import HandoffContext


@dataclass(frozen=True)
class SequentialStep:
    """Run exactly one agent as a pipeline step.

    Attributes:
        agent_class: Agent class to instantiate and run.
        task: Optional task override.  When set the agent receives this string
            instead of ``HandoffContext.content``.
        budget: Optional per-step budget override.  Takes precedence over the
            workflow-level budget.

    Example::

        step = SequentialStep(agent_class=PlannerAgent, task="Plan the research")
    """

    agent_class: type[Agent]
    """Agent class to instantiate and run."""

    task: str | None = None
    """Optional task override for this step."""

    budget: Budget | None = None
    """Optional per-step budget override."""


@dataclass(frozen=True)
class ParallelStep:
    """Run multiple agents concurrently and merge their outputs.

    Attributes:
        agent_classes: Two or more agent classes to run in parallel.
        budget: Optional per-step budget override applied to all agents.

    Raises:
        ValueError: If fewer than two agent classes are provided.

    Example::

        step = ParallelStep(agent_classes=[RedditAgent, HNAgent, ArxivAgent])
    """

    agent_classes: tuple[type[Agent], ...]
    """Agent classes to run concurrently (minimum 2)."""

    budget: Budget | None = None
    """Optional per-step budget override."""

    def __post_init__(self) -> None:
        """Validate that at least two agents are provided."""
        if len(self.agent_classes) < 2:
            raise ValueError(
                f"ParallelStep requires at least 2 agent classes, got {len(self.agent_classes)}."
            )


@dataclass(frozen=True)
class BranchStep:
    """Conditionally execute one of two agents based on a predicate.

    The ``condition`` callable receives the incoming :class:`HandoffContext` and
    returns ``True`` to run ``if_true_class`` or ``False`` to run
    ``if_false_class``.

    Attributes:
        condition: Predicate taking :class:`~syrin.workflow._context.HandoffContext`
            and returning a bool (or truthy/falsy value).
        if_true_class: Agent class to run when the condition is truthy.
        if_false_class: Agent class to run when the condition is falsy.
        budget: Optional per-step budget override.

    Example::

        step = BranchStep(
            condition=lambda ctx: "urgent" in ctx.content.lower(),
            if_true_class=FastAgent,
            if_false_class=ThoroughAgent,
        )
    """

    condition: Callable[[HandoffContext[object]], object]
    """Predicate: ``True`` → ``if_true_class``, ``False`` → ``if_false_class``."""

    if_true_class: type[Agent]
    """Agent class to execute when condition is truthy."""

    if_false_class: type[Agent]
    """Agent class to execute when condition is falsy."""

    budget: Budget | None = None
    """Optional per-step budget override."""


@dataclass(frozen=True)
class DynamicStep:
    """Spawn N agents determined at runtime by a factory lambda.

    The ``fn`` callable receives the incoming :class:`HandoffContext` and
    returns a sequence of ``(agent_class, task, budget_usd)`` tuples.  All
    spawned agents run concurrently.

    Attributes:
        fn: Factory function ``(HandoffContext) → list[tuple[type[Agent], str, float]]``.
        max_agents: Optional upper bound on agents spawned.  Raises
            :class:`~syrin.workflow.exceptions.DynamicFanoutError` when exceeded.

    Raises:
        DynamicFanoutError: If the factory returns zero agents or exceeds
            ``max_agents``.

    Example::

        step = DynamicStep(
            fn=lambda ctx: [
                (ResearchAgent, section, 0.50)
                for section in ctx.data.sections
            ],
            max_agents=10,
        )
    """

    fn: Callable[
        [HandoffContext[object]],
        list[tuple[type[Agent], str, float]],
    ]
    """Factory: ``(HandoffContext) → [(agent_class, task, budget_usd), ...]``."""

    max_agents: int | None = None
    """Maximum agents the factory may spawn.  ``None`` = unlimited."""

    label: str = field(default="dynamic", compare=False)
    """Optional human-readable label shown in visualisations."""


# ──────────────────────────────────────────────────────────────────────────────
# Sealed union — exhaustive match dispatch
# ──────────────────────────────────────────────────────────────────────────────

WorkflowStep: TypeAlias = "SequentialStep | ParallelStep | BranchStep | DynamicStep"
"""Sealed union of the four step kinds.

Use a ``match`` statement for exhaustive dispatch::

    match step:
        case SequentialStep(agent_class=cls):
            ...
        case ParallelStep(agent_classes=classes):
            ...
        case BranchStep(condition=pred, if_true_class=t, if_false_class=f):
            ...
        case DynamicStep(fn=factory, max_agents=cap):
            ...
"""
