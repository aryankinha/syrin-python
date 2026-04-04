"""Tests for budget estimation (v0.11.0 API).

Tests cover CostEstimator.estimate_agent() and estimate_many(), using
CostEstimate as the result type.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from syrin.budget import Budget
from syrin.budget._estimate import (
    CostEstimate,
    CostEstimator,
)


# ---------------------------------------------------------------------------
# Helpers: minimal agent-like classes for testing
# ---------------------------------------------------------------------------
class _AgentNoHint:
    """Agent with no output_tokens_estimate and no history."""

    __name__ = "_AgentNoHint"


class _AgentWithInt:
    """Agent with output_tokens_estimate as int."""

    __name__ = "_AgentWithInt"
    output_tokens_estimate: int = 350


class _AgentWithTuple:
    """Agent with output_tokens_estimate as (min, max) tuple."""

    __name__ = "_AgentWithTuple"
    output_tokens_estimate: tuple[int, int] = (200, 800)


# ---------------------------------------------------------------------------
# T1: CostEstimator().estimate_agent() returns CostEstimate
# ---------------------------------------------------------------------------
def test_estimate_agent_returns_cost_estimate() -> None:
    """CostEstimator().estimate_agent() returns a CostEstimate."""
    estimator = CostEstimator()
    result = estimator.estimate_agent(_AgentWithInt)
    assert isinstance(result, CostEstimate)


# ---------------------------------------------------------------------------
# T2: CostEstimate.p50 is a positive float
# ---------------------------------------------------------------------------
def test_p50_is_positive() -> None:
    """CostEstimate.p50 is a positive float."""
    estimator = CostEstimator()
    result = estimator.estimate_agent(_AgentWithInt)
    assert result.p50 > 0.0


# ---------------------------------------------------------------------------
# T3: CostEstimate.p95 >= CostEstimate.p50
# ---------------------------------------------------------------------------
def test_p95_gte_p50() -> None:
    """CostEstimate.p95 >= CostEstimate.p50."""
    estimator = CostEstimator()
    result = estimator.estimate_agent(_AgentWithInt)
    assert result.p95 >= result.p50


# ---------------------------------------------------------------------------
# T4: estimate_many returns one aggregated CostEstimate
# ---------------------------------------------------------------------------
def test_estimate_many_aggregates() -> None:
    """estimate_many() returns a single CostEstimate aggregating all agents."""
    estimator = CostEstimator()
    result = estimator.estimate_many([_AgentWithInt, _AgentWithTuple])
    assert isinstance(result, CostEstimate)


# ---------------------------------------------------------------------------
# T5: sufficient is True when budget.max_cost >= total p95
# ---------------------------------------------------------------------------
def test_sufficient_true_when_enough() -> None:
    """CostEstimate.sufficient is True when max_cost >= total p95."""
    estimator = CostEstimator()
    result = estimator.estimate_many([_AgentWithInt], budget=Budget(max_cost=1000.0))
    assert result.sufficient is True


# ---------------------------------------------------------------------------
# T6: sufficient is False when budget.max_cost < total p95
# ---------------------------------------------------------------------------
def test_sufficient_false_when_insufficient() -> None:
    """CostEstimate.sufficient is False when max_cost < total p95."""
    estimator = CostEstimator()
    result = estimator.estimate_many([_AgentWithInt], budget=Budget(max_cost=0.000001))
    assert result.sufficient is False


# ---------------------------------------------------------------------------
# T7: Agent with output_tokens_estimate = 350 (int) uses correct cost
# ---------------------------------------------------------------------------
def test_int_hint_uses_exact_tokens() -> None:
    """Agent with output_tokens_estimate=350 produces non-zero p50 and p95."""
    from syrin.budget._estimate import DEFAULT_TOKEN_COST_USD

    estimator = CostEstimator()
    result = estimator.estimate_agent(_AgentWithInt)
    expected = 350 * DEFAULT_TOKEN_COST_USD
    assert result.p50 == pytest.approx(expected)
    assert result.p95 == pytest.approx(expected)
    assert result.low_confidence is False


# ---------------------------------------------------------------------------
# T8: Agent with output_tokens_estimate = (200, 800) uses min/max correctly
# ---------------------------------------------------------------------------
def test_tuple_hint_uses_min_for_p50_max_for_p95() -> None:
    """Agent with output_tokens_estimate=(200, 800) uses 200 as p50 and 800 as p95."""
    from syrin.budget._estimate import DEFAULT_TOKEN_COST_USD

    estimator = CostEstimator()
    result = estimator.estimate_agent(_AgentWithTuple)
    assert result.p50 == pytest.approx(200 * DEFAULT_TOKEN_COST_USD)
    assert result.p95 == pytest.approx(800 * DEFAULT_TOKEN_COST_USD)
    assert result.low_confidence is False


# ---------------------------------------------------------------------------
# T9: Agent with no hint and no history → low_confidence
# ---------------------------------------------------------------------------
def test_no_hint_no_history_is_low_confidence() -> None:
    """Agent with no output_tokens_estimate and no history is low_confidence."""
    estimator = CostEstimator()
    result = estimator.estimate_agent(_AgentNoHint)
    assert result.low_confidence is True


# ---------------------------------------------------------------------------
# T10: low_confidence is False when all agents have hints
# ---------------------------------------------------------------------------
def test_low_confidence_false_when_all_have_hints() -> None:
    """low_confidence is False when all agents have output_tokens_estimate."""
    estimator = CostEstimator()
    result = estimator.estimate_many([_AgentWithInt, _AgentWithTuple])
    assert result.low_confidence is False


# ---------------------------------------------------------------------------
# T11: Estimation makes zero LLM calls
# ---------------------------------------------------------------------------
def test_estimation_makes_zero_llm_calls() -> None:
    """CostEstimator.estimate_many() makes zero LLM calls."""
    with patch("syrin.agent._core.Agent.arun", new_callable=AsyncMock) as mock_arun:
        estimator = CostEstimator()
        estimator.estimate_many([_AgentWithInt, _AgentWithTuple, _AgentNoHint])
        mock_arun.assert_not_called()


# ---------------------------------------------------------------------------
# T12: CostEstimate dataclass fields
# ---------------------------------------------------------------------------
def test_cost_estimate_fields() -> None:
    """CostEstimate has expected fields."""
    est = CostEstimate(p50=0.0003, p95=0.0006, sufficient=True, low_confidence=False)
    assert est.p50 == pytest.approx(0.0003)
    assert est.p95 == pytest.approx(0.0006)
    assert est.sufficient is True
    assert est.low_confidence is False
