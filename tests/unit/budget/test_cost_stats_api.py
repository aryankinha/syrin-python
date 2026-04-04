"""Tests for wf.cost_stats() and Agent.cost_stats().

Exit criteria:
- wf.cost_stats() returns WorkflowCostStats with per_step CostStats list.
- ResearchAgent.cost_stats() (any agent subclass) returns agent-level CostStats.
"""

from __future__ import annotations

import pytest

from syrin import Agent, Model
from syrin.budget._history import CostStats, _get_default_store
from syrin.workflow import Workflow
from syrin.workflow._core import WorkflowCostStats


def _almock() -> Model:
    return Model.Almock(latency_seconds=0.01, lorem_length=5)


class _StepA(Agent):
    model = _almock()
    system_prompt = "step a"


class _StepB(Agent):
    model = _almock()
    system_prompt = "step b"


class TestAgentCostStats:
    """Agent.cost_stats() classmethod returns CostStats for the agent."""

    def test_returns_cost_stats_instance(self) -> None:
        """Agent.cost_stats() returns a CostStats instance."""
        stats = _StepA.cost_stats()
        assert isinstance(stats, CostStats)

    def test_cost_stats_has_required_fields(self) -> None:
        """CostStats has all required fields."""
        stats = _StepA.cost_stats()
        assert hasattr(stats, "mean")
        assert hasattr(stats, "p50_cost")
        assert hasattr(stats, "p95_cost")
        assert hasattr(stats, "p99_cost")
        assert hasattr(stats, "stddev")
        assert hasattr(stats, "run_count")
        assert hasattr(stats, "trend_weekly_pct")

    def test_cost_stats_reflects_recorded_runs(self) -> None:
        """cost_stats() reflects actual recorded runs."""
        store = _get_default_store()
        store.clear("_StepB")
        try:
            for _ in range(5):
                store.record("_StepB", 0.10)
            stats = _StepB.cost_stats()
            assert stats.run_count == 5
            assert stats.p50_cost == pytest.approx(0.10, abs=0.001)
        finally:
            store.clear("_StepB")

    def test_no_history_returns_zero_run_count(self) -> None:
        """cost_stats() returns run_count=0 when no history is recorded."""

        class _BrandNewAgent(Agent):
            model = _almock()
            system_prompt = "new"

        store = _get_default_store()
        store.clear("_BrandNewAgent")
        stats = _BrandNewAgent.cost_stats()
        assert stats.run_count == 0


class TestWorkflowCostStats:
    """wf.cost_stats() returns WorkflowCostStats with per-step breakdown."""

    def test_returns_workflow_cost_stats_instance(self) -> None:
        """wf.cost_stats() returns a WorkflowCostStats."""
        wf = Workflow("test-cost-stats")
        wf.step(_StepA, task="step a")
        wf.step(_StepB, task="step b")
        stats = wf.cost_stats()
        assert isinstance(stats, WorkflowCostStats)

    def test_per_step_has_one_entry_per_step(self) -> None:
        """per_step list has one CostStats per sequential step."""
        wf = Workflow("per-step-test")
        wf.step(_StepA, task="a")
        wf.step(_StepB, task="b")
        stats = wf.cost_stats()
        assert len(stats.per_step) == 2

    def test_per_step_entries_are_cost_stats(self) -> None:
        """Each per_step entry is a CostStats."""
        wf = Workflow("per-step-type-test")
        wf.step(_StepA, task="a")
        stats = wf.cost_stats()
        assert all(isinstance(s, CostStats) for s in stats.per_step)

    def test_total_mean_and_total_p95_are_floats(self) -> None:
        """WorkflowCostStats.total_mean and total_p95 are floats."""
        wf = Workflow("total-stats-test")
        wf.step(_StepA, task="a")
        wf.step(_StepB, task="b")
        stats = wf.cost_stats()
        assert isinstance(stats.total_mean, float)
        assert isinstance(stats.total_p95, float)

    def test_total_p95_is_sum_of_per_step_p95(self) -> None:
        """total_p95 equals the sum of per-step p95 costs."""
        wf = Workflow("sum-p95-test")
        wf.step(_StepA, task="a")
        wf.step(_StepB, task="b")
        stats = wf.cost_stats()
        expected_total_p95 = sum(s.p95_cost for s in stats.per_step)
        assert stats.total_p95 == pytest.approx(expected_total_p95)
