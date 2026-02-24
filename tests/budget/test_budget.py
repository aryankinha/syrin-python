"""Tests for budget models and BudgetTracker (budget.py)."""

from __future__ import annotations

import pytest

from syrin.budget import (
    Budget,
    BudgetLimitType,
    BudgetStatus,
    BudgetThreshold,
    BudgetTracker,
    CheckBudgetResult,
    RateLimit,
    Threshold,
    TokenLimits,
    raise_on_exceeded,
    warn_on_exceeded,
)
from syrin.enums import ThresholdMetric
from syrin.types import CostInfo, TokenUsage


def test_rate_limit_model() -> None:
    r = RateLimit(hour=10.0, day=100.0)
    assert r.hour == 10.0
    assert r.day == 100.0
    assert r.week is None


def test_budget_model() -> None:
    b = Budget(run=5.0, on_exceeded=warn_on_exceeded, thresholds=[])
    assert b.run == 5.0
    assert b.on_exceeded is warn_on_exceeded
    assert b.thresholds == []


def test_threshold_with_action() -> None:
    """Threshold now takes a function as action."""
    t = Threshold(
        at=80, action=lambda ctx: print(f"Budget at {ctx.percentage}%"), metric=ThresholdMetric.COST
    )
    assert t.at == 80
    assert callable(t.action)


def test_threshold_with_lambda() -> None:
    """Test threshold with lambda action."""
    t = Threshold(
        at=80, action=lambda ctx: print(f"At {ctx.percentage}%"), metric=ThresholdMetric.COST
    )
    assert t.at == 80


def test_threshold_with_function() -> None:
    """Test threshold with function action."""

    def my_action(ctx):
        pass

    t = Threshold(at=90, action=my_action, metric=ThresholdMetric.COST)
    assert t.at == 90


def test_budget_tracker_record_and_run_cost() -> None:
    tracker = BudgetTracker()
    tracker.record(CostInfo(cost_usd=0.5, token_usage=TokenUsage()))
    tracker.record(CostInfo(cost_usd=0.3, token_usage=TokenUsage()))
    assert tracker.current_run_cost == 0.8
    tracker.reset_run()
    assert tracker.current_run_cost == 0.0


def test_budget_tracker_check_budget_ok() -> None:
    tracker = BudgetTracker()
    tracker.record(CostInfo(cost_usd=0.1, token_usage=TokenUsage()))
    budget = Budget(run=5.0)
    assert tracker.check_budget(budget) == BudgetStatus.OK


def test_budget_tracker_check_budget_exceeded() -> None:
    tracker = BudgetTracker()
    tracker.record(CostInfo(cost_usd=10.0, token_usage=TokenUsage()))
    budget = Budget(run=5.0)
    result = tracker.check_budget(budget)
    assert result == BudgetStatus.EXCEEDED  # backward compat
    assert result.status == BudgetStatus.EXCEEDED
    assert result.exceeded_limit == BudgetLimitType.RUN


def test_budget_tracker_check_budget_returns_check_budget_result() -> None:
    """check_budget returns CheckBudgetResult with status and exceeded_limit."""
    tracker = BudgetTracker()
    budget = Budget(run=5.0)
    result = tracker.check_budget(budget)
    assert isinstance(result, CheckBudgetResult)
    assert result.status == BudgetStatus.OK
    assert result.exceeded_limit is None


def test_budget_tracker_check_budget_exceeded_limit_run() -> None:
    """When run cost exceeded, exceeded_limit is 'run'."""
    tracker = BudgetTracker()
    tracker.record(CostInfo(cost_usd=10.0, token_usage=TokenUsage()))
    result = tracker.check_budget(Budget(run=5.0))
    assert result.status == BudgetStatus.EXCEEDED and result.exceeded_limit == BudgetLimitType.RUN


def test_budget_tracker_check_budget_exceeded_limit_run_tokens() -> None:
    """When run_tokens exceeded (via token_limits), exceeded_limit is 'run_tokens'."""
    tracker = BudgetTracker()
    tracker.record(
        CostInfo(
            cost_usd=0.0,
            token_usage=TokenUsage(total_tokens=500),
        )
    )
    result = tracker.check_budget(
        Budget(run=10.0),
        token_limits=TokenLimits(run=100),
    )
    assert (
        result.status == BudgetStatus.EXCEEDED
        and result.exceeded_limit == BudgetLimitType.RUN_TOKENS
    )


