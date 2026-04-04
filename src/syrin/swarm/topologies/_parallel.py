"""PARALLEL topology — all agents run concurrently, results merged."""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING

from syrin.enums import AgentStatus, FallbackStrategy, Hook

if TYPE_CHECKING:
    from syrin.agent._core import Agent
    from syrin.budget._pool import BudgetPool
    from syrin.response import Response
    from syrin.swarm._core import Swarm
    from syrin.swarm._result import SwarmResult


def _compute_was_within_p95(total_spent: float, budget: object) -> bool | None:
    """Return True if total_spent ≤ p95 estimate, False if over, None if unknown.

    Uses the BudgetStore history when available; falls back to 95% of max_cost.
    """
    if budget is None:
        return None
    # Try history-based p95 first
    try:
        store = getattr(budget, "_store", None) or getattr(budget, "store", None)
        if store is not None:
            stats = store.stats()
            p95 = getattr(stats, "p95_cost", 0.0)
            if isinstance(p95, (int, float)) and p95 > 0:
                return total_spent <= p95
    except Exception:
        pass
    # Fall back to 95% of max_cost as proxy p95
    max_cost = getattr(budget, "max_cost", None)
    if max_cost and isinstance(max_cost, (int, float)) and max_cost > 0:
        return bool(total_spent <= max_cost * 0.95)
    return None


