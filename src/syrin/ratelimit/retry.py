"""Retry logic for rate limit handling.

Provides automatic retry with exponential backoff when hitting 429 errors.
Integrates with the agent to automatically handle rate limit responses.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from syrin.enums import RetryBackoff

if TYPE_CHECKING:
    from syrin.ratelimit.config import APIRateLimit


class RateLimitRetryHandler:
    """Handles retry logic for rate limit errors.

    Reads retry parameters directly from an ``APIRateLimit`` instance.
    Use this to wrap operations that may hit rate limits and automatically
    retry with configurable backoff.

    Args:
        config: APIRateLimit instance providing retry_* fields.
    """

    def __init__(self, config: APIRateLimit) -> None:
        self.config = config

    def calculate_backoff(self, attempt: int, retry_after: int | None = None) -> float:
        """Calculate backoff delay for the given attempt.

        Args:
            attempt: Zero-based attempt number (0 = first retry)
            retry_after: Optional Retry-After header value in seconds

        Returns:
            Delay in seconds
        """
        if retry_after is not None and retry_after > 0:
            return min(float(retry_after), self.config.retry_max_delay)

        base = self.config.retry_base_delay
        if self.config.retry_backoff == RetryBackoff.EXPONENTIAL:
            delay = base * (2**attempt)
        elif self.config.retry_backoff == RetryBackoff.LINEAR:
            delay = base * (attempt + 1)
        else:  # CONSTANT
            delay = base

        delay = min(delay, self.config.retry_max_delay)

        if self.config.retry_jitter:
            import random

            delay = delay * (0.5 + random.random())  # 50–150% of delay

        return float(delay)

    def should_retry(self, attempt: int, status_code: int | None = None) -> bool:
        """Determine if we should retry.

        Args:
            attempt: Current attempt number
            status_code: HTTP status code if available

        Returns:
            True if we should retry
        """
        if attempt >= self.config.retry_max:
            return False

        if status_code is not None:
            return status_code in self.config.retry_on_status

        return True

    async def execute_with_retry(  # type: ignore[explicit-any]
        self,
        operation: Callable[[], Any],
        is_rate_limit: Callable[[Any], bool] | None = None,
    ) -> object:
        """Execute an operation with automatic retry on rate limits.

        Args:
            operation: Async function to execute (must return awaitable when called)
            is_rate_limit: Optional function to check if result is a rate limit error

        Returns:
            Result of operation

        Raises:
            Last exception if all retries exhausted
        """
        from collections.abc import Awaitable

        last_error: Exception | None = None

        for attempt in range(self.config.retry_max + 1):
            try:
                result = operation()
                if isinstance(result, Awaitable):
                    result = await result

                if is_rate_limit and is_rate_limit(result) and self.should_retry(attempt, 429):
                    delay = self.calculate_backoff(attempt)
                    await asyncio.sleep(delay)
                    continue

                return result

            except Exception as e:
                last_error = e

                if self._is_rate_limit_error(e) and self.should_retry(attempt):
                    delay = self.calculate_backoff(attempt)
                    await asyncio.sleep(delay)
                else:
                    raise

        raise last_error if last_error else RuntimeError("Retry failed without exception")

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if an exception is a rate limit error."""
        error_str = str(error).lower()
        if "rate" in error_str and ("limit" in error_str or "429" in error_str):
            return True
        if "429" in error_str or "too many requests" in error_str:
            return True
        return "rate_limit" in error_str or "ratelimit" in error_str


__all__ = [
    "RateLimitRetryHandler",
]
