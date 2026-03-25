"""TDD tests for ExceedPolicy enum integration with Budget and TokenLimits.

Verifies:
- ExceedPolicy enum values and string representation
- Budget.exceed_policy maps to the correct on_exceeded handler
- TokenLimits.exceed_policy maps to the correct on_exceeded handler
- STOP policy raises BudgetExceededError
- WARN policy logs and continues
- IGNORE policy silently continues
- SWITCH policy silently continues (agent handles fallback separately)
- Explicit on_exceeded takes precedence over exceed_policy
- exceed_policy=None leaves on_exceeded as None
"""

from __future__ import annotations

import logging

import pytest

from syrin.budget import (
    Budget,
    BudgetExceededContext,
    BudgetLimitType,
    TokenLimits,
    raise_on_exceeded,
    warn_on_exceeded,
)
from syrin.enums import ExceedPolicy
from syrin.exceptions import BudgetExceededError


def _make_ctx(
    budget_type: BudgetLimitType = BudgetLimitType.RUN,
    current: float = 10.0,
    limit: float = 5.0,
) -> BudgetExceededContext:
    return BudgetExceededContext(
        current_cost=current,
        limit=limit,
        budget_type=budget_type,
        message=f"Budget exceeded: ${current:.4f} >= ${limit:.4f}",
    )


# ---------------------------------------------------------------------------
# ExceedPolicy enum
# ---------------------------------------------------------------------------


class TestExceedPolicyEnum:
    def test_stop_value(self) -> None:
        assert ExceedPolicy.STOP == "stop"

    def test_warn_value(self) -> None:
        assert ExceedPolicy.WARN == "warn"

    def test_switch_value(self) -> None:
        assert ExceedPolicy.SWITCH == "switch"

    def test_ignore_value(self) -> None:
        assert ExceedPolicy.IGNORE == "ignore"

    def test_is_str(self) -> None:
        """ExceedPolicy values are plain strings (StrEnum)."""
        assert isinstance(ExceedPolicy.STOP, str)
        assert isinstance(ExceedPolicy.WARN, str)

    def test_all_values_unique(self) -> None:
        values = [p.value for p in ExceedPolicy]
        assert len(values) == len(set(values))

    def test_from_string(self) -> None:
        assert ExceedPolicy("stop") is ExceedPolicy.STOP
        assert ExceedPolicy("warn") is ExceedPolicy.WARN
        assert ExceedPolicy("switch") is ExceedPolicy.SWITCH
        assert ExceedPolicy("ignore") is ExceedPolicy.IGNORE

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            ExceedPolicy("invalid")


# ---------------------------------------------------------------------------
# Budget.exceed_policy integration
# ---------------------------------------------------------------------------


class TestBudgetExceedPolicy:
    def test_no_policy_leaves_on_exceeded_none(self) -> None:
        b = Budget(max_cost=1.0)
        assert b.on_exceeded is None

    def test_stop_policy_sets_raise_handler(self) -> None:
        b = Budget(max_cost=1.0, exceed_policy=ExceedPolicy.STOP)
        assert b.on_exceeded is not None
        # STOP handler should raise BudgetExceededError
        with pytest.raises(BudgetExceededError):
            b.on_exceeded(_make_ctx())

    def test_warn_policy_sets_warn_handler(self, caplog: pytest.LogCaptureFixture) -> None:
        b = Budget(max_cost=1.0, exceed_policy=ExceedPolicy.WARN)
        assert b.on_exceeded is not None
        with caplog.at_level(logging.WARNING):
            b.on_exceeded(_make_ctx())  # Should NOT raise
        assert len(caplog.records) > 0

    def test_ignore_policy_continues_silently(self) -> None:
        b = Budget(max_cost=1.0, exceed_policy=ExceedPolicy.IGNORE)
        assert b.on_exceeded is not None
        result = b.on_exceeded(_make_ctx())  # Should NOT raise, returns None
        assert result is None

    def test_switch_policy_continues_silently(self) -> None:
        b = Budget(max_cost=1.0, exceed_policy=ExceedPolicy.SWITCH)
        assert b.on_exceeded is not None
        result = b.on_exceeded(_make_ctx())  # Should NOT raise, returns None
        assert result is None

    def test_explicit_on_exceeded_takes_precedence(self) -> None:
        """When both on_exceeded and exceed_policy are set, on_exceeded wins."""
        called: list[str] = []

        def custom_handler(ctx: BudgetExceededContext) -> None:
            called.append("custom")

        b = Budget(max_cost=1.0, on_exceeded=custom_handler, exceed_policy=ExceedPolicy.STOP)
        # The custom handler (not STOP) should be in effect
        b.on_exceeded(_make_ctx())
        assert called == ["custom"]

    def test_exceed_policy_none_leaves_on_exceeded_none(self) -> None:
        b = Budget(max_cost=1.0, exceed_policy=None)
        assert b.on_exceeded is None

    def test_stop_policy_str_roundtrip(self) -> None:
        b = Budget(max_cost=1.0, exceed_policy=ExceedPolicy.STOP)
        assert b.exceed_policy == "stop"
        assert b.exceed_policy is ExceedPolicy.STOP