def test_budget_tracker_check_budget_exceeded_limit_hour_day_week_month() -> None:
    """When rate limit exceeded, exceeded_limit is hour/day/week/month."""
    tracker = BudgetTracker()
    tracker.record(CostInfo(cost_usd=100.0, token_usage=TokenUsage()))
    assert (
        tracker.check_budget(Budget(per=RateLimit(hour=10.0))).exceeded_limit
        == BudgetLimitType.HOUR
    )
    assert (
        tracker.check_budget(Budget(per=RateLimit(day=10.0))).exceeded_limit == BudgetLimitType.DAY
    )
    assert (
        tracker.check_budget(Budget(per=RateLimit(week=10.0))).exceeded_limit
        == BudgetLimitType.WEEK
    )
    assert (
        tracker.check_budget(Budget(per=RateLimit(month=10.0))).exceeded_limit
        == BudgetLimitType.MONTH
    )


def test_budget_tracker_check_budget_ok_and_threshold_have_no_exceeded_limit() -> None:
    """OK and THRESHOLD results have exceeded_limit None."""
    tracker = BudgetTracker()
    tracker.record(CostInfo(cost_usd=0.5, token_usage=TokenUsage()))
    assert tracker.check_budget(Budget(run=5.0)).exceeded_limit is None
    budget_with_threshold = Budget(
        run=5.0,
        thresholds=[
            Threshold(at=10, action=lambda _: None, metric=ThresholdMetric.COST),
        ],
    )
    triggered = tracker.check_thresholds(budget_with_threshold)
    assert len(triggered) == 1
    result = tracker.check_budget(budget_with_threshold)
    assert result.status == BudgetStatus.THRESHOLD and result.exceeded_limit is None


def test_budget_tracker_check_thresholds() -> None:
    triggered_actions = []

    def capture_action(ctx):
        triggered_actions.append(ctx.percentage)

    tracker = BudgetTracker()
    tracker.record(CostInfo(cost_usd=4.0, token_usage=TokenUsage()))
    budget = Budget(
        run=5.0, thresholds=[Threshold(at=80, action=capture_action, metric=ThresholdMetric.COST)]
    )
    triggered = tracker.check_thresholds(budget)
    assert len(triggered) == 1
    assert triggered[0].at == 80
    assert 80 in triggered_actions  # Action was executed


def test_budget_threshold_fallthrough_false_only_closest_runs() -> None:
    """With threshold_fallthrough=False (default), only the closest (highest) crossed threshold runs."""
    triggered_at: list[int] = []

    def make_action(at: int):
        def action(ctx):
            triggered_at.append(at)

        return action

    tracker = BudgetTracker()
    tracker.record(CostInfo(cost_usd=88.0, token_usage=TokenUsage()))
    budget = Budget(
        run=100.0,
        thresholds=[
            BudgetThreshold(at=50, action=make_action(50)),
            BudgetThreshold(at=70, action=make_action(70)),
            BudgetThreshold(at=90, action=make_action(90)),
        ],
    )
    triggered = tracker.check_thresholds(budget)
    assert len(triggered) == 1
    assert triggered[0].at == 70
    assert triggered_at == [70]


def test_budget_threshold_fallthrough_true_all_crossed_run() -> None:
    """With threshold_fallthrough=True, all crossed thresholds run (switch-case fallthrough)."""
    triggered_at: list[int] = []

    def make_action(at: int):
        def action(ctx):
            triggered_at.append(at)

        return action

    tracker = BudgetTracker()
    tracker.record(CostInfo(cost_usd=88.0, token_usage=TokenUsage()))
    budget = Budget(
        run=100.0,
        threshold_fallthrough=True,
        thresholds=[
            BudgetThreshold(at=50, action=make_action(50)),
            BudgetThreshold(at=70, action=make_action(70)),
            BudgetThreshold(at=90, action=make_action(90)),
        ],
    )
    triggered = tracker.check_thresholds(budget)
    assert len(triggered) == 2
    assert triggered_at == [50, 70]


def test_budget_threshold_fallthrough_false_exactly_at_boundary() -> None:
    """At exactly 70%, only the 70 threshold runs (not 50)."""
    triggered_at: list[int] = []

    def make_action(at: int):
        def action(ctx):
            triggered_at.append(at)

        return action

    tracker = BudgetTracker()
    tracker.record(CostInfo(cost_usd=70.0, token_usage=TokenUsage()))
    budget = Budget(
        run=100.0,
        thresholds=[
            BudgetThreshold(at=50, action=make_action(50)),
            BudgetThreshold(at=70, action=make_action(70)),
            BudgetThreshold(at=90, action=make_action(90)),
        ],
    )
    triggered = tracker.check_thresholds(budget)
    assert len(triggered) == 1
    assert triggered[0].at == 70
    assert triggered_at == [70]


