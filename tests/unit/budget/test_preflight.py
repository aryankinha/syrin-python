"""Tests for Budget preflight, abort-on-forecast, and anomaly_detection fields."""

from __future__ import annotations

from syrin.budget import AnomalyConfig, Budget
from syrin.budget._guardrails import AnomalyConfig
from syrin.enums import EstimationPolicy, PreflightPolicy

# ---------------------------------------------------------------------------
# Preflight fields
# ---------------------------------------------------------------------------


def test_budget_preflight_defaults_false() -> None:
    budget = Budget(max_cost=1.0)
    assert budget.preflight is False
    assert budget.preflight_fail_on == PreflightPolicy.WARN_ONLY


def test_budget_preflight_below_p95() -> None:
    budget = Budget(
        max_cost=1.0,
        preflight=True,
        preflight_fail_on=PreflightPolicy.BELOW_P95,
    )
    assert budget.preflight is True
    assert budget.preflight_fail_on == PreflightPolicy.BELOW_P95


def test_budget_preflight_warn_only() -> None:
    budget = Budget(
        max_cost=1.0,
        preflight=True,
        preflight_fail_on=PreflightPolicy.WARN_ONLY,
    )
    assert budget.preflight is True
    assert budget.preflight_fail_on == PreflightPolicy.WARN_ONLY


# ---------------------------------------------------------------------------
# Abort on forecast fields
# ---------------------------------------------------------------------------


def test_budget_abort_on_forecast_exceeded() -> None:
    budget = Budget(
        max_cost=2.0,
        abort_on_forecast_exceeded=True,
        abort_forecast_multiplier=1.1,
    )
    assert budget.abort_on_forecast_exceeded is True
    assert abs(budget.abort_forecast_multiplier - 1.1) < 1e-10


def test_budget_abort_on_forecast_defaults() -> None:
    budget = Budget(max_cost=1.0)
    assert budget.abort_on_forecast_exceeded is False
    assert abs(budget.abort_forecast_multiplier - 1.0) < 1e-10


# ---------------------------------------------------------------------------
# AnomalyConfig field
# ---------------------------------------------------------------------------


def test_budget_anomaly_detection_none_by_default() -> None:
    budget = Budget(max_cost=1.0)
    assert budget.anomaly_detection is None


def test_budget_anomaly_detection_configured() -> None:
    config = AnomalyConfig(threshold_multiplier=2.0)
    budget = Budget(max_cost=1.0, anomaly_detection=config)
    assert budget.anomaly_detection is not None
    assert budget.anomaly_detection.threshold_multiplier == 2.0


# ---------------------------------------------------------------------------
# Backward compatibility — existing estimation fields must still work
# ---------------------------------------------------------------------------


def test_budget_backward_compat_estimation_fields() -> None:
    budget = Budget(
        max_cost=5.0,
        estimation=True,
        estimation_policy=EstimationPolicy.RAISE,
    )
    assert budget.estimation is True
    assert budget.estimation_policy == EstimationPolicy.RAISE