# ---------------------------------------------------------------------------
# TokenLimits.exceed_policy integration
# ---------------------------------------------------------------------------


class TestTokenLimitsExceedPolicy:
    def test_no_policy_leaves_on_exceeded_none(self) -> None:
        tl = TokenLimits(max_tokens=1000)
        assert tl.on_exceeded is None

    def test_stop_policy_raises(self) -> None:
        tl = TokenLimits(max_tokens=1000, exceed_policy=ExceedPolicy.STOP)
        assert tl.on_exceeded is not None
        with pytest.raises(BudgetExceededError):
            tl.on_exceeded(_make_ctx(budget_type=BudgetLimitType.RUN_TOKENS))

    def test_warn_policy_continues(self, caplog: pytest.LogCaptureFixture) -> None:
        tl = TokenLimits(max_tokens=1000, exceed_policy=ExceedPolicy.WARN)
        assert tl.on_exceeded is not None
        with caplog.at_level(logging.WARNING):
            tl.on_exceeded(_make_ctx(budget_type=BudgetLimitType.RUN_TOKENS))
        assert len(caplog.records) > 0

    def test_ignore_policy_continues_silently(self) -> None:
        tl = TokenLimits(max_tokens=1000, exceed_policy=ExceedPolicy.IGNORE)
        assert tl.on_exceeded is not None
        result = tl.on_exceeded(_make_ctx(budget_type=BudgetLimitType.RUN_TOKENS))
        assert result is None

    def test_explicit_on_exceeded_takes_precedence(self) -> None:
        called: list[str] = []

        def custom(ctx: BudgetExceededContext) -> None:
            called.append("tl_custom")

        tl = TokenLimits(max_tokens=1000, on_exceeded=custom, exceed_policy=ExceedPolicy.STOP)
        tl.on_exceeded(_make_ctx())
        assert called == ["tl_custom"]


# ---------------------------------------------------------------------------
# STOP vs WARN behaviour contracts
# ---------------------------------------------------------------------------


class TestPolicyHandlerContracts:
    def test_raise_on_exceeded_raises_budget_error(self) -> None:
        ctx = _make_ctx(current=5.0, limit=1.0)
        with pytest.raises(BudgetExceededError):
            raise_on_exceeded(ctx)

    def test_raise_on_exceeded_includes_current_and_limit(self) -> None:
        ctx = _make_ctx(current=7.5, limit=2.0)
        with pytest.raises(BudgetExceededError) as exc_info:
            raise_on_exceeded(ctx)
        err = exc_info.value
        assert err.current_cost == pytest.approx(7.5)
        assert err.limit == pytest.approx(2.0)

    def test_warn_on_exceeded_does_not_raise(self, caplog: pytest.LogCaptureFixture) -> None:
        ctx = _make_ctx()
        with caplog.at_level(logging.WARNING):
            warn_on_exceeded(ctx)  # Must NOT raise

    def test_warn_on_exceeded_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        ctx = _make_ctx(current=9.99, limit=5.0)
        with caplog.at_level(logging.WARNING):
            warn_on_exceeded(ctx)
        assert any(
            "budget" in r.message.lower() or "exceed" in r.message.lower() for r in caplog.records
        )

    def test_stop_policy_budget_type_preserved(self) -> None:
        b = Budget(max_cost=1.0, exceed_policy=ExceedPolicy.STOP)
        ctx = _make_ctx(budget_type=BudgetLimitType.HOUR)
        with pytest.raises(BudgetExceededError) as exc_info:
            b.on_exceeded(ctx)
        # budget_type should be preserved in the exception
        assert exc_info.value.budget_type == BudgetLimitType.HOUR.value