def test_budget_tracker_get_summary() -> None:
    tracker = BudgetTracker()
    tracker.record(CostInfo(cost_usd=1.0, token_usage=TokenUsage()))
    s = tracker.get_summary()
    assert s.current_run_cost == 1.0
    assert s.entries_count == 1
    d = s.to_dict()
    assert "current_run_cost" in d
    assert "hourly_cost" in d


def test_budget_tracker_rolling_window() -> None:
    tracker = BudgetTracker()
    # All entries are "now" in monotonic time, so hourly/daily include them
    tracker.record(CostInfo(cost_usd=1.0, token_usage=TokenUsage()))
    assert tracker.hourly_cost == 1.0
    assert tracker.daily_cost == 1.0


# =============================================================================
# AGGRESSIVE EDGE CASES - TRY TO BREAK BUDGET
# =============================================================================


def test_rate_limit_negative_values_should_fail() -> None:
    """Negative rate limits should raise validation error."""
    with pytest.raises((ValueError, TypeError)):
        RateLimit(hour=-1.0)


def test_rate_limit_zero_values_allowed() -> None:
    """Zero rate limits should be valid (allow no spending)."""
    r = RateLimit(hour=0.0, day=0.0)
    assert r.hour == 0.0
    assert r.day == 0.0


def test_rate_limit_very_high_values() -> None:
    """Very high rate limits should be allowed."""
    r = RateLimit(hour=1_000_000.0, day=10_000_000.0)
    assert r.hour == 1_000_000.0


def test_budget_with_very_many_thresholds() -> None:
    """Many threshold actions should work."""
    thresholds = [
        Threshold(at=i, action=lambda _: None, metric=ThresholdMetric.COST)
        for i in range(0, 100, 5)
    ]
    b = Budget(run=10.0, thresholds=thresholds)
    assert len(b.thresholds) == 20


def test_budget_threshold_edge_cases() -> None:
    """Threshold at exact boundaries."""
    t0 = Threshold(at=0, action=lambda _: None, metric=ThresholdMetric.COST)
    assert t0.at == 0

    t100 = Threshold(at=100, action=lambda _: None, metric=ThresholdMetric.COST)
    assert t100.at == 100

    with pytest.raises(ValueError):
        Threshold(at=-1, action=lambda _: None, metric=ThresholdMetric.COST)

    with pytest.raises(ValueError):
        Threshold(at=101, action=lambda _: None, metric=ThresholdMetric.COST)


def test_budget_tracker_very_many_entries() -> None:
    """Many budget entries should be tracked efficiently."""
    tracker = BudgetTracker()
    for _i in range(10000):
        tracker.record(CostInfo(cost_usd=0.001, token_usage=TokenUsage()))

    assert tracker.current_run_cost == 10.0
    assert tracker.get_summary().entries_count == 10000


def test_budget_tracker_check_budget_at_exact_limit() -> None:
    """Test budget check at exact limit boundary - uses >= so exact = EXCEEDED."""
    tracker = BudgetTracker()
    tracker.record(CostInfo(cost_usd=5.0, token_usage=TokenUsage()))
    budget = Budget(run=5.0)
    # At exact limit triggers EXCEEDED (uses >= not >)
    assert tracker.check_budget(budget) == BudgetStatus.EXCEEDED


def test_budget_tracker_check_budget_slightly_over() -> None:
    """Test budget check slightly over limit."""
    tracker = BudgetTracker()
    tracker.record(CostInfo(cost_usd=5.01, token_usage=TokenUsage()))
    budget = Budget(run=5.0)
    assert tracker.check_budget(budget) == BudgetStatus.EXCEEDED


def test_budget_with_no_thresholds() -> None:
    """Budget with empty thresholds list."""
    b = Budget(run=10.0, thresholds=[])
    assert b.thresholds == []


