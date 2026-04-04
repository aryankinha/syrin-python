"""HandoffContext — typed, immutable context passed between workflow steps.

Each step receives a :class:`HandoffContext` containing the previous step's
output, accumulated history, budget remaining, and metadata about the current
position in the workflow.  The dataclass is frozen so steps cannot accidentally
mutate shared state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class HandoffContext(Generic[T]):
    """Immutable context passed from one workflow step to the next.

    Each step receives a ``HandoffContext`` and produces a new one for the next
    step.  All fields are read-only after construction (``frozen=True``).

    Attributes:
        content: String output of the previous step.  Always a ``str``, never
            ``None``.  For the first step this is the workflow's initial input.
        data: Typed structured output from the previous step when that step's
            agent has an ``output_type``.  ``None`` when the previous step
            produced only plain text.
        history: Oldest-first list of ``content`` strings from every completed
            step.  Empty for the first step.
        budget_remaining: Remaining budget (in USD) for the whole workflow at
            this point.  ``0.0`` when no budget is configured.
        step_index: Zero-based index of the *current* (about-to-run) step.
        workflow_name: Name of the workflow this context belongs to.
        run_id: Unique identifier for this ``play()`` / ``run()`` invocation.

    Example::

        ctx = HandoffContext(
            content="Plan complete",
            data=my_plan,
            history=["user input"],
            budget_remaining=4.50,
            step_index=1,
            workflow_name="research-pipeline",
            run_id="run-abc123",
        )
        assert ctx.content == "Plan complete"
        assert ctx.step_index == 1
    """

    content: str
    """String output of the previous step (never ``None``)."""

    data: T | None = None
    """Typed structured output from the previous step, or ``None``."""

    history: tuple[str, ...] = field(default_factory=tuple)
    """Oldest-first tuple of content strings from all completed steps."""

    budget_remaining: float = 0.0
    """Remaining workflow budget in USD at this point in execution."""

    step_index: int = 0
    """Zero-based index of the step that will *receive* this context."""

    workflow_name: str = ""
    """Name of the owning :class:`~syrin.workflow.Workflow`."""

    run_id: str = ""
    """Unique run identifier generated at ``play()`` / ``run()`` time."""

    def evolve(self, **changes: object) -> HandoffContext[T]:
        """Return a new :class:`HandoffContext` with the given fields replaced.

        This is the functional update pattern for frozen dataclasses — instead
        of mutating, you derive a new context for the next step.

        Args:
            **changes: Field overrides.  Only valid
                :class:`HandoffContext` field names are accepted.

        Returns:
            A new :class:`HandoffContext` with the requested fields updated.

        Example::

            next_ctx = ctx.evolve(
                content="Step 2 result",
                history=(*ctx.history, ctx.content),
                step_index=ctx.step_index + 1,
                budget_remaining=3.80,
            )
        """
        from typing import cast  # noqa: PLC0415

        return HandoffContext(
            content=cast(str, changes.get("content", self.content)),
            data=cast("T | None", changes.get("data", self.data)),
            history=cast("tuple[str, ...]", changes.get("history", self.history)),
            budget_remaining=cast(float, changes.get("budget_remaining", self.budget_remaining)),
            step_index=cast(int, changes.get("step_index", self.step_index)),
            workflow_name=cast(str, changes.get("workflow_name", self.workflow_name)),
            run_id=cast(str, changes.get("run_id", self.run_id)),
        )
