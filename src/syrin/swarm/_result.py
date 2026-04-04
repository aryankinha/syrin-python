"""SwarmResult and supporting types for completed swarm runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from syrin.enums import AgentStatus

if TYPE_CHECKING:
    from syrin.response import Response


@dataclass
class AgentBudgetSummary:
    """Budget summary for a single agent in the swarm.

    Attributes:
        agent_name: The agent's class name.
        allocated: Amount allocated from the shared pool (USD).
        spent: Actual amount spent (USD).
    """

    agent_name: str
    allocated: float
    spent: float


@dataclass
class SwarmBudgetReport:
    """Aggregate budget report for a completed swarm run.

    Attributes:
        per_agent: Per-agent budget summaries.
        total_spent: Sum of all agent costs (USD).
        was_within_p95: ``True`` when ``total_spent <= p95_estimate``.
            ``None`` when no p95 estimate is available (no history or
            estimation not configured).

    Example::

        report = result.budget_report
        print(f"Total cost: ${report.total_spent:.4f}")
        for entry in report.per_agent:
            print(f"  {entry.agent_name}: ${entry.spent:.4f}")
        if report.was_within_p95 is not None:
            print(f"Within p95: {report.was_within_p95}")
    """

    per_agent: list[AgentBudgetSummary]
    total_spent: float
    was_within_p95: bool | None = None


@dataclass
class AgentStatusEntry:
    """Status snapshot for a single agent in the swarm.

    Attributes:
        agent_name: The agent's class name.
        state: Current :class:`~syrin.enums.AgentStatus`.
    """

    agent_name: str
    state: AgentStatus


class SwarmResult:
    """Result of a completed :class:`~syrin.swarm.Swarm` run.

    Attributes:
        content: Consolidated output from all successful agents, joined with
            newlines.
        cost_breakdown: Per-agent cost mapping (``agent_name → USD``).
        agent_results: Individual :class:`~syrin.response.Response` objects
            from each agent that completed successfully.
        partial_results: Responses from agents that succeeded when others
            failed (SKIP_AND_CONTINUE / ISOLATE_AND_CONTINUE).
        budget_report: Aggregated budget report, or ``None`` when no shared
            budget was configured.
        consensus_result: Result of a CONSENSUS topology run, or ``None``
            for other topologies.
        reflection_result: Result of a REFLECTION topology run, or ``None``
            for other topologies.

    Example::

        result = await swarm.run()
        print(result.content)
        print(f"Total cost: ${sum(result.cost_breakdown.values()):.4f}")
    """

    def __init__(
        self,
        content: str = "",
        cost_breakdown: dict[str, float] | None = None,
        agent_results: list[Response[str]] | None = None,
        partial_results: list[Response[str]] | None = None,
        budget_report: SwarmBudgetReport | None = None,
        consensus_result: object | None = None,
        reflection_result: object | None = None,
    ) -> None:
        """Initialise SwarmResult.

        Args:
            content: Consolidated content from all successful agents.
            cost_breakdown: Per-agent cost mapping.
            agent_results: Successful agent responses.
            partial_results: Responses from agents that succeeded when
                the swarm had partial failures.
            budget_report: Aggregated budget report (set when a shared
                budget was configured).
            consensus_result: :class:`~syrin.swarm.topologies._consensus.ConsensusResult`
                when topology is CONSENSUS, else ``None``.
            reflection_result: :class:`~syrin.swarm.topologies._reflection.ReflectionResult`
                when topology is REFLECTION, else ``None``.
        """
        self.content: str = content
        self.cost_breakdown: dict[str, float] = cost_breakdown or {}
        self.agent_results: list[object] = list(agent_results) if agent_results else []
        self.partial_results: list[object] = list(partial_results) if partial_results else []
        self.budget_report: SwarmBudgetReport | None = budget_report
        self.consensus_result: object | None = consensus_result
        self.reflection_result: object | None = reflection_result


__all__ = [
    "AgentBudgetSummary",
    "AgentStatusEntry",
    "SwarmBudgetReport",
    "SwarmResult",
]