def test_budget_on_exceeded_various_valid_actions() -> None:
    """Test all valid on_exceeded actions."""
    b1 = Budget(run=1.0, on_exceeded=raise_on_exceeded)
    assert b1.on_exceeded is raise_on_exceeded

    b2 = Budget(run=1.0, on_exceeded=warn_on_exceeded)
    assert b2.on_exceeded is warn_on_exceeded

    from syrin.budget import stop_on_exceeded

    b3 = Budget(run=1.0, on_exceeded=stop_on_exceeded)
    assert b3.on_exceeded is stop_on_exceeded


def test_budget_tracker_reset_run_multiple_times() -> None:
    """Multiple reset runs should work correctly."""
    tracker = BudgetTracker()
    tracker.record(CostInfo(cost_usd=5.0, token_usage=TokenUsage()))
    assert tracker.current_run_cost == 5.0

    tracker.reset_run()
    assert tracker.current_run_cost == 0.0

    tracker.record(CostInfo(cost_usd=3.0, token_usage=TokenUsage()))
    assert tracker.current_run_cost == 3.0

    tracker.reset_run()
    assert tracker.current_run_cost == 0.0

    tracker.record(CostInfo(cost_usd=2.0, token_usage=TokenUsage()))
    assert tracker.current_run_cost == 2.0


def test_budget_rejects_wrong_threshold_class() -> None:
    """Budget should reject ContextThreshold."""
    from syrin.threshold import ContextThreshold

    with pytest.raises(TypeError, match="Budget only accepts BudgetThreshold"):
        Budget(
            run=10.0,
            thresholds=[ContextThreshold(at=80, action=lambda _: None)],
        )


def test_budget_rejects_wrong_threshold_class_ratelimit() -> None:
    """Budget should reject RateLimitThreshold."""
    from syrin.threshold import RateLimitThreshold

    with pytest.raises(TypeError, match="Budget only accepts BudgetThreshold"):
        Budget(
            run=10.0,
            thresholds=[
                RateLimitThreshold(at=80, action=lambda _: None, metric=ThresholdMetric.RPM)
            ],
        )


def test_budget_rejects_invalid_metric() -> None:
    """Budget should reject thresholds with invalid metrics like RPM."""
    with pytest.raises(ValueError, match="Budget thresholds only support"):
        Budget(
            run=10.0,
            thresholds=[BudgetThreshold(at=80, action=lambda _: None, metric=ThresholdMetric.RPM)],
        )


def test_budget_threshold_accepts_cost_metric() -> None:
    """BudgetThreshold should accept COST metric."""
    threshold = BudgetThreshold(at=50, action=lambda _: None, metric=ThresholdMetric.COST)
    assert threshold.at == 50
    assert threshold.metric == ThresholdMetric.COST


def test_budget_threshold_accepts_tokens_metric() -> None:
    """BudgetThreshold should accept TOKENS metric."""
    threshold = BudgetThreshold(at=50, action=lambda _: None, metric=ThresholdMetric.TOKENS)
    assert threshold.at == 50
    assert threshold.metric == ThresholdMetric.TOKENS


def test_budget_threshold_default_metric_is_cost() -> None:
    """BudgetThreshold should default to COST metric."""
    threshold = BudgetThreshold(at=50, action=lambda _: None)
    assert threshold.metric == ThresholdMetric.COST


def test_budget_threshold_at_zero() -> None:
    """BudgetThreshold at 0%."""
    threshold = BudgetThreshold(at=0, action=lambda _: None)
    assert threshold.at == 0
    assert threshold.should_trigger(0) is True


def test_budget_threshold_at_100() -> None:
    """BudgetThreshold at 100%."""
    threshold = BudgetThreshold(at=100, action=lambda _: None)
    assert threshold.at == 100
    assert threshold.should_trigger(100) is True


def test_budget_threshold_invalid_at_negative() -> None:
    """BudgetThreshold should reject negative at value."""
    with pytest.raises(ValueError, match="Threshold 'at' must be between 0 and 100"):
        BudgetThreshold(at=-1, action=lambda _: None)


def test_budget_threshold_invalid_at_over_100() -> None:
    """BudgetThreshold should reject at > 100."""
    with pytest.raises(ValueError, match="Threshold 'at' must be between 0 and 100"):
        BudgetThreshold(at=101, action=lambda _: None)


def test_budget_threshold_requires_action() -> None:
    """BudgetThreshold should require action."""
    with pytest.raises(ValueError, match="Threshold 'action' is required"):
        BudgetThreshold(at=80, action=None)  # type: ignore


# =============================================================================
# NEW FEATURES: reserve, threshold window, consume
# =============================================================================


