"""REFLECTION topology — producer–critic loop with iterative refinement."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from syrin.enums import AgentStatus, Hook

if TYPE_CHECKING:
    from syrin.swarm._core import Swarm
    from syrin.swarm._result import SwarmResult


@dataclass
class RoundOutput:
    """Output from one producer–critic round.

    Attributes:
        round_index: 0-based round number.
        producer_output: The producer agent's output for this round.
        critic_feedback: The critic's feedback (or "" if not yet evaluated).
        score: The critic's quality score (0.0–1.0). Extracted from critic
            output; defaults to 0.5 if no numeric score is found.
        stop_condition_met: True if the *stop_when* predicate returned True
            for this round.
    """

    round_index: int
    producer_output: str
    critic_feedback: str
    score: float
    stop_condition_met: bool


@dataclass
class ReflectionResult:
    """Result of a REFLECTION topology swarm run.

    Attributes:
        content: The best producer output (from the round where the stop
            condition was met, or the round with the highest score).
        round_outputs: One :class:`RoundOutput` per completed round.
        final_round: 0-based index of the round that produced the final
            result.
        rounds_completed: Total number of rounds executed.
    """

    content: str
    round_outputs: list[RoundOutput]
    final_round: int
    rounds_completed: int


@dataclass
class ReflectionConfig:
    """Configuration for the REFLECTION topology.

    Attributes:
        producer: Agent class that produces/revises output each round.
        critic: Agent class that evaluates the producer's output and
            provides feedback.
        max_rounds: Maximum number of producer–critic cycles (default 3).
        stop_when: Optional callable; receives a :class:`RoundOutput` and
            returns True to stop early.  ``None`` means run all *max_rounds*.
        budget_per_round: Optional per-round budget cap in USD.

    Example::

        cfg = ReflectionConfig(
            producer=WriterAgent,
            critic=CriticAgent,
            max_rounds=5,
            stop_when=lambda ro: ro.score >= 0.9,
        )
    """

    producer: type  # type[Agent] — avoid circular import
    critic: type  # type[Agent]
    max_rounds: int = 3
    stop_when: Callable[[RoundOutput], bool] | None = None
    budget_per_round: float | None = None


_SCORE_PATTERN = re.compile(r"(?:score[:\s]*)?(\d+(?:\.\d+)?)", re.IGNORECASE)


def _extract_score(text: str) -> float:
    """Extract a numeric score in [0, 1] from *text*.

    Searches for a number following a "Score:" prefix first, then any
    stand-alone decimal in the text.  Returns 0.5 if none is found.

    Args:
        text: Critic output string.

    Returns:
        Float in [0.0, 1.0].
    """
    # Prefer match near "Score:" keyword
    score_kw = re.search(r"[Ss]core\s*[:\-]?\s*(\d+(?:\.\d+)?)", text)
    if score_kw:
        val = float(score_kw.group(1))
        return max(0.0, min(1.0, val))

    # Fallback: last decimal in range [0,1]
    candidates = [float(m.group(1)) for m in re.finditer(r"\b(\d+\.\d+)\b", text)]
    candidates = [v for v in candidates if 0.0 <= v <= 1.0]
    if candidates:
        return candidates[-1]

    return 0.5


async def run_reflection(swarm: Swarm, config: ReflectionConfig) -> SwarmResult:
    """Execute a producer–critic loop and return the best result.

    In each round:
    1. The *producer* receives the goal (round 1) or goal + previous
       critic feedback (rounds 2+).
    2. The *critic* receives the producer's output and returns feedback
       with a numeric score.
    3. If *stop_when* is defined and returns ``True``, the loop ends early.
    4. If *max_rounds* is reached, the round with the highest score is
       returned.

    Args:
        swarm: The :class:`~syrin.swarm.Swarm` to execute.
        config: :class:`ReflectionConfig` controlling the loop.

    Returns:
        :class:`~syrin.swarm._result.SwarmResult` with ``reflection_result``
        populated.
    """
    from syrin.swarm._result import AgentBudgetSummary, SwarmBudgetReport, SwarmResult

    # ── SWARM_STARTED ─────────────────────────────────────────────────────────
    swarm._fire_event(
        Hook.SWARM_STARTED,
        {"goal": swarm.goal, "agent_count": swarm.agent_count, "topology": "reflection"},
    )

    round_outputs: list[RoundOutput] = []
    cost_breakdown: dict[str, float] = {}
    critic_feedback = ""

    for round_idx in range(config.max_rounds):
        # ── Build producer input ────────────────────────────────────────────
        if round_idx == 0:
            producer_input = swarm.goal
        else:
            producer_input = f"{swarm.goal}\n\nPrevious feedback:\n{critic_feedback}"

        # ── Instantiate fresh agent objects each round ──────────────────────
        producer_instance = config.producer()
        critic_instance = config.critic()

        producer_name = config.producer.__name__
        critic_name = config.critic.__name__

        # ── Producer ────────────────────────────────────────────────────────
        swarm._set_agent_status(producer_name, AgentStatus.RUNNING)
        swarm._fire_event(
            Hook.AGENT_JOINED_SWARM,
            {"agent_name": producer_name, "round": round_idx},
        )

        try:
            producer_response = await producer_instance.arun(producer_input)
            producer_output = getattr(producer_response, "content", "") or ""
            producer_cost = getattr(producer_response, "cost", 0.0) or 0.0
        except Exception:
            # Budget exhausted or unexpected error — return best so far
            swarm._set_agent_status(producer_name, AgentStatus.FAILED)
            break

        cost_breakdown[f"{producer_name}_r{round_idx}"] = producer_cost
        swarm._set_agent_status(producer_name, AgentStatus.STOPPED)
        swarm._fire_event(
            Hook.AGENT_LEFT_SWARM,
            {"agent_name": producer_name, "round": round_idx, "cost": producer_cost},
        )

        # ── Critic ──────────────────────────────────────────────────────────
        swarm._set_agent_status(critic_name, AgentStatus.RUNNING)
        swarm._fire_event(
            Hook.AGENT_JOINED_SWARM,
            {"agent_name": critic_name, "round": round_idx},
        )

        try:
            critic_response = await critic_instance.arun(producer_output)
            critic_feedback = getattr(critic_response, "content", "") or ""
            critic_cost = getattr(critic_response, "cost", 0.0) or 0.0
        except Exception:
            swarm._set_agent_status(critic_name, AgentStatus.FAILED)
            # Store what we have and exit
            ro = RoundOutput(
                round_index=round_idx,
                producer_output=producer_output,
                critic_feedback="",
                score=0.5,
                stop_condition_met=False,
            )
            round_outputs.append(ro)
            break

        cost_breakdown[f"{critic_name}_r{round_idx}"] = critic_cost
        swarm._set_agent_status(critic_name, AgentStatus.STOPPED)
        swarm._fire_event(
            Hook.AGENT_LEFT_SWARM,
            {"agent_name": critic_name, "round": round_idx, "cost": critic_cost},
        )

        score = _extract_score(critic_feedback)

        stop_met = config.stop_when is not None and config.stop_when(
            RoundOutput(
                round_index=round_idx,
                producer_output=producer_output,
                critic_feedback=critic_feedback,
                score=score,
                stop_condition_met=False,
            )
        )

        ro = RoundOutput(
            round_index=round_idx,
            producer_output=producer_output,
            critic_feedback=critic_feedback,
            score=score,
            stop_condition_met=stop_met,
        )
        round_outputs.append(ro)

        if stop_met:
            break

    # ── Determine best round ──────────────────────────────────────────────────
    if not round_outputs:
        # Nothing completed at all
        reflection_result = ReflectionResult(
            content="",
            round_outputs=[],
            final_round=0,
            rounds_completed=0,
        )
        swarm._fire_event(
            Hook.SWARM_ENDED,
            {"goal": swarm.goal, "status": "failed", "rounds_completed": 0},
        )
        return SwarmResult(
            content="",
            reflection_result=reflection_result,
        )

    # Find round that triggered stop_when, or highest score.
    # On tie, the last (latest) round wins — it incorporates the most feedback.
    stop_round = next((ro for ro in round_outputs if ro.stop_condition_met), None)
    if stop_round is not None:
        best_ro = stop_round
    else:
        best_ro = max(round_outputs, key=lambda ro: (ro.score, ro.round_index))

    reflection_result = ReflectionResult(
        content=best_ro.producer_output,
        round_outputs=round_outputs,
        final_round=best_ro.round_index,
        rounds_completed=len(round_outputs),
    )

    total_spent = sum(cost_breakdown.values())
    per_agent = [
        AgentBudgetSummary(agent_name=n, allocated=0.0, spent=c) for n, c in cost_breakdown.items()
    ]
    budget_report = SwarmBudgetReport(per_agent=per_agent, total_spent=total_spent)

    # ── SWARM_ENDED ───────────────────────────────────────────────────────────
    swarm._fire_event(
        Hook.SWARM_ENDED,
        {
            "goal": swarm.goal,
            "status": "success",
            "rounds_completed": reflection_result.rounds_completed,
            "final_round": reflection_result.final_round,
            "total_spent": total_spent,
        },
    )

    return SwarmResult(
        content=reflection_result.content,
        cost_breakdown=cost_breakdown,
        agent_results=[],
        partial_results=[],
        budget_report=budget_report,
        reflection_result=reflection_result,
    )


__all__ = [
    "ReflectionConfig",
    "ReflectionResult",
    "RoundOutput",
    "run_reflection",
]
