"""Rate limit configuration: RetryConfig absorption into APIRateLimit flat fields.

Verifies:
- retry_* flat fields on APIRateLimit
- RetryConfig removed from public ratelimit module
- RateLimitRetryHandler uses APIRateLimit fields
"""

from __future__ import annotations

from syrin.enums import RetryBackoff
from syrin.ratelimit import APIRateLimit
from syrin.ratelimit.retry import RateLimitRetryHandler


class TestAPIRateLimitRetryFields:
    """APIRateLimit has flat retry_* fields."""

    def test_default_retry_fields(self) -> None:
        """Default retry values match RetryConfig defaults."""
        limit = APIRateLimit(rpm=100)
        assert limit.retry_max == 3
        assert limit.retry_base_delay == 1.0
        assert limit.retry_max_delay == 60.0
        assert limit.retry_backoff == RetryBackoff.EXPONENTIAL
        assert limit.retry_jitter is True
        assert limit.retry_on_status == [429]

    def test_custom_retry_fields(self) -> None:
        """Custom retry values are stored correctly."""
        limit = APIRateLimit(
            rpm=100,
            retry_max=5,
            retry_base_delay=2.0,
            retry_max_delay=30.0,
            retry_backoff=RetryBackoff.LINEAR,
            retry_jitter=False,
            retry_on_status=[429, 503],
        )
        assert limit.retry_max == 5
        assert limit.retry_base_delay == 2.0
        assert limit.retry_max_delay == 30.0
        assert limit.retry_backoff == RetryBackoff.LINEAR
        assert limit.retry_jitter is False
        assert limit.retry_on_status == [429, 503]

    def test_retry_on_429_field_removed(self) -> None:
        """retry_on_429 is removed; use retry_on_status instead."""
        limit = APIRateLimit(rpm=100)
        assert not hasattr(limit, "retry_on_429"), "retry_on_429 should be removed"

    def test_max_retries_field_removed(self) -> None:
        """max_retries is removed; use retry_max instead."""
        limit = APIRateLimit(rpm=100)
        assert not hasattr(limit, "max_retries"), "max_retries should be removed"

    def test_retry_backoff_constant(self) -> None:
        """CONSTANT backoff strategy is accepted."""
        limit = APIRateLimit(rpm=100, retry_backoff=RetryBackoff.CONSTANT)
        assert limit.retry_backoff == RetryBackoff.CONSTANT

    def test_retry_max_zero_disables_retry(self) -> None:
        """retry_max=0 disables retry."""
        limit = APIRateLimit(rpm=100, retry_max=0)
        assert limit.retry_max == 0


class TestRetryConfigRemovedFromPublicAPI:
    """RetryConfig is not exported from syrin.ratelimit."""

    def test_retry_config_not_in_ratelimit_module(self) -> None:
        """RetryConfig is not importable from syrin.ratelimit."""
        import syrin.ratelimit as rl

        assert not hasattr(rl, "RetryConfig"), "RetryConfig must be removed from public API"

    def test_create_retry_handler_not_in_ratelimit_module(self) -> None:
        """create_retry_handler is not exported from syrin.ratelimit."""
        import syrin.ratelimit as rl

        assert not hasattr(rl, "create_retry_handler")

    def test_retry_config_not_in_syrin_root(self) -> None:
        """RetryConfig is not in syrin root."""
        import syrin

        assert not hasattr(syrin, "RetryConfig")


class TestRateLimitRetryHandlerUsesAPIRateLimit:
    """RateLimitRetryHandler accepts APIRateLimit and uses its retry_* fields."""

    def test_handler_from_api_rate_limit(self) -> None:
        """RateLimitRetryHandler can be constructed from APIRateLimit."""
        config = APIRateLimit(rpm=100, retry_max=5, retry_base_delay=2.0)
        handler = RateLimitRetryHandler(config)
        assert handler.config is config

    def test_should_retry_respects_retry_max(self) -> None:
        """should_retry uses retry_max from APIRateLimit."""
        config = APIRateLimit(rpm=100, retry_max=2)
        handler = RateLimitRetryHandler(config)
        assert handler.should_retry(0) is True
        assert handler.should_retry(1) is True
        assert handler.should_retry(2) is False

    def test_should_retry_respects_retry_on_status(self) -> None:
        """should_retry uses retry_on_status from APIRateLimit."""
        config = APIRateLimit(rpm=100, retry_on_status=[429, 503])
        handler = RateLimitRetryHandler(config)
        assert handler.should_retry(0, status_code=429) is True
        assert handler.should_retry(0, status_code=503) is True
        assert handler.should_retry(0, status_code=500) is False

    def test_calculate_delay_exponential(self) -> None:
        """calculate_delay uses retry_backoff=EXPONENTIAL."""
        config = APIRateLimit(rpm=100, retry_base_delay=1.0, retry_jitter=False)
        handler = RateLimitRetryHandler(config)
        assert handler.calculate_backoff(0) == 1.0
        assert handler.calculate_backoff(1) == 2.0
        assert handler.calculate_backoff(2) == 4.0

    def test_calculate_delay_linear(self) -> None:
        """calculate_delay uses retry_backoff=LINEAR."""
        config = APIRateLimit(
            rpm=100, retry_base_delay=2.0, retry_backoff=RetryBackoff.LINEAR, retry_jitter=False
        )
        handler = RateLimitRetryHandler(config)
        assert handler.calculate_backoff(0) == 2.0
        assert handler.calculate_backoff(1) == 4.0
        assert handler.calculate_backoff(2) == 6.0

    def test_calculate_delay_respects_max_delay(self) -> None:
        """calculate_delay caps at retry_max_delay."""
        config = APIRateLimit(
            rpm=100, retry_base_delay=10.0, retry_max_delay=15.0, retry_jitter=False
        )
        handler = RateLimitRetryHandler(config)
        # attempt 3: 10 * 2^3 = 80, capped at 15
        assert handler.calculate_backoff(3) == 15.0

    def test_jitter_adds_variance(self) -> None:
        """With retry_jitter=True, delays vary between calls."""
        config = APIRateLimit(rpm=100, retry_base_delay=10.0, retry_jitter=True)
        handler = RateLimitRetryHandler(config)
        delays = {handler.calculate_backoff(0) for _ in range(10)}
        assert len(delays) > 1, "Jitter should produce different values"