def test_budget_reserve_effective_limit() -> None:
    """Reserve reduces effective run limit."""
    b = Budget(run=10.0, reserve=2.0)
    assert b.run == 10.0
    assert b.reserve == 2.0
    b._set_spent(0)
    assert b.remaining == 8.0  # 10 - 2 - 0


def test_budget_remaining_with_reserve_after_spend() -> None:
    """Remaining accounts for reserve and spent."""
    b = Budget(run=10.0, reserve=1.0)
    b._set_spent(4.0)
    assert b.remaining == 5.0  # (10 - 1) - 4


def test_budget_tracker_check_budget_reserve_exceeded() -> None:
    """check_budget uses effective run (run - reserve)."""
    tracker = BudgetTracker()
    tracker.record(CostInfo(cost_usd=5.0, token_usage=TokenUsage()))
    budget = Budget(run=10.0, reserve=5.0)  # effective = 5
    assert tracker.check_budget(budget) == BudgetStatus.EXCEEDED


def test_budget_tracker_check_budget_reserve_ok() -> None:
    """Under effective limit is OK."""
    tracker = BudgetTracker()
    tracker.record(CostInfo(cost_usd=3.0, token_usage=TokenUsage()))
    budget = Budget(run=10.0, reserve=5.0)  # effective = 5
    assert tracker.check_budget(budget) == BudgetStatus.OK


def test_budget_tracker_current_run_tokens() -> None:
    """Tracker sums total_tokens from entries."""
    tracker = BudgetTracker()
    tracker.record(
        CostInfo(
            cost_usd=0.1,
            token_usage=TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150),
        )
    )
    tracker.record(
        CostInfo(
            cost_usd=0.2,
            token_usage=TokenUsage(input_tokens=200, output_tokens=100, total_tokens=300),
        )
    )
    assert tracker.current_run_tokens == 450
    assert abs(tracker.current_run_cost - 0.3) < 1e-9


def test_budget_tracker_check_budget_run_tokens_exceeded() -> None:
    """check_budget returns EXCEEDED when token_limits.run_tokens limit hit."""
    tracker = BudgetTracker()
    tracker.record(
        CostInfo(
            cost_usd=0.01,
            token_usage=TokenUsage(total_tokens=15000),
        )
    )
    assert (
        tracker.check_budget(
            Budget(run=10.0),
            token_limits=TokenLimits(run=10000),
        )
        == BudgetStatus.EXCEEDED
    )


def test_budget_tracker_check_budget_run_tokens_ok() -> None:
    """Under token_limits.run_tokens limit is OK."""
    tracker = BudgetTracker()
    tracker.record(
        CostInfo(
            cost_usd=0.01,
            token_usage=TokenUsage(total_tokens=5000),
        )
    )
    assert (
        tracker.check_budget(
            Budget(run=10.0),
            token_limits=TokenLimits(run=10000),
        )
        == BudgetStatus.OK
    )


def test_budget_summary_includes_current_run_tokens() -> None:
    """BudgetSummary has current_run_tokens."""
    tracker = BudgetTracker()
    tracker.record(
        CostInfo(
            cost_usd=1.0,
            token_usage=TokenUsage(total_tokens=1000),
        )
    )
    s = tracker.get_summary()
    assert s.current_run_tokens == 1000
    assert "current_run_tokens" in s.to_dict()


def test_budget_tracker_state_roundtrip_with_tokens() -> None:
    """get_state/load_state preserves total_tokens (backward compat: missing => 0)."""
    tracker = BudgetTracker()
    tracker.record(
        CostInfo(
            cost_usd=0.5,
            token_usage=TokenUsage(total_tokens=500),
        )
    )
    state = tracker.get_state()
    assert state["cost_history"][0]["total_tokens"] == 500

    tracker2 = BudgetTracker()
    tracker2.load_state(state)
    assert tracker2.current_run_cost == 0.5
    assert tracker2.current_run_tokens == 500


def test_budget_tracker_load_state_backward_compat_no_total_tokens() -> None:
    """Old state without total_tokens loads with 0 tokens per entry."""
    state = {
        "cost_history": [
            {"cost_usd": 1.0, "timestamp": 1000.0, "model_name": "gpt-4"},
        ],
        "run_start": 999.0,
    }
    tracker = BudgetTracker()
    tracker.load_state(state)
    assert tracker.current_run_cost == 1.0
    assert tracker.current_run_tokens == 0


