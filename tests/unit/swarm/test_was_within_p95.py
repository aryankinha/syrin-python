"""Tests for SwarmBudgetReport.was_within_p95.

Exit criteria: was_within_p95 is True when actual cost ≤ p95 estimate; False otherwise.
"""

from __future__ import annotations

from syrin import Agent, Budget, Model
from syrin.enums import SwarmTopology
from syrin.response import Response
from syrin.swarm import Swarm, SwarmConfig


def _make_agent(content: str, cost: float = 0.01) -> type[Agent]:
    class _Stub(Agent):
        model = Model.Almock()
        system_prompt = "stub"

        async def arun(self, input_text: str) -> Response[str]:
            return Response(content=content, cost=cost)

    _Stub.__name__ = f"Stub_{content[:8]}"
    return _Stub


class TestWasWithinP95:
    """SwarmBudgetReport.was_within_p95 correctness."""

    async def test_within_p95_when_cost_below_95pct_of_max(self) -> None:
        """was_within_p95 is True when agent cost < 95% of max_cost."""
        A = _make_agent("result", cost=0.01)
        swarm = Swarm(
            agents=[A()],
            goal="test p95",
            budget=Budget(max_cost=1.00),  # 95% of 1.00 = 0.95
            config=SwarmConfig(topology=SwarmTopology.PARALLEL),
        )
        result = await swarm.run()
        assert result.budget_report is not None
        # 0.01 <= 0.95
        assert result.budget_report.was_within_p95 is True

    async def test_over_p95_when_cost_exceeds_95pct_of_max(self) -> None:
        """was_within_p95 is False when agent cost > 95% of max_cost."""
        A = _make_agent("result", cost=0.98)
        swarm = Swarm(
            agents=[A()],
            goal="test p95 over",
            budget=Budget(max_cost=1.00),  # 95% of 1.00 = 0.95
            config=SwarmConfig(topology=SwarmTopology.PARALLEL),
        )
        result = await swarm.run()
        assert result.budget_report is not None
        # 0.98 > 0.95
        assert result.budget_report.was_within_p95 is False

    async def test_none_when_no_budget(self) -> None:
        """was_within_p95 is None when no budget is configured."""
        A = _make_agent("result", cost=0.01)
        swarm = Swarm(
            agents=[A()], goal="no budget", config=SwarmConfig(topology=SwarmTopology.PARALLEL)
        )
        result = await swarm.run()
        assert result.budget_report is not None
        assert result.budget_report.was_within_p95 is None
