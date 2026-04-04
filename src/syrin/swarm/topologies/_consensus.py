"""CONSENSUS topology — multiple agents vote, winner determined by ConsensusStrategy."""

from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from syrin.enums import AgentStatus, ConsensusStrategy, FallbackStrategy, Hook

if TYPE_CHECKING:
    from syrin.agent._core import Agent
    from syrin.response import Response
    from syrin.swarm._core import Swarm
    from syrin.swarm._result import SwarmResult


@dataclass
class ConsensusVote:
    """A single agent's vote in the consensus process.

    Attributes:
        agent_name: The voting agent's class name.
        answer: The agent's answer/output content.
        weight: The agent's vote weight (default 1.0 for MAJORITY/UNANIMITY).
    """

    agent_name: str
    answer: str
    weight: float = 1.0


@dataclass
class ConsensusConfig:
    """Configuration for the CONSENSUS topology.

    Attributes:
        strategy: How to determine the winning answer.
        min_agreement: Minimum fraction of agents that must agree (0.0–1.0).
            Applies to MAJORITY and WEIGHTED strategies. The winning answer's
            fraction must be *strictly greater than* this value.

    Example::

        cfg = ConsensusConfig(
            strategy=ConsensusStrategy.MAJORITY,
            min_agreement=0.60,
        )
    """

    strategy: ConsensusStrategy = ConsensusStrategy.MAJORITY
    min_agreement: float = 0.5  # fraction must be > this to win


@dataclass
class ConsensusResult:
    """Result of a CONSENSUS topology swarm run.

    Attributes:
        consensus_reached: True if a consensus was achieved.
        content: The winning answer (empty string if no consensus).
        votes: Each agent's individual vote, one per successful agent.
        winning_answer: Convenience alias for *content*.
        agreement_fraction: Fraction of votes (or weighted fraction) for the
            winning answer.  0.0 if no consensus was reached.
    """

    consensus_reached: bool
    content: str
    votes: list[ConsensusVote]
    winning_answer: str
    agreement_fraction: float


def _determine_consensus(
    votes: list[ConsensusVote],
    config: ConsensusConfig,
) -> tuple[bool, str, float]:
    """Evaluate *votes* against *config* and return ``(reached, answer, fraction)``.

    Args:
        votes: Non-empty list of :class:`ConsensusVote` objects.
        config: The :class:`ConsensusConfig` governing evaluation.

    Returns:
        A tuple of:
        - *reached*: whether consensus was achieved,
        - *answer*: the winning answer string (or "" if not reached),
        - *fraction*: the agreement fraction of the winner.
    """
    if not votes:
        return False, "", 0.0

    strategy = config.strategy

    if strategy == ConsensusStrategy.UNANIMITY:
        answers = {v.answer for v in votes}
        if len(answers) == 1:
            answer = votes[0].answer
            return True, answer, 1.0
        return False, "", 0.0

    if strategy == ConsensusStrategy.WEIGHTED:
        # Sum weights per answer
        weight_map: dict[str, float] = {}
        for vote in votes:
            weight_map[vote.answer] = weight_map.get(vote.answer, 0.0) + vote.weight
        total_weight = sum(weight_map.values())
        if total_weight == 0.0:
            return False, "", 0.0
        best_answer = max(weight_map, key=lambda k: weight_map[k])
        fraction = weight_map[best_answer] / total_weight
        reached = fraction > config.min_agreement
        return reached, best_answer if reached else "", fraction if reached else 0.0

    # MAJORITY (default)
    total = len(votes)
    counts: Counter[str] = Counter(v.answer for v in votes)
    best_answer, best_count = counts.most_common(1)[0]
    fraction = best_count / total
    reached = fraction > config.min_agreement
    return reached, best_answer if reached else "", fraction if reached else 0.0


