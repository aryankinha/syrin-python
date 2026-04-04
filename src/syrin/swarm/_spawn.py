"""Swarm spawn primitives: SpawnResult and SpawnSpec.

These types support the ``agent.spawn()`` and ``agent.spawn_many()`` async
methods that allow agents in a swarm to launch child agents while drawing
budget from the shared :class:`~syrin.budget.BudgetPool`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from syrin.enums import StopReason

if TYPE_CHECKING:
    from syrin.agent._core import Agent


@dataclass
class SpawnResult:
    """Result of spawning a child agent from within a swarm.

    Attributes:
        content: The child agent's output text.
        cost: Actual cost incurred by the child (USD).
        budget_remaining: Remaining pool balance after the child completes (USD).
        stop_reason: Why the child agent terminated.
        child_agent_id: Identifier for the spawned child (``parent::child`` format).

    Example::

        result = await self.spawn(ResearchAgent, task="Find papers", budget=1.00)
        print(result.content)
        print(f"Spent: ${result.cost:.4f}, remaining: ${result.budget_remaining:.4f}")
    """

    content: str
    cost: float
    budget_remaining: float
    stop_reason: StopReason
    child_agent_id: str


@dataclass
class SpawnSpec:
    """Specification for spawning one agent within :meth:`~syrin.agent._core.Agent.spawn_many`.

    Attributes:
        agent: Agent class to instantiate.
        task: Task string passed to the child agent.
        budget: Budget to allocate for this child (USD).
        timeout: Per-child timeout in seconds.  ``None`` means no limit.

    Example::

        specs = [
            SpawnSpec(agent=ResearchAgent, task="Find papers on X", budget=0.50),
            SpawnSpec(agent=SummaryAgent,  task="Summarise findings",  budget=0.25),
        ]
        results = await self.spawn_many(specs)
    """

    agent: type[Agent]
    task: str
    budget: float
    timeout: float | None = None


async def _spawn_from_pool(
    parent_name: str,
    agent_class: type[Agent],
    task: str,
    budget_amount: float,
    pool: object,  # BudgetPool — imported lazily to avoid circular
    timeout: float | None = None,
    child_id: str | None = None,
) -> SpawnResult:
    """Allocate *budget_amount* from *pool*, run *agent_class*, and return a SpawnResult.

    Args:
        parent_name: Name of the spawning agent (used in child ID).
        agent_class: Agent class to instantiate and run.
        task: Task passed to the child agent.
        budget_amount: Amount to allocate from the pool.
        pool: :class:`~syrin.budget.BudgetPool` shared pool.
        timeout: Optional per-child timeout.
        child_id: Explicit child ID; auto-generated (unique) if not provided.

    Raises:
        BudgetAllocationError: If the pool cannot satisfy the allocation.
        Exception: Any exception raised by the child agent's ``arun``.
    """
    import asyncio
    import uuid

    from syrin.budget._pool import BudgetPool

    p: BudgetPool = pool  # type: ignore[assignment]
    if child_id is None:
        child_id = f"{parent_name}::{agent_class.__name__}::{uuid.uuid4().hex[:8]}"

    await p.allocate(child_id, budget_amount)
    try:
        child = agent_class()
        if timeout is not None:
            response = await asyncio.wait_for(child.arun(task), timeout=timeout)
        else:
            response = await child.arun(task)
        await p.spend(child_id, response.cost)
        remaining = p.remaining
        await p.return_unused(child_id)
        return SpawnResult(
            content=response.content,
            cost=response.cost,
            budget_remaining=remaining,
            stop_reason=StopReason.END_TURN,
            child_agent_id=child_id,
        )
    except Exception:
        await p.return_unused(child_id)
        raise


__all__ = ["SpawnResult", "SpawnSpec"]
