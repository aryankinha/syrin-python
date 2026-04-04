"""Tests for Budget.anomaly_detection — fires Hook.BUDGET_ANOMALY when cost > threshold * p95.

Exit criteria:
- Budget(anomaly_detection=AnomalyConfig(threshold_multiplier=2.0)) fires Hook.BUDGET_ANOMALY
  when actual cost > 2x historical p95.
"""

from __future__ import annotations

import pytest

from syrin import Agent, Budget, Model
from syrin.budget._guardrails import AnomalyConfig
from syrin.enums import Hook
from syrin.events import EventContext


def _almock() -> Model:
    return Model.Almock(latency_seconds=0.01, lorem_length=5)


class TestBudgetAnomalyDetection:
    """Budget.anomaly_detection fires BUDGET_ANOMALY when cost is anomalous."""

    def test_anomaly_hook_fires_when_cost_exceeds_threshold(self) -> None:
        """BUDGET_ANOMALY fires when actual cost > threshold_multiplier * p95."""
        from syrin.budget._history import _get_default_store

        anomaly_events: list[EventContext] = []

        class AnomalyAgent(Agent):
            model = _almock()
            system_prompt = "anomaly"

        # Seed historical data: p95 ≈ 0.05
        store = _get_default_store()
        store.clear("AnomalyAgent")
        for _ in range(10):
            store.record("AnomalyAgent", 0.05)

        try:
            agent = AnomalyAgent(
                budget=Budget(
                    max_cost=10.0,
                    estimation=True,
                    anomaly_detection=AnomalyConfig(threshold_multiplier=2.0),
                )
            )
            agent.events.on(Hook.BUDGET_ANOMALY, anomaly_events.append)

            # Directly call _check_budget_anomaly with a cost that exceeds 2x p95
            # (0.50 > 2.0 * 0.05 = 0.10)
            agent._check_budget_anomaly(0.50)

            assert len(anomaly_events) >= 1, "BUDGET_ANOMALY should fire for cost > 2x p95"
            ctx = anomaly_events[0]
            assert ctx["actual"] == pytest.approx(0.50, abs=0.01)
        finally:
            store.clear("AnomalyAgent")

    def test_no_anomaly_hook_when_cost_is_normal(self) -> None:
        """BUDGET_ANOMALY does NOT fire when cost is within threshold."""
        from syrin.budget._history import _get_default_store

        anomaly_events: list[EventContext] = []

        class NormalCostAgent(Agent):
            model = _almock()
            system_prompt = "normal"

        store = _get_default_store()
        store.clear("NormalCostAgent")
        for _ in range(10):
            store.record("NormalCostAgent", 0.05)  # p95 ≈ 0.05; threshold = 0.10

        try:
            agent = NormalCostAgent(
                budget=Budget(
                    max_cost=10.0,
                    estimation=True,
                    anomaly_detection=AnomalyConfig(threshold_multiplier=2.0),
                )
            )
            agent.events.on(Hook.BUDGET_ANOMALY, anomaly_events.append)

            # Cost 0.04 < threshold 0.10 → no anomaly
            agent._check_budget_anomaly(0.04)

            assert len(anomaly_events) == 0, "BUDGET_ANOMALY should NOT fire for normal cost"
        finally:
            store.clear("NormalCostAgent")

    def test_no_anomaly_without_history(self) -> None:
        """BUDGET_ANOMALY does NOT fire if there is no historical p95 data."""
        from syrin.budget._history import _get_default_store

        anomaly_events: list[EventContext] = []

        class NewAgent(Agent):
            model = _almock()
            system_prompt = "new"

        store = _get_default_store()
        store.clear("NewAgent")  # ensure no history

        agent = NewAgent(
            budget=Budget(
                max_cost=10.0,
                estimation=True,
                anomaly_detection=AnomalyConfig(threshold_multiplier=2.0),
            )
        )
        agent.events.on(Hook.BUDGET_ANOMALY, anomaly_events.append)

        agent._check_budget_anomaly(99.0)  # Very high but no p95 history

        assert len(anomaly_events) == 0, "Without p95 history, anomaly cannot be detected"

    def test_anomaly_config_with_custom_multiplier(self) -> None:
        """AnomalyConfig.threshold_multiplier controls the detection sensitivity."""
        from syrin.budget._history import _get_default_store

        tight_events: list[EventContext] = []
        loose_events: list[EventContext] = []

        class TightAgent(Agent):
            model = _almock()
            system_prompt = "tight"

        class LooseAgent(Agent):
            model = _almock()
            system_prompt = "loose"

        store = _get_default_store()
        store.clear("TightAgent")
        store.clear("LooseAgent")
        for _ in range(10):
            store.record("TightAgent", 0.10)
            store.record("LooseAgent", 0.10)

        try:
            tight = TightAgent(
                budget=Budget(
                    max_cost=10.0,
                    estimation=True,
                    anomaly_detection=AnomalyConfig(threshold_multiplier=1.1),
                )
            )
            tight.events.on(Hook.BUDGET_ANOMALY, tight_events.append)

            loose = LooseAgent(
                budget=Budget(
                    max_cost=10.0,
                    estimation=True,
                    anomaly_detection=AnomalyConfig(threshold_multiplier=5.0),
                )
            )
            loose.events.on(Hook.BUDGET_ANOMALY, loose_events.append)

            # 0.15 > 1.1 * 0.10 = 0.11 → fires for tight
            tight._check_budget_anomaly(0.15)
            # 0.15 < 5.0 * 0.10 = 0.50 → does NOT fire for loose
            loose._check_budget_anomaly(0.15)

            assert len(tight_events) >= 1, "Tight threshold (1.1x) should fire"
            assert len(loose_events) == 0, "Loose threshold (5x) should not fire"
        finally:
            store.clear("TightAgent")
            store.clear("LooseAgent")
