"""TDD tests for Response cost transparency fields.

Verifies:
- Response.cost_estimated defaults to None
- Response.cache_hit defaults to False
- Response.cache_savings defaults to 0.0
- Response.actual_cost defaults to None
- Fields are correctly typed and settable
- Response.cost reflects the run cost
- All fields are independent (setting one doesn't affect others)
- Edge cases: zero cost, negative savings (not expected but shouldn't crash), large values
"""

from __future__ import annotations

import pytest

from syrin.enums import StopReason
from syrin.response import Response
from syrin.types import TokenUsage


def _make_response(**kwargs: object) -> Response[str]:
    defaults: dict[str, object] = {
        "content": "Hello",
        "cost": 0.0,
        "tokens": TokenUsage(),
        "model": "openai/gpt-4o-mini",
        "duration": 0.1,
        "stop_reason": StopReason.END_TURN,
    }
    defaults.update(kwargs)
    return Response(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------


class TestCostTransparencyDefaults:
    def test_cost_estimated_defaults_to_none(self) -> None:
        r = _make_response()
        assert r.cost_estimated is None

    def test_cache_hit_defaults_to_false(self) -> None:
        r = _make_response()
        assert r.cache_hit is False

    def test_cache_savings_defaults_to_zero(self) -> None:
        r = _make_response()
        assert r.cache_savings == pytest.approx(0.0)

    def test_actual_cost_defaults_to_none(self) -> None:
        r = _make_response()
        assert r.actual_cost is None

    def test_cost_defaults_to_zero(self) -> None:
        r = _make_response()
        assert r.cost == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Setting cost_estimated
# ---------------------------------------------------------------------------


class TestCostEstimated:
    def test_can_set_cost_estimated(self) -> None:
        r = _make_response(cost_estimated=0.0015)
        assert r.cost_estimated == pytest.approx(0.0015)

    def test_cost_estimated_none_when_not_estimated(self) -> None:
        r = _make_response(cost_estimated=None)
        assert r.cost_estimated is None

    def test_cost_estimated_zero_is_valid(self) -> None:
        r = _make_response(cost_estimated=0.0)
        assert r.cost_estimated == pytest.approx(0.0)

    def test_cost_estimated_large_value(self) -> None:
        r = _make_response(cost_estimated=99.9999)
        assert r.cost_estimated == pytest.approx(99.9999)

    def test_cost_estimated_independent_of_actual_cost(self) -> None:
        r = _make_response(cost_estimated=0.001, actual_cost=0.002)
        assert r.cost_estimated == pytest.approx(0.001)
        assert r.actual_cost == pytest.approx(0.002)
        assert r.cost_estimated != r.actual_cost


# ---------------------------------------------------------------------------
# cache_hit
# ---------------------------------------------------------------------------


class TestCacheHit:
    def test_cache_hit_true(self) -> None:
        r = _make_response(cache_hit=True)
        assert r.cache_hit is True

    def test_cache_hit_false(self) -> None:
        r = _make_response(cache_hit=False)
        assert r.cache_hit is False

    def test_cache_hit_is_bool(self) -> None:
        r = _make_response(cache_hit=True)
        assert isinstance(r.cache_hit, bool)


# ---------------------------------------------------------------------------
# cache_savings
# ---------------------------------------------------------------------------


class TestCacheSavings:
    def test_cache_savings_set_correctly(self) -> None:
        r = _make_response(cache_savings=0.0042)
        assert r.cache_savings == pytest.approx(0.0042)

    def test_cache_savings_zero(self) -> None:
        r = _make_response(cache_savings=0.0)
        assert r.cache_savings == pytest.approx(0.0)

    def test_cache_savings_is_float(self) -> None:
        r = _make_response(cache_savings=0.5)
        assert isinstance(r.cache_savings, float)

    def test_cache_savings_when_no_cache_hit(self) -> None:
        """cache_savings should be 0.0 when cache_hit is False."""
        r = _make_response(cache_hit=False, cache_savings=0.0)
        assert r.cache_savings == pytest.approx(0.0)

    def test_cache_savings_when_cache_hit(self) -> None:
        """cache_savings can be positive when cache_hit is True."""
        r = _make_response(cache_hit=True, cache_savings=0.005)
        assert r.cache_hit is True
        assert r.cache_savings == pytest.approx(0.005)


# ---------------------------------------------------------------------------
# actual_cost
# ---------------------------------------------------------------------------


class TestActualCost:
    def test_actual_cost_can_be_set(self) -> None:
        r = _make_response(actual_cost=0.0031)
        assert r.actual_cost == pytest.approx(0.0031)

    def test_actual_cost_none_when_provider_doesnt_return(self) -> None:
        r = _make_response(actual_cost=None)
        assert r.actual_cost is None

    def test_actual_cost_zero_is_valid(self) -> None:
        r = _make_response(actual_cost=0.0)
        assert r.actual_cost == pytest.approx(0.0)

    def test_actual_cost_independent_of_cost(self) -> None:
        """actual_cost from provider may differ from computed cost."""
        r = _make_response(cost=0.003, actual_cost=0.0028)
        assert r.cost == pytest.approx(0.003)
        assert r.actual_cost == pytest.approx(0.0028)


# ---------------------------------------------------------------------------
# Full response with all cost transparency fields
# ---------------------------------------------------------------------------


class TestFullCostTransparency:
    def test_all_fields_together(self) -> None:
        r = _make_response(
            cost=0.003,
            actual_cost=0.0028,
            cost_estimated=0.0025,
            cache_hit=True,
            cache_savings=0.0005,
        )
        assert r.cost == pytest.approx(0.003)
        assert r.actual_cost == pytest.approx(0.0028)
        assert r.cost_estimated == pytest.approx(0.0025)
        assert r.cache_hit is True
        assert r.cache_savings == pytest.approx(0.0005)

    def test_budget_fields_also_present(self) -> None:
        r = _make_response(
            cost=0.01,
            budget_remaining=4.99,
            budget_used=0.01,
        )
        assert r.budget_remaining == pytest.approx(4.99)
        assert r.budget_used == pytest.approx(0.01)

    def test_no_cache_scenario(self) -> None:
        """Typical response with no caching."""
        r = _make_response(
            cost=0.005,
            actual_cost=0.005,
            cost_estimated=0.004,
            cache_hit=False,
            cache_savings=0.0,
        )
        assert r.cache_hit is False
        assert r.cache_savings == pytest.approx(0.0)
        assert r.cost_estimated is not None
        assert r.cost_estimated < r.cost  # estimate was a bit low

    def test_cost_savings_not_larger_than_cost(self) -> None:
        """Sanity: savings shouldn't exceed the original cost."""
        r = _make_response(cost=0.01, cache_savings=0.005)
        assert r.cache_savings <= r.cost
