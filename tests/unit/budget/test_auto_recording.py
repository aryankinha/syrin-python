"""TDD tests for automatic cost history recording (auto-store feature).

Tests cover:
- Budget._record_run_cost() writes to the default store when estimation=True
- Budget._record_run_cost() is a no-op when estimation=False or cost <= 0
- Budget._effective_estimator() returns the default store-backed estimator
- Budget._effective_estimator() returns the custom estimator when set
- Agent.run() auto-records cost to the store after a successful run
- estimated_cost uses auto-store history after the first recorded run
"""

from __future__ import annotations

from pathlib import Path

import pytest

from syrin.model import Model

_MOCK_MODEL = Model.Almock()


# ---------------------------------------------------------------------------
# Budget._record_run_cost
# ---------------------------------------------------------------------------


def test_auto_recording_skipped_when_estimation_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_record_run_cost() is a no-op when estimation=False."""
    import syrin.budget._history as history_module
    from syrin.budget._core import Budget
    from syrin.budget._history import RollingBudgetStore

    store = RollingBudgetStore(path=tmp_path / "store.json")
    monkeypatch.setattr(history_module, "_default_rolling_store", store)

    budget = Budget(max_cost=1.0, estimation=False)
    budget._record_run_cost("MyAgent", 0.05)

    assert store.stats("MyAgent").run_count == 0


def test_auto_recording_skipped_on_zero_cost(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_record_run_cost() is a no-op when cost <= 0."""
    import syrin.budget._history as history_module
    from syrin.budget._core import Budget
    from syrin.budget._history import RollingBudgetStore

    store = RollingBudgetStore(path=tmp_path / "store.json")
    monkeypatch.setattr(history_module, "_default_rolling_store", store)

    budget = Budget(max_cost=1.0, estimation=True)
    budget._record_run_cost("MyAgent", 0.0)
    budget._record_run_cost("MyAgent", -0.01)

    assert store.stats("MyAgent").run_count == 0


def test_auto_recording_after_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_record_run_cost() records to the default store when estimation=True and cost > 0."""
    import syrin.budget._history as history_module
    from syrin.budget._core import Budget
    from syrin.budget._history import RollingBudgetStore

    store = RollingBudgetStore(path=tmp_path / "store.json")
    monkeypatch.setattr(history_module, "_default_rolling_store", store)

    budget = Budget(max_cost=1.0, estimation=True)
    budget._record_run_cost("ResearchAgent", 0.05)
    budget._record_run_cost("ResearchAgent", 0.07)

    stats = store.stats("ResearchAgent")
    assert stats.run_count == 2
    assert stats.mean == pytest.approx(0.06)


# ---------------------------------------------------------------------------
# Budget._effective_estimator
# ---------------------------------------------------------------------------


def test_effective_estimator_returns_default_with_auto_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_effective_estimator() returns a CostEstimator backed by the default store."""
    import syrin.budget._history as history_module
    from syrin.budget._core import Budget
    from syrin.budget._estimate import CostEstimator
    from syrin.budget._history import RollingBudgetStore

    store = RollingBudgetStore(path=tmp_path / "store.json")
    monkeypatch.setattr(history_module, "_default_rolling_store", store)

    budget = Budget(max_cost=1.0, estimation=True)
    estimator = budget._effective_estimator()

    assert isinstance(estimator, CostEstimator)
    # The estimator should have the auto store wired up
    assert estimator._store is store


def test_effective_estimator_returns_custom_when_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_effective_estimator() returns the custom estimator when Budget.estimator is set."""
    import syrin.budget._history as history_module
    from syrin.budget._core import Budget
    from syrin.budget._estimate import CostEstimate, CostEstimator
    from syrin.budget._history import RollingBudgetStore

    store = RollingBudgetStore(path=tmp_path / "store.json")
    monkeypatch.setattr(history_module, "_default_rolling_store", store)

    class FixedEstimator(CostEstimator):
        def estimate_agent(self, agent_class: type) -> CostEstimate:
            return CostEstimate(p50=0.42, p95=0.84, sufficient=True, low_confidence=False)

    custom = FixedEstimator()
    budget = Budget(max_cost=1.0, estimation=True, estimator=custom)
    estimator = budget._effective_estimator()

    assert estimator is custom


# ---------------------------------------------------------------------------
# estimated_cost uses auto-store history after first run
# ---------------------------------------------------------------------------


def test_estimated_cost_uses_auto_store_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After recording a real cost, estimated_cost uses that history (low_confidence=False)."""
    import syrin.budget._history as history_module
    from syrin.agent._core import Agent
    from syrin.budget._core import Budget
    from syrin.budget._history import RollingBudgetStore

    store = RollingBudgetStore(path=tmp_path / "store.json")
    monkeypatch.setattr(history_module, "_default_rolling_store", store)

    class MyAgent(Agent):
        model = _MOCK_MODEL
        system_prompt = "test"
        # No output_tokens_estimate — relies on history

    budget = Budget(max_cost=1.0, estimation=True)
    agent = MyAgent(budget=budget)

    # Before any history: should be low_confidence=True
    est_before = agent.estimated_cost
    assert est_before is not None
    assert est_before.low_confidence is True

    # Record a run cost via the budget method (simulating what run() will do)
    budget._record_run_cost("MyAgent", 0.05)

    # After recording: should be low_confidence=False
    est_after = agent.estimated_cost
    assert est_after is not None
    assert est_after.low_confidence is False
    assert est_after.p50 == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# Agent.run() auto-records cost
# ---------------------------------------------------------------------------


def test_agent_run_auto_records_cost(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Agent.run() records the actual cost to the default store when estimation=True."""
    import syrin.budget._history as history_module
    from syrin.agent._core import Agent
    from syrin.budget._core import Budget
    from syrin.budget._history import RollingBudgetStore

    store = RollingBudgetStore(path=tmp_path / "store.json")
    monkeypatch.setattr(history_module, "_default_rolling_store", store)

    class MyAgent(Agent):
        model = _MOCK_MODEL
        system_prompt = "test"

    budget = Budget(max_cost=1.0, estimation=True)
    agent = MyAgent(budget=budget)

    result = agent.run("Hello")
    # cost should be recorded regardless of exact amount
    stats = store.stats("MyAgent")
    assert stats.run_count == 1
    assert stats.mean == pytest.approx(result.cost)


def test_agent_run_does_not_record_when_estimation_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Agent.run() does NOT record cost when estimation=False."""
    import syrin.budget._history as history_module
    from syrin.agent._core import Agent
    from syrin.budget._core import Budget
    from syrin.budget._history import RollingBudgetStore

    store = RollingBudgetStore(path=tmp_path / "store.json")
    monkeypatch.setattr(history_module, "_default_rolling_store", store)

    class MyAgent(Agent):
        model = _MOCK_MODEL
        system_prompt = "test"

    budget = Budget(max_cost=1.0, estimation=False)
    agent = MyAgent(budget=budget)

    agent.run("Hello")
    assert store.stats("MyAgent").run_count == 0
