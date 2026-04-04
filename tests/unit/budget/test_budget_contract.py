"""TDD tests for the budget contract in _budget_ops.py.

Verifies the on_exceeded contract:
- Callback that returns → execution continues (warn behaviour)
- Callback that raises → exception propagates (stop behaviour)
- on_exceeded=None → BudgetExceededError raised by default
- Correct routing of token on_exceeded vs budget on_exceeded
- pre_call_budget_check follows the same contract
"""

from __future__ import annotations

import types
from typing import Any
from unittest.mock import MagicMock

import pytest

from syrin.agent._budget_ops import (
    _apply_budget_exceeded,
    check_and_apply_budget,
    pre_call_budget_check,
)
from syrin.budget import (
    Budget,
    BudgetExceededContext,
    BudgetLimitType,
    BudgetTracker,
    RateLimit,
    TokenLimits,
    TokenRateLimit,
    raise_on_exceeded,
    warn_on_exceeded,
)
from syrin.enums import ExceedPolicy
from syrin.exceptions import BudgetExceededError
from syrin.types import CostInfo, TokenUsage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _MockBudgetComponent:
    def save(self) -> None:
        pass


def _make_agent(
    budget: Budget | None = None,
    token_limits: TokenLimits | None = None,
    run_cost: float = 0.0,
    run_tokens: int = 0,
    estimate: float = 0.001,
) -> types.SimpleNamespace:
    tracker = BudgetTracker()
    if run_cost > 0 or run_tokens > 0:
        tracker.record(
            CostInfo(
                cost_usd=run_cost,
                token_usage=TokenUsage(total_tokens=run_tokens),
            )
        )
    agent = types.SimpleNamespace(
        _budget=budget,
        _token_limits=token_limits,
        _budget_tracker=tracker,
        _model=None,
        _model_config=None,
        estimate_cost=lambda _msgs, **_kw: estimate,
        _budget_component=_MockBudgetComponent(),
        _emit_event=MagicMock(),
    )
    return agent


def _exceeded_ctx(
    budget_type: BudgetLimitType = BudgetLimitType.RUN,
    current: float = 10.0,
    limit: float = 5.0,
) -> BudgetExceededContext:
    return BudgetExceededContext(
        current_cost=current,
        limit=limit,
        budget_type=budget_type,
        message="test exceeded",
    )


# ---------------------------------------------------------------------------
# _apply_budget_exceeded — contract unit tests
# ---------------------------------------------------------------------------


class TestApplyBudgetExceeded:
    def test_none_handler_raises_budget_exceeded_error(self) -> None:
        """With no handler, BudgetExceededError is raised."""
        ctx = _exceeded_ctx()
        with pytest.raises(BudgetExceededError):
            _apply_budget_exceeded(None, ctx)

    def test_raising_handler_propagates_exception(self) -> None:
        """raise_on_exceeded raises BudgetExceededError; it propagates."""
        ctx = _exceeded_ctx()
        with pytest.raises(BudgetExceededError):
            _apply_budget_exceeded(raise_on_exceeded, ctx)

    def test_returning_handler_allows_continuation(self) -> None:
        """warn_on_exceeded returns; _apply_budget_exceeded returns True."""
        ctx = _exceeded_ctx()
        result = _apply_budget_exceeded(warn_on_exceeded, ctx)
        assert result is True

    def test_custom_returning_handler_allows_continuation(self) -> None:
        """Custom callback that returns allows continuation."""
        called_with: list[BudgetExceededContext] = []

        def custom(ctx: BudgetExceededContext) -> None:
            called_with.append(ctx)

        ctx = _exceeded_ctx()
        result = _apply_budget_exceeded(custom, ctx)
        assert result is True
        assert called_with == [ctx]

    def test_custom_raising_handler_propagates(self) -> None:
        """Custom callback that raises stops execution."""

        def custom(ctx: BudgetExceededContext) -> None:
            raise RuntimeError("custom stop")

        ctx = _exceeded_ctx()
        with pytest.raises(RuntimeError, match="custom stop"):
            _apply_budget_exceeded(custom, ctx)


# ---------------------------------------------------------------------------
# pre_call_budget_check
# ---------------------------------------------------------------------------