async def run_consensus(swarm: Swarm, config: ConsensusConfig | None = None) -> SwarmResult:
    """Execute all swarm agents concurrently and determine a consensus answer.

    All agents receive the same *goal* string independently, then their
    answers are evaluated according to *config*.  Failed agents are excluded
    from the vote per :attr:`~syrin.swarm._config.SwarmConfig.on_agent_failure`.

    Args:
        swarm: The :class:`~syrin.swarm.Swarm` to execute.
        config: Optional :class:`ConsensusConfig`; defaults to MAJORITY with
            ``min_agreement=0.5``.

    Returns:
        :class:`~syrin.swarm._result.SwarmResult` with ``consensus_result``
        populated.

    Raises:
        Exception: If any agent fails and ``on_agent_failure`` is
            :attr:`~syrin.enums.FallbackStrategy.ABORT_SWARM`.
    """
    from syrin.budget._pool import BudgetPool
    from syrin.budget.exceptions import BudgetAllocationError
    from syrin.swarm._result import AgentBudgetSummary, SwarmBudgetReport, SwarmResult

    cfg = config or ConsensusConfig()
    swarm_config = swarm.config
    pool: BudgetPool | None = None

    if swarm.budget is not None and swarm.budget.max_cost is not None:
        pool = BudgetPool(total=swarm.budget.max_cost)

    # ── SWARM_STARTED ─────────────────────────────────────────────────────────
    swarm._fire_event(
        Hook.SWARM_STARTED,
        {"goal": swarm.goal, "agent_count": swarm.agent_count, "topology": "consensus"},
    )

    agent_budgets: dict[str, tuple[float, float]] = {}  # name → (allocated, spent)

    async def run_one(agent: Agent, name: str) -> tuple[str, Response[str] | None]:
        """Run a single agent and return ``(name, response_or_None)``."""
        swarm._set_agent_status(name, AgentStatus.RUNNING)
        swarm._fire_event(Hook.AGENT_JOINED_SWARM, {"agent_name": name})

        # ── Budget allocation ────────────────────────────────────────────────
        # Cost is tracked in agent_budgets afterward; no per-agent pre-allocation.
        alloc_amount = 0.0
        pool_allocated = False

        # ── Inject swarm context ─────────────────────────────────────────────
        from syrin.swarm._registry import SwarmContext

        ctx = SwarmContext(goal=swarm.goal, pool=pool, config=swarm_config, swarm_id=swarm._run_id)
        object.__setattr__(agent, "_swarm_context", ctx)

        try:
            if swarm_config.agent_timeout is not None:
                response = await asyncio.wait_for(
                    agent.arun(swarm.goal), timeout=swarm_config.agent_timeout
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
            swarm._set_agent_status(name, AgentStatus.KILLED)
            if pool is not None and pool_allocated:
                await pool.return_unused(name)
            return (name, None)

        except BudgetAllocationError:
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

            if swarm_config.on_agent_failure == FallbackStrategy.ABORT_SWARM:
                raise

            return (name, None)

    # ── Create tasks and gather ───────────────────────────────────────────────
    # Handle duplicate agent class names by appending index suffix so each
    # agent gets a unique tracking key.  Track weight per unique name.
    agent_tasks: dict[str, asyncio.Task[tuple[str, Response[str] | None]]] = {}
    agent_weights: dict[str, float] = {}
    name_counter: dict[str, int] = {}
    for agent in swarm._agents:
        base_name = type(agent).__name__
        count = name_counter.get(base_name, 0)
        name_counter[base_name] = count + 1
        unique_name = base_name if count == 0 else f"{base_name}_{count}"
        agent_weights[unique_name] = float(getattr(agent, "weight", 1.0))
        task: asyncio.Task[tuple[str, Response[str] | None]] = asyncio.create_task(
            run_one(agent, unique_name)
        )
        agent_tasks[unique_name] = task

    swarm._agent_tasks.update(agent_tasks)

    raw = await asyncio.gather(*agent_tasks.values(), return_exceptions=True)

    # ── Process results ───────────────────────────────────────────────────────
    votes: list[ConsensusVote] = []
    cost_breakdown: dict[str, float] = {}
    first_exc: BaseException | None = None

    for item in raw:
        if isinstance(item, BaseException):
            if first_exc is None:
                first_exc = item
            if isinstance(item, BudgetAllocationError):
                swarm._fire_event(
                    Hook.SWARM_ENDED,
                    {"goal": swarm.goal, "status": "failed", "consensus_reached": False},
                )
                raise item
            if swarm_config.on_agent_failure == FallbackStrategy.ABORT_SWARM:
                swarm._fire_event(
                    Hook.SWARM_ENDED,
                    {"goal": swarm.goal, "status": "failed", "consensus_reached": False},
                )
                raise item
        else:
            name, resp = item
            if resp is not None:
                answer = getattr(resp, "content", "") or ""
                actual = getattr(resp, "cost", 0.0) or 0.0
                weight = agent_weights.get(name, 1.0)
                votes.append(ConsensusVote(agent_name=name, answer=answer, weight=weight))
                cost_breakdown[name] = actual
            else:
                pass

    # ── Determine consensus ───────────────────────────────────────────────────
    reached, winning_answer, agreement_fraction = _determine_consensus(votes, cfg)

    consensus_result = ConsensusResult(
        consensus_reached=reached,
        content=winning_answer,
        votes=votes,
        winning_answer=winning_answer,
        agreement_fraction=agreement_fraction,
    )

    # ── Build budget report ───────────────────────────────────────────────────
    per_agent_summaries = [
        AgentBudgetSummary(agent_name=n, allocated=alloc, spent=spent)
        for n, (alloc, spent) in agent_budgets.items()
    ]
    for name, cost in cost_breakdown.items():
        if name not in agent_budgets:
            per_agent_summaries.append(
                AgentBudgetSummary(agent_name=name, allocated=0.0, spent=cost)
            )

    total_spent = sum(s.spent for s in per_agent_summaries)
    budget_report = SwarmBudgetReport(per_agent=per_agent_summaries, total_spent=total_spent)

    # ── SWARM_ENDED ───────────────────────────────────────────────────────────
    swarm._fire_event(
        Hook.SWARM_ENDED,
        {
            "goal": swarm.goal,
            "status": "success" if reached else "no_consensus",
            "consensus_reached": reached,
            "winning_answer": winning_answer,
            "total_agents": swarm.agent_count,
            "total_spent": total_spent,
        },
    )

    return SwarmResult(
        content=winning_answer,
        cost_breakdown=cost_breakdown,
        agent_results=[],
        partial_results=[],
        budget_report=budget_report if (pool is not None or votes) else None,
        consensus_result=consensus_result,
    )


__all__ = [
    "ConsensusConfig",
    "ConsensusResult",
    "ConsensusVote",
    "run_consensus",
]
