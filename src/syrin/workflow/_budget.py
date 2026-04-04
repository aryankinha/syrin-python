"""Budget resolution utilities for the Workflow system.

The :func:`resolve_budget` function implements the cascading budget priority
for workflow steps:

    step budget > swarm budget > workflow budget > unlimited

This is a pure function with no side effects so it can be tested in isolation
and reused anywhere the cascade logic is needed.
"""

from __future__ import annotations

from syrin.budget import Budget


def resolve_budget(
    step: Budget | None = None,
    swarm: Budget | None = None,
    workflow: Budget | None = None,
) -> Budget:
    """Return the effective :class:`~syrin.budget.Budget` for a workflow step.

    Priority order (highest to lowest):

    1. **step** — explicit per-step budget override
    2. **swarm** — swarm-level budget (when workflow runs inside a Swarm)
    3. **workflow** — workflow-level budget
    4. **unlimited** — a :class:`Budget` with no cost cap

    This function is a pure function: it never mutates any of its arguments.

    Args:
        step: Per-step budget override, or ``None`` if not set.
        swarm: Swarm-level budget, or ``None`` if not set.
        workflow: Workflow-level budget, or ``None`` if not set.

    Returns:
        The :class:`Budget` that should be applied to the step.

    Example::

        # Step budget wins
        b = resolve_budget(
            step=Budget(max_cost=0.50),
            swarm=Budget(max_cost=2.00),
            workflow=Budget(max_cost=10.00),
        )
        assert b.max_cost == 0.50

        # Fall through to workflow when step and swarm are absent
        b = resolve_budget(workflow=Budget(max_cost=10.00))
        assert b.max_cost == 10.00

        # Unlimited when nothing is set
        b = resolve_budget()
        assert b.max_cost is None
    """
    if step is not None:
        return step
    if swarm is not None:
        return swarm
    if workflow is not None:
        return workflow
    return Budget()