class TestPreCallBudgetCheck:
    def test_under_limit_no_raise(self) -> None:
        """No exception when estimated cost is under the limit."""
        budget = Budget(max_cost=10.0, exceed_policy=ExceedPolicy.STOP)
        agent = _make_agent(budget=budget, run_cost=1.0, estimate=0.001)
        pre_call_budget_check(agent, [])  # should not raise

    def test_no_budget_no_raise(self) -> None:
        """No budget → no check."""
        agent = _make_agent(budget=None, estimate=99.0)
        pre_call_budget_check(agent, [])  # should not raise

    def test_no_max_cost_no_raise(self) -> None:
        """Budget with no max_cost → no check."""
        budget = Budget(exceed_policy=ExceedPolicy.STOP)
        agent = _make_agent(budget=budget, estimate=99.0)
        pre_call_budget_check(agent, [])  # should not raise

    def test_exceeded_with_raise_handler_raises(self) -> None:
        """When run usage + estimate >= max_cost and handler raises → BudgetExceededError."""
        budget = Budget(max_cost=5.0, exceed_policy=ExceedPolicy.STOP)
        agent = _make_agent(budget=budget, run_cost=4.99, estimate=0.02)
        with pytest.raises(BudgetExceededError):
            pre_call_budget_check(agent, [])

    def test_exceeded_with_warn_handler_continues(self) -> None:
        """When run usage + estimate >= max_cost and handler returns → no exception."""
        budget = Budget(max_cost=5.0, exceed_policy=ExceedPolicy.WARN)
        agent = _make_agent(budget=budget, run_cost=4.99, estimate=0.02)
        pre_call_budget_check(agent, [])  # warn returns, should not raise

    def test_exceeded_with_no_handler_raises(self) -> None:
        """When exceeded and on_exceeded=None → BudgetExceededError by default."""
        budget = Budget(max_cost=5.0, on_exceeded=None)
        agent = _make_agent(budget=budget, run_cost=4.99, estimate=0.02)
        with pytest.raises(BudgetExceededError):
            pre_call_budget_check(agent, [])

    def test_zero_max_cost_blocks_any_call(self) -> None:
        """Budget(max_cost=0.0) blocks all calls — any estimate exceeds."""
        budget = Budget(max_cost=0.0, exceed_policy=ExceedPolicy.STOP)
        agent = _make_agent(budget=budget, run_cost=0.0, estimate=0.0001)
        with pytest.raises(BudgetExceededError):
            pre_call_budget_check(agent, [])

    def test_exactly_at_limit_blocks(self) -> None:
        """run_usage + estimate == max_cost → exceeded (>= comparison)."""
        budget = Budget(max_cost=5.0, exceed_policy=ExceedPolicy.STOP)
        agent = _make_agent(budget=budget, run_cost=4.9, estimate=0.1)
        with pytest.raises(BudgetExceededError):
            pre_call_budget_check(agent, [])


# ---------------------------------------------------------------------------
# check_and_apply_budget
# ---------------------------------------------------------------------------


class TestCheckAndApplyBudget:
    def test_no_budget_no_token_limits_no_raise(self) -> None:
        """No budget and no token limits → no check."""
        agent = _make_agent()
        check_and_apply_budget(agent)  # should not raise

    def test_under_limit_no_raise(self) -> None:
        """Under budget limit → no exception."""
        budget = Budget(max_cost=10.0, exceed_policy=ExceedPolicy.STOP)
        agent = _make_agent(budget=budget, run_cost=1.0)
        check_and_apply_budget(agent)  # should not raise

    def test_exceeded_with_raise_handler_raises(self) -> None:
        """Run cost >= max_cost and handler raises → BudgetExceededError."""
        budget = Budget(max_cost=5.0, exceed_policy=ExceedPolicy.STOP)
        agent = _make_agent(budget=budget, run_cost=6.0)
        with pytest.raises(BudgetExceededError):
            check_and_apply_budget(agent)

    def test_exceeded_with_warn_handler_continues(self) -> None:
        """Run cost >= max_cost and warn handler returns → no exception (continue)."""
        budget = Budget(max_cost=5.0, exceed_policy=ExceedPolicy.WARN)
        agent = _make_agent(budget=budget, run_cost=6.0)
        check_and_apply_budget(agent)  # should not raise

    def test_exceeded_with_no_handler_raises(self) -> None:
        """Run cost >= max_cost and on_exceeded=None → BudgetExceededError by default."""
        budget = Budget(max_cost=5.0, on_exceeded=None)
        agent = _make_agent(budget=budget, run_cost=6.0)
        with pytest.raises(BudgetExceededError):
            check_and_apply_budget(agent)

    def test_token_run_exceeded_uses_token_on_exceeded(self) -> None:
        """When token run limit exceeded, token on_exceeded handler is called."""
        called: list[BudgetExceededContext] = []

        def token_handler(ctx: BudgetExceededContext) -> None:
            called.append(ctx)

        budget = Budget(max_cost=100.0, exceed_policy=ExceedPolicy.STOP)
        token_limits = TokenLimits(max_tokens=100, on_exceeded=token_handler)
        agent = _make_agent(budget=budget, token_limits=token_limits, run_tokens=200)
        check_and_apply_budget(agent)  # token_handler returns, so no raise
        assert len(called) == 1
        assert called[0].budget_type == BudgetLimitType.RUN_TOKENS

    def test_token_on_exceeded_fallback_when_budget_handler_is_none(self) -> None:
        """When budget.on_exceeded is None but token_limits.on_exceeded exists, use it."""
        called: list[BudgetExceededContext] = []

        def token_handler(ctx: BudgetExceededContext) -> None:
            called.append(ctx)

        budget = Budget(max_cost=5.0, on_exceeded=None)
        token_limits = TokenLimits(on_exceeded=token_handler)
        # Run cost exceeds budget → budget.on_exceeded is None, fallback to token handler
        agent = _make_agent(budget=budget, token_limits=token_limits, run_cost=6.0)
        check_and_apply_budget(agent)
        assert len(called) == 1

    def test_hourly_rate_limit_exceeded_raises(self) -> None:
        """When hourly rate limit exceeded and raise handler → BudgetExceededError."""
        budget = Budget(
            max_cost=100.0,
            rate_limits=RateLimit(hour=1.0),
            exceed_policy=ExceedPolicy.STOP,
        )
        agent = _make_agent(budget=budget, run_cost=2.0)
        with pytest.raises(BudgetExceededError):
            check_and_apply_budget(agent)

    def test_token_rate_limit_hour_exceeded_uses_token_handler(self) -> None:
        """Hour token rate limit exceeded → token on_exceeded called."""
        called: list[BudgetExceededContext] = []

        def token_handler(ctx: BudgetExceededContext) -> None:
            called.append(ctx)

        token_limits = TokenLimits(
            rate_limits=TokenRateLimit(hour=100),
            on_exceeded=token_handler,
        )
        # We need to record enough tokens to exceed the hourly limit
        # Use a tracker with tokens already recorded
        tracker = BudgetTracker()
        tracker.record(CostInfo(cost_usd=0.01, token_usage=TokenUsage(total_tokens=200)))
        agent = types.SimpleNamespace(
            _budget=None,
            _token_limits=token_limits,
            _budget_tracker=tracker,
            _model=None,
            _model_config=None,
            estimate_cost=lambda _msgs, **_kw: 0.001,
            _budget_component=_MockBudgetComponent(),
            _emit_event=MagicMock(),
        )
        check_and_apply_budget(agent)
        assert len(called) == 1
        assert called[0].budget_type == BudgetLimitType.HOUR_TOKENS


