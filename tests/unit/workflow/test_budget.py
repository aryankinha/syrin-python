"""P1-T3: Budget resolution tests.

resolve_budget() implements a cascading priority:
    step > swarm > workflow > unlimited (Budget with no cap)

This is a pure function — no side effects, no mutation.
"""

from __future__ import annotations

from syrin import Budget
from syrin.workflow._budget import resolve_budget


class TestResolveBudget:
    """resolve_budget() returns the highest-priority budget."""

    def test_step_wins_over_all(self) -> None:
        """Step budget takes precedence over swarm and workflow."""
        result = resolve_budget(
            step=Budget(max_cost=0.50),
            swarm=Budget(max_cost=2.00),
            workflow=Budget(max_cost=10.00),
        )
        assert result.max_cost == 0.50

    def test_swarm_wins_over_workflow(self) -> None:
        """Swarm budget takes precedence over workflow when step is absent."""
        result = resolve_budget(
            step=None,
            swarm=Budget(max_cost=2.00),
            workflow=Budget(max_cost=10.00),
        )
        assert result.max_cost == 2.00

    def test_workflow_wins_when_only_one(self) -> None:
        """Workflow budget is used when step and swarm are absent."""
        result = resolve_budget(
            step=None,
            swarm=None,
            workflow=Budget(max_cost=10.00),
        )
        assert result.max_cost == 10.00

    def test_unlimited_when_all_none(self) -> None:
        """Returns a Budget with no cap when nothing is configured."""
        result = resolve_budget(step=None, swarm=None, workflow=None)
        assert isinstance(result, Budget)
        assert result.max_cost is None

    def test_unlimited_with_no_args(self) -> None:
        """resolve_budget() with no arguments returns an unlimited Budget."""
        result = resolve_budget()
        assert result.max_cost is None

    def test_pure_function_no_mutation(self) -> None:
        """The original Budget objects are not mutated."""
        step_bgt = Budget(max_cost=0.50)
        swarm_bgt = Budget(max_cost=2.00)
        wf_bgt = Budget(max_cost=10.00)

        resolve_budget(step=step_bgt, swarm=swarm_bgt, workflow=wf_bgt)

        assert step_bgt.max_cost == 0.50
        assert swarm_bgt.max_cost == 2.00
        assert wf_bgt.max_cost == 10.00

    def test_step_with_zero_cost(self) -> None:
        """A step budget of $0 still wins over higher-budget alternatives."""
        result = resolve_budget(
            step=Budget(max_cost=0.0),
            swarm=Budget(max_cost=5.00),
        )
        assert result.max_cost == 0.0

    def test_only_step_provided(self) -> None:
        """Only step budget: returns step budget."""
        result = resolve_budget(step=Budget(max_cost=1.00))
        assert result.max_cost == 1.00

    def test_only_swarm_provided(self) -> None:
        """Only swarm budget: returns swarm budget."""
        result = resolve_budget(swarm=Budget(max_cost=3.00))
        assert result.max_cost == 3.00

    def test_returns_budget_instance(self) -> None:
        """resolve_budget() always returns a Budget instance."""
        result = resolve_budget()
        assert isinstance(result, Budget)

        result2 = resolve_budget(workflow=Budget(max_cost=5.00))
        assert isinstance(result2, Budget)
