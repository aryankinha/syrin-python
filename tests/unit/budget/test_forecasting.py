"""Tests for budget forecasting (P6-T4).

All tests written first (TDD red phase). Implementation in
src/syrin/budget/_forecast.py.

Exit criteria:
- BudgetForecaster computes ON_TRACK / AT_RISK / LIKELY_EXCEEDED correctly.
- fire_hook() calls the hook_fn with Hook.BUDGET_FORECAST.
- as_hook_data() returns a dict with required forecast fields.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from syrin.budget._forecast import BudgetForecaster, ForecastResult
from syrin.enums import BudgetForecastStatus, Hook


def test_forecaster_constructs() -> None:
    """BudgetForecaster(total_p50=1.00, total_p95=2.00) constructs without error."""
    forecaster = BudgetForecaster(total_p50=1.0, total_p95=2.0)
    assert forecaster is not None


def test_update_updates_state() -> None:
    """forecaster.update() can be called with step_index and actual_spent."""
    forecaster = BudgetForecaster(total_p50=1.0, total_p95=2.0)
    # Should not raise
    forecaster.update(step_index=0, actual_spent=0.05)


def test_forecast_returns_forecast_result() -> None:
    """forecaster.forecast() returns ForecastResult with expected fields."""
    forecaster = BudgetForecaster(total_p50=1.0, total_p95=2.0)
    forecaster.update(step_index=0, actual_spent=0.05)
    result = forecaster.forecast(steps_remaining=3)
    assert isinstance(result, ForecastResult)
    assert hasattr(result, "status")
    assert hasattr(result, "forecast_p50")
    assert hasattr(result, "forecast_p95")


def test_on_track_when_under_p50() -> None:
    """status = ON_TRACK when actual spend pace is below p50 projection."""
    # burn_rate = 0.05/1 = 0.05; projected = 0.05 + 0.05*3 = 0.20 < p50=1.0
    forecaster = BudgetForecaster(total_p50=1.0, total_p95=2.0)
    forecaster.update(step_index=0, actual_spent=0.05)
    result = forecaster.forecast(steps_remaining=3)
    assert result.status == BudgetForecastStatus.ON_TRACK


def test_at_risk_when_between_p50_and_p95() -> None:
    """status = AT_RISK when projected cost exceeds p50 but not p95."""
    # burn_rate = 0.4/1 = 0.4; projected = 0.4 + 0.4*3 = 1.6; p50=1.0 < 1.6 < p95=2.0
    forecaster = BudgetForecaster(total_p50=1.0, total_p95=2.0)
    forecaster.update(step_index=0, actual_spent=0.4)
    result = forecaster.forecast(steps_remaining=3)
    assert result.status == BudgetForecastStatus.AT_RISK


def test_likely_exceeded_when_over_p95() -> None:
    """status = LIKELY_EXCEEDED when projected cost exceeds p95."""
    # burn_rate = 0.7/1 = 0.7; projected = 0.7 + 0.7*3 = 2.8 > p95=2.0
    forecaster = BudgetForecaster(total_p50=1.0, total_p95=2.0)
    forecaster.update(step_index=0, actual_spent=0.7)
    result = forecaster.forecast(steps_remaining=3)
    assert result.status == BudgetForecastStatus.LIKELY_EXCEEDED


def test_as_hook_data_returns_dict() -> None:
    """forecaster.as_hook_data() returns a dict with forecast fields."""
    forecaster = BudgetForecaster(total_p50=1.0, total_p95=2.0)
    forecaster.update(step_index=0, actual_spent=0.05)
    data = forecaster.as_hook_data(spent=0.05, steps_remaining=3)
    assert isinstance(data, dict)


def test_fire_hook_fires_budget_forecast() -> None:
    """forecaster.fire_hook() calls the hook_fn with Hook.BUDGET_FORECAST."""
    forecaster = BudgetForecaster(total_p50=1.0, total_p95=2.0)
    forecaster.update(step_index=0, actual_spent=0.05)
    hook_fn = MagicMock()
    forecaster.fire_hook(hook_fn, spent=0.05, steps_remaining=3)
    hook_fn.assert_called_once()
    args = hook_fn.call_args[0]
    assert args[0] == Hook.BUDGET_FORECAST


def test_hook_data_has_required_fields() -> None:
    """Hook data from as_hook_data() includes forecast_p50, forecast_p95, forecast_status."""
    forecaster = BudgetForecaster(total_p50=1.0, total_p95=2.0)
    forecaster.update(step_index=0, actual_spent=0.05)
    data = forecaster.as_hook_data(spent=0.05, steps_remaining=3)
    assert "forecast_p50" in data
    assert "forecast_p95" in data
    assert "forecast_status" in data