# ---------------------------------------------------------------------------
# BudgetStatus.EXCEEDED does not double-raise (A3 regression test)
# ---------------------------------------------------------------------------


class TestThresholdReFireGuard:
    def test_threshold_fires_only_once_per_run(self) -> None:
        """A threshold action should not fire again on repeated check_budget calls."""
        fire_count = [0]

        def action(ctx: Any) -> None:
            fire_count[0] += 1

        from syrin.enums import ThresholdMetric
        from syrin.threshold import BudgetThreshold

        budget = Budget(
            max_cost=10.0,
            thresholds=[BudgetThreshold(at=50, action=action, metric=ThresholdMetric.COST)],
        )
        tracker = BudgetTracker()
        tracker.record(CostInfo(cost_usd=6.0, token_usage=TokenUsage()))

        # Call check_budget three times — threshold should fire only once
        agent = _make_agent(budget=budget, run_cost=0.0)
        agent._budget_tracker = tracker
        check_and_apply_budget(agent)
        check_and_apply_budget(agent)
        check_and_apply_budget(agent)
        assert fire_count[0] == 1, f"Expected 1 fire, got {fire_count[0]}"

    def test_threshold_re_fires_after_reset_run(self) -> None:
        """After reset_run(), the threshold may fire again on the next run."""
        fire_count = [0]

        def action(ctx: Any) -> None:
            fire_count[0] += 1

        from syrin.enums import ThresholdMetric
        from syrin.threshold import BudgetThreshold

        tracker = BudgetTracker()
        tracker.record(CostInfo(cost_usd=6.0, token_usage=TokenUsage()))
        budget = Budget(
            max_cost=10.0,
            thresholds=[BudgetThreshold(at=50, action=action, metric=ThresholdMetric.COST)],
        )
        triggered1 = tracker.check_thresholds(budget)
        assert len(triggered1) == 1
        assert fire_count[0] == 1

        # Second call without reset: should not fire
        triggered2 = tracker.check_thresholds(budget)
        assert len(triggered2) == 0
        assert fire_count[0] == 1

        # After reset_run + new cost, should fire again
        tracker.reset_run()
        tracker.record(CostInfo(cost_usd=6.0, token_usage=TokenUsage()))
        triggered3 = tracker.check_thresholds(budget)
        assert len(triggered3) == 1
        assert fire_count[0] == 2


class TestNoDuplicateRaise:
    def test_warn_handler_called_once_per_exceeded(self) -> None:
        """warn_on_exceeded is invoked exactly once when budget exceeded."""
        call_count = [0]

        def counting_warn(ctx: BudgetExceededContext) -> None:
            call_count[0] += 1

        budget = Budget(max_cost=5.0, on_exceeded=counting_warn)
        agent = _make_agent(budget=budget, run_cost=6.0)
        check_and_apply_budget(agent)
        assert call_count[0] == 1
