"""Edge cases and invalid/valid tests for critical path modules (threshold, config, run).

TDD-style: valid inputs, invalid inputs, and boundary cases for code quality coverage.
"""

from __future__ import annotations

from unittest.mock import patch

import syrin
from syrin.config import get_config
from syrin.enums import StopReason, ThresholdMetric, ThresholdWindow
from syrin.response import Response
from syrin.threshold import (
    BudgetThreshold,
    ContextThreshold,
    ThresholdContext,
)

# -----------------------------------------------------------------------------
# Config — edge cases
# -----------------------------------------------------------------------------


def test_config_get_unknown_key_returns_none_without_default() -> None:
    """config.get('unknown') without default returns None (or attribute)."""
    config = get_config()
    val = config.get("_nonexistent_attr_xyz", None)
    assert val is None


def test_config_set_trace_toggle() -> None:
    """Config trace can be toggled via set()."""
    config = get_config()
    orig = config.trace
    config.set(trace=not orig)
    assert config.trace is not orig
    config.set(trace=orig)


# -----------------------------------------------------------------------------
# Threshold — valid
# -----------------------------------------------------------------------------


def test_budget_threshold_creation() -> None:
    """BudgetThreshold accepts valid at and metric with action."""
    t = BudgetThreshold(at=80, metric=ThresholdMetric.COST, action=lambda _: None)
    assert t.at == 80
    assert t.metric == ThresholdMetric.COST


def test_context_threshold_creation() -> None:
    """ContextThreshold accepts valid at and action."""
    t = ContextThreshold(at=75, action=lambda _: None)
    assert t.metric == ThresholdMetric.TOKENS
    assert t.window == ThresholdWindow.MAX_TOKENS


def test_threshold_context_has_metric() -> None:
    """ThresholdContext holds metric and optional parent."""
    ctx = ThresholdContext(
        percentage=80,
        metric=ThresholdMetric.COST,
        current_value=0.5,
        limit_value=1.0,
        parent=None,
    )
    assert ctx.metric == ThresholdMetric.COST
    assert ctx.parent is None
    assert ctx.percentage == 80


# -----------------------------------------------------------------------------
# Threshold — edge cases
# -----------------------------------------------------------------------------


def test_budget_threshold_should_trigger_boundary() -> None:
    """should_trigger at exactly at percentage returns True."""
    t = BudgetThreshold(at=100, metric=ThresholdMetric.COST, action=lambda _: None)
    result = t.should_trigger(100)
    assert result is True


def test_run_with_empty_input_string() -> None:
    """run() with empty input string does not crash (valid edge case)."""
    with patch("syrin.Agent") as MockAgent:
        MockAgent.return_value.run.return_value = Response(
            content="",
            cost=0.0,
            tokens=0,
            stop_reason=StopReason.END_TURN,
        )
        result = syrin.run("", model="openai/gpt-4o-mini")
    assert isinstance(result, Response)
    assert result.content == ""