async def run_parallel(swarm: Swarm) -> SwarmResult:
    """Execute all swarm agents concurrently and merge results.

    All agents receive the same *goal* string and run in parallel.
    Failed agents are handled according to :attr:`~syrin.swarm._config.SwarmConfig.on_agent_failure`.

    Args:
        swarm: The :class:`~syrin.swarm.Swarm` to execute.

    Returns:
        :class:`~syrin.swarm._result.SwarmResult` with merged content and budget report.

    Raises:
        Exception: If any agent fails and ``on_agent_failure`` is
            :attr:`~syrin.enums.FallbackStrategy.ABORT_SWARM`.
    """
    from syrin.budget.exceptions import BudgetAllocationError
    from syrin.swarm._result import AgentBudgetSummary, SwarmBudgetReport, SwarmResult

    config = swarm.config
    pool: BudgetPool | None = None

    # Wire up shared pool if budget has max_cost
    if swarm.budget is not None and swarm.budget.max_cost is not None:
        from syrin.budget._pool import BudgetPool

        pool = BudgetPool(total=swarm.budget.max_cost)

    # ── SWARM_STARTED ─────────────────────────────────────────────────────────
    swarm._fire_event(
        Hook.SWARM_STARTED,
        {"goal": swarm.goal, "agent_count": swarm.agent_count, "topology": "parallel"},
    )

    # Track per-agent spend for the budget report
    agent_budgets: dict[str, tuple[float, float]] = {}  # name → (allocated, spent)

    async def run_one(agent: Agent) -> tuple[str, Response[str] | None]:
        """Run a single agent, honouring pool allocation and failure strategy."""
        name = type(agent).__name__
        swarm._set_agent_status(name, AgentStatus.RUNNING)
        swarm._fire_event(Hook.AGENT_JOINED_SWARM, {"agent_name": name})

        # ── Budget allocation ────────────────────────────────────────────────
        # Cost is tracked in agent_budgets afterward; no per-agent pre-allocation.
        alloc_amount = 0.0
        pool_allocated = False

        # ── Inject swarm context for spawn() support ─────────────────────────
        from syrin.swarm._registry import SwarmContext

        ctx = SwarmContext(goal=swarm.goal, pool=pool, config=config, swarm_id=swarm._run_id)
        try:
            object.__setattr__(agent, "_swarm_context", ctx)
        except TypeError:
            # Some metaclasses (e.g. _AgentMeta) block object.__setattr__ on
            # the class itself.  Fall back to a plain setattr on the instance.
            with contextlib.suppress(Exception):  # noqa: BLE001
                agent._swarm_context = ctx  # type: ignore[attr-defined]

        try:
            if config.agent_timeout is not None:
                response = await asyncio.wait_for(
                    agent.arun(swarm.goal), timeout=config.agent_timeout
                )
            else:
                response = await agent.arun(swarm.goal)

            actual_cost = getattr(response, "cost", 0.0) or 0.0
            if pool is not None and pool_allocated:
                await pool.spend(name, actual_cost)
                await pool.return_unused(name)

            agent_budgets[name] = (alloc_amount, actual_cost)
            swarm._set_agent_status(name, AgentStatus.STOPPED)
            swarm._fire_event(
                Hook.AGENT_LEFT_SWARM,
                {"agent_name": name, "cost": actual_cost},
            )
            return (name, response)

        except asyncio.CancelledError:
            # Agent was explicitly cancelled via cancel_agent()
            swarm._set_agent_status(name, AgentStatus.KILLED)
            if pool is not None and pool_allocated:
                await pool.return_unused(name)
            return (name, None)

        except BudgetAllocationError:
            # Budget constraint violations are hard errors — always propagate.
            swarm._set_agent_status(name, AgentStatus.FAILED)
            if pool is not None and pool_allocated:
                await pool.return_unused(name)
            raise

        except Exception as exc:
            swarm._set_agent_status(name, AgentStatus.FAILED)
            swarm._fire_event(
                Hook.AGENT_FAILED,
                {"agent_name": name, "error": str(exc), "exception": exc},
            )
            if pool is not None and pool_allocated:
                await pool.return_unused(name)
            swarm._fire_event(
                Hook.BLAST_RADIUS_COMPUTED,
                {"agent_name": name, "error": str(exc), "affected_agents": []},
            )

            if config.on_agent_failure == FallbackStrategy.ABORT_SWARM:
                raise

            return (name, None)

    # ── Create individual tasks so cancel_agent() can cancel specific ones ───
    agent_tasks: dict[str, asyncio.Task[tuple[str, Response[str] | None]]] = {}
    for agent in swarm._agents:
        name = type(agent).__name__
        task: asyncio.Task[tuple[str, Response[str] | None]] = asyncio.create_task(run_one(agent))
        agent_tasks[name] = task

    # Expose tasks on the swarm for cancel_agent() support
    swarm._agent_tasks.update(agent_tasks)

    raw = await asyncio.gather(*agent_tasks.values(), return_exceptions=True)

    # ── Check for SWARM_BUDGET_LOW ────────────────────────────────────────────
    if pool is not None and pool.remaining < pool.total * 0.2:
        swarm._fire_event(
            Hook.SWARM_BUDGET_LOW,
            {"remaining": pool.remaining, "total": pool.total},
        )

    # ── Process results ───────────────────────────────────────────────────────
    successes: list[Response[str]] = []
    cost_breakdown: dict[str, float] = {}
    had_failures = False
    first_exc: BaseException | None = None

    for item in raw:
        if isinstance(item, BaseException):
            had_failures = True
            if first_exc is None:
                first_exc = item
            # Budget allocation errors are hard constraints — always re-raise.
            if isinstance(item, BudgetAllocationError):
                swarm._fire_event(
                    Hook.SWARM_ENDED,
                    {"goal": swarm.goal, "status": "failed", "total_agents": swarm.agent_count},
                )
                raise item
            if config.on_agent_failure == FallbackStrategy.ABORT_SWARM:
                # Emit SWARM_ENDED before raising
                swarm._fire_event(
                    Hook.SWARM_ENDED,
                    {"goal": swarm.goal, "status": "failed", "total_agents": swarm.agent_count},
                )
                raise item
        else:
            name, resp = item
            if resp is not None:
                successes.append(resp)
                actual = getattr(resp, "cost", 0.0) or 0.0
                cost_breakdown[name] = actual
            else:
                # Agent returned None → failed with SKIP_AND_CONTINUE or was cancelled
                had_failures = True

    # ── Fire SWARM_PARTIAL_RESULT if some failed, some succeeded ─────────────
    if had_failures and successes:
        swarm._fire_event(
            Hook.SWARM_PARTIAL_RESULT,
            {"succeeded": len(successes), "total": swarm.agent_count},
        )

    # ── Build SwarmBudgetReport ───────────────────────────────────────────────
    per_agent_summaries = [
        AgentBudgetSummary(agent_name=n, allocated=alloc, spent=spent)
        for n, (alloc, spent) in agent_budgets.items()
    ]
    # Add agents that had no budget tracking (no pool)
    for name, cost in cost_breakdown.items():
        if name not in agent_budgets:
            per_agent_summaries.append(
                AgentBudgetSummary(agent_name=name, allocated=0.0, spent=cost)
            )

    total_spent = sum(s.spent for s in per_agent_summaries)
    was_within_p95 = _compute_was_within_p95(total_spent, swarm.budget)
    budget_report = SwarmBudgetReport(
        per_agent=per_agent_summaries,
        total_spent=total_spent,
        was_within_p95=was_within_p95,
    )

    merged_content = "\n".join(getattr(r, "content", "") or "" for r in successes)

    # ── SWARM_ENDED ───────────────────────────────────────────────────────────
    swarm._fire_event(
        Hook.SWARM_ENDED,
        {
            "goal": swarm.goal,
            "status": "partial" if had_failures else "success",
            "total_agents": swarm.agent_count,
            "succeeded": len(successes),
            "total_spent": total_spent,
        },
    )

    return SwarmResult(
        content=merged_content,
        cost_breakdown=cost_breakdown,
        agent_results=successes,
        partial_results=successes if had_failures else [],
        budget_report=budget_report if (pool is not None or successes) else None,
    )


__all__ = ["run_parallel"]
