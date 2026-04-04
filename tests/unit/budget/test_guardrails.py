"""Tests for budget guardrails (P6-T5).

All tests written first (TDD red phase). Implementation in
src/syrin/budget/_guardrails.py.
"""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest

from syrin.budget._guardrails import (
    AnomalyConfig,
    BudgetGuardrails,
    BudgetLimitError,
    DynamicFanoutError,
    RetryBudgetExhausted,
)
from syrin.enums import Hook


# ---------------------------------------------------------------------------
# T1: check_fanout with exactly max_agents → no exception
# ---------------------------------------------------------------------------
def test_check_fanout_exact_limit_passes() -> None:
    """check_fanout with len(items) == max_agents does not raise."""
    BudgetGuardrails.check_fanout(items=list(range(5)), max_agents=5)


# ---------------------------------------------------------------------------
# T2: check_fanout with len(items) > max_agents → raises DynamicFanoutError
# ---------------------------------------------------------------------------
def test_check_fanout_over_limit_raises() -> None:
    """check_fanout with len(items) > max_agents raises DynamicFanoutError."""
    with pytest.raises(DynamicFanoutError):
        BudgetGuardrails.check_fanout(items=list(range(6)), max_agents=5)


# ---------------------------------------------------------------------------
# T3: DynamicFanoutError.requested and .max_allowed are set correctly
# ---------------------------------------------------------------------------
def test_dynamic_fanout_error_attributes() -> None:
    """DynamicFanoutError.requested == 6, .max_allowed == 5."""
    with pytest.raises(DynamicFanoutError) as exc_info:
        BudgetGuardrails.check_fanout(items=list(range(6)), max_agents=5)
    err = exc_info.value
    assert err.requested == 6
    assert err.max_allowed == 5


# ---------------------------------------------------------------------------
# T4: check_daily_limit with spent <= limit → no exception
# ---------------------------------------------------------------------------
def test_check_daily_limit_under_limit_passes() -> None:
    """check_daily_limit with spent_today <= daily_limit does not raise."""
    BudgetGuardrails.check_daily_limit(spent_today=49.99, daily_limit=50.00)


# ---------------------------------------------------------------------------
# T5: check_daily_limit with spent > limit → raises BudgetLimitError
# ---------------------------------------------------------------------------
def test_check_daily_limit_over_limit_raises() -> None:
    """check_daily_limit with spent_today > daily_limit raises BudgetLimitError."""
    with pytest.raises(BudgetLimitError):
        BudgetGuardrails.check_daily_limit(spent_today=50.01, daily_limit=50.00)


# ---------------------------------------------------------------------------
# T6: check_daily_approaching at 80% fires DAILY_LIMIT_APPROACHING
# ---------------------------------------------------------------------------
def test_check_daily_approaching_at_80_pct_fires_hook() -> None:
    """check_daily_approaching fires DAILY_LIMIT_APPROACHING when at 80% of daily_limit."""
    fire_fn: Callable[[Hook, dict[str, object]], None] = MagicMock()
    BudgetGuardrails.check_daily_approaching(spent_today=40.00, daily_limit=50.00, fire_fn=fire_fn)
    fire_fn.assert_called_once()  # type: ignore[attr-defined]
    args = fire_fn.call_args[0]  # type: ignore[attr-defined]
    assert args[0] == Hook.DAILY_LIMIT_APPROACHING


# ---------------------------------------------------------------------------
# T7: check_daily_approaching at 60% does NOT fire
# ---------------------------------------------------------------------------
def test_check_daily_approaching_at_60_pct_no_hook() -> None:
    """check_daily_approaching does NOT fire when spend is 60% of daily_limit."""
    fire_fn: Callable[[Hook, dict[str, object]], None] = MagicMock()
    BudgetGuardrails.check_daily_approaching(spent_today=30.00, daily_limit=50.00, fire_fn=fire_fn)
    fire_fn.assert_not_called()  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# T8: check_retry_budget at exact ratio → no exception
# ---------------------------------------------------------------------------
def test_check_retry_budget_at_limit_passes() -> None:
    """check_retry_budget with retry_spent == max_cost * max_ratio does not raise."""
    BudgetGuardrails.check_retry_budget(retry_spent=0.30, max_cost=1.00, max_ratio=0.30)


# ---------------------------------------------------------------------------
# T9: check_retry_budget over ratio → raises RetryBudgetExhausted
# ---------------------------------------------------------------------------
def test_check_retry_budget_over_ratio_raises() -> None:
    """check_retry_budget with retry_spent > max_cost * max_ratio raises RetryBudgetExhausted."""
    with pytest.raises(RetryBudgetExhausted):
        BudgetGuardrails.check_retry_budget(retry_spent=0.31, max_cost=1.00, max_ratio=0.30)


# ---------------------------------------------------------------------------
# T10: check_anomaly fires BUDGET_ANOMALY when actual > threshold_multiplier * p95
# ---------------------------------------------------------------------------
def test_check_anomaly_fires_when_exceeded() -> None:
    """check_anomaly fires BUDGET_ANOMALY when actual > p95 * threshold_multiplier."""
    fire_fn: Callable[[Hook, dict[str, object]], None] = MagicMock()
    config = AnomalyConfig(threshold_multiplier=2.0)
    BudgetGuardrails.check_anomaly(actual=4.01, p95=2.00, config=config, fire_fn=fire_fn)
    fire_fn.assert_called_once()  # type: ignore[attr-defined]
    args = fire_fn.call_args[0]  # type: ignore[attr-defined]
    assert args[0] == Hook.BUDGET_ANOMALY


# ---------------------------------------------------------------------------
# T11: check_anomaly does NOT fire when actual <= threshold_multiplier * p95
# ---------------------------------------------------------------------------
def test_check_anomaly_does_not_fire_when_under() -> None:
    """check_anomaly does NOT fire when actual <= p95 * threshold_multiplier."""
    fire_fn: Callable[[Hook, dict[str, object]], None] = MagicMock()
    config = AnomalyConfig(threshold_multiplier=2.0)
    BudgetGuardrails.check_anomaly(actual=3.99, p95=2.00, config=config, fire_fn=fire_fn)
    fire_fn.assert_not_called()  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Additional: AnomalyConfig default threshold_multiplier
# ---------------------------------------------------------------------------
def test_anomaly_config_default_threshold() -> None:
    """AnomalyConfig.threshold_multiplier defaults to 2.0."""
    config = AnomalyConfig()
    assert config.threshold_multiplier == 2.0


# ---------------------------------------------------------------------------
# Additional: DynamicFanoutError message
# ---------------------------------------------------------------------------
def test_dynamic_fanout_error_message() -> None:
    """DynamicFanoutError has a descriptive string message."""
    err = DynamicFanoutError(requested=6, max_allowed=5)
    assert "6" in str(err)
    assert "5" in str(err)


# ---------------------------------------------------------------------------
# Additional: RetryBudgetExhausted attributes
# ---------------------------------------------------------------------------
def test_retry_budget_exhausted_attributes() -> None:
    """RetryBudgetExhausted has retry_spent and limit attributes."""
    with pytest.raises(RetryBudgetExhausted) as exc_info:
        BudgetGuardrails.check_retry_budget(retry_spent=0.31, max_cost=1.00, max_ratio=0.30)
    err = exc_info.value
    assert err.retry_spent == pytest.approx(0.31)
    assert err.limit == pytest.approx(0.30)  # max_cost * max_ratio = 1.00 * 0.30