def test_budget_threshold_window_run_default() -> None:
    """BudgetThreshold defaults to window='run'."""
    from syrin.threshold import BudgetThreshold

    t = BudgetThreshold(at=80, action=lambda _: None)
    assert getattr(t, "window", "run") == "run"


def test_budget_threshold_window_hour() -> None:
    """Threshold with window=hour uses hourly cost vs per.hour."""
    from syrin.threshold import BudgetThreshold

    tracker = BudgetTracker()
    tracker.record(CostInfo(cost_usd=4.0, token_usage=TokenUsage()))  # 4 in hour
    budget = Budget(
        run=100.0,  # run not exceeded
        per=RateLimit(hour=5.0),
        thresholds=[BudgetThreshold(at=80, action=lambda _: None, window="hour")],
    )
    triggered = tracker.check_thresholds(budget)
    assert len(triggered) == 1  # 4/5 = 80%
    assert triggered[0].window == "hour"


def test_budget_threshold_window_day() -> None:
    """Threshold with window=day uses daily cost vs per.day."""
    from syrin.threshold import BudgetThreshold

    tracker = BudgetTracker()
    tracker.record(CostInfo(cost_usd=8.0, token_usage=TokenUsage()))
    budget = Budget(
        run=100.0,
        per=RateLimit(day=10.0),
        thresholds=[BudgetThreshold(at=80, action=lambda _: None, window="day")],
    )
    triggered = tracker.check_thresholds(budget)
    assert len(triggered) == 1
    assert triggered[0].window == "day"


def test_budget_threshold_window_month_skipped_when_no_per() -> None:
    """Threshold with window=month and no per.month does not trigger."""
    from syrin.threshold import BudgetThreshold

    tracker = BudgetTracker()
    tracker.record(CostInfo(cost_usd=100.0, token_usage=TokenUsage()))
    budget = Budget(
        run=100.0,
        per=RateLimit(hour=10.0),
        thresholds=[BudgetThreshold(at=80, action=lambda _: None, window="month")],
    )
    triggered = tracker.check_thresholds(budget)
    assert len(triggered) == 0


def test_budget_threshold_window_enum_accepted() -> None:
    """BudgetThreshold accepts ThresholdWindow enum (preferred) or string."""
    from syrin.enums import ThresholdWindow
    from syrin.threshold import BudgetThreshold

    t1 = BudgetThreshold(at=80, action=lambda _: None, window=ThresholdWindow.HOUR)
    assert t1.window == ThresholdWindow.HOUR
    t2 = BudgetThreshold(at=80, action=lambda _: None, window="day")
    assert t2.window == ThresholdWindow.DAY


def test_budget_threshold_window_invalid_raises() -> None:
    """BudgetThreshold with invalid window raises."""
    from syrin.threshold import BudgetThreshold

    with pytest.raises(ValueError, match="invalid|ThresholdWindow"):
        BudgetThreshold(at=80, action=lambda _: None, window="invalid")  # type: ignore


def test_budget_consume_no_callback_no_op() -> None:
    """Budget.consume with no callback set does nothing."""
    b = Budget(run=10.0)
    b.consume(1.0)  # no callback, no raise
    assert b._spent == 0.0


def test_budget_consume_zero_or_negative_no_op() -> None:
    """Budget.consume(0) or negative does not call callback."""
    b = Budget(run=10.0)
    calls = []

    def cb(amount: float) -> None:
        calls.append(amount)

    b._consume_callback = cb
    b.consume(0.0)
    b.consume(-1.0)
    assert calls == []


def test_budget_reserve_equals_run_remaining_based_on_spent_only() -> None:
    """When reserve >= run, effective limit is run (remaining clamped to 0)."""
    b = Budget(run=5.0, reserve=5.0)
    b._set_spent(0)
    assert b.remaining == 0.0  # (5 - 5) - 0


def test_budget_reserve_exceeds_run_remaining_clamped_to_zero() -> None:
    """When reserve > run, remaining is clamped to 0 (never negative)."""
    b = Budget(run=5.0, reserve=10.0)
    b._set_spent(0)
    assert b.remaining == 0.0


def test_budget_tracker_check_budget_no_token_limits_no_token_check() -> None:
    """Without token_limits, no token limit check (Budget is USD only)."""
    tracker = BudgetTracker()
    tracker.record(
        CostInfo(
            cost_usd=0.01,
            token_usage=TokenUsage(total_tokens=100_000),
        )
    )
    assert tracker.check_budget(Budget(run=10.0)) == BudgetStatus.OK
