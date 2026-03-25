"""Retry logic for rate limit handling.

Provides automatic retry with exponential backoff when hitting 429 errors.
Integrates with the agent to automatically handle rate limit responses.
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from syrin.enums import RetryBackoff


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Args:
        max_retries: Maximum number of retry attempts (default 3)
        base_delay: Initial delay in seconds (default 1.0)
        max_delay: Maximum delay in seconds (default 60.0)
        backoff_strategy: Exponential, linear, or constant (default exponential)
        jitter: Add random jitter to prevent thundering herd (default True)
        retry_on_status: HTTP status codes to retry on (default [429])
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_strategy: RetryBackoff = RetryBackoff.EXPONENTIAL
    jitter: bool = True
    retry_on_status: list[int] = field(default_factory=lambda: [429])

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number.

        Args:
            attempt: Zero-based attempt number (0 = first retry)

        Returns:
            Delay in seconds
        """
        if self.backoff_strategy == RetryBackoff.EXPONENTIAL:
            delay = self.base_delay * (2**attempt)
        elif self.backoff_strategy == RetryBackoff.LINEAR:
            delay = self.base_delay * (attempt + 1)
        else:  # CONSTANT
            delay = self.base_delay

        delay = float(min(delay, self.max_delay))

        if self.jitter:
            import random

            delay = float(delay * (0.5 + random.random()))  # 50-150% of delay

        return delay


class RateLimitRetryHandler:
    """Handles retry logic for rate limit errors.

    This class can be used to wrap operations that may hit rate limits
    and automatically retry with exponential backoff.
    """

    def __init__(self, config: RetryConfig | None = None):
        self.config = config or RetryConfig()

    def calculate_backoff(self, attempt: int, retry_after: int | None = None) -> float:
        """Calculate backoff delay.

        Args:
            attempt: Attempt number (0-indexed)
            retry_after: Optional Retry-After header value in seconds

        Returns:
            Delay in seconds
        """
        if retry_after is not None and retry_after > 0:
            return min(retry_after, self.config.max_delay)
        return self.config.calculate_delay(attempt)

    def should_retry(self, attempt: int, status_code: int | None = None) -> bool:
        """Determine if we should retry.

        Args:
            attempt: Current attempt number
            status_code: HTTP status code if available

        Returns:
            True if we should retry
        """
        if attempt >= self.config.max_retries:
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

        for attempt in range(self.config.max_retries + 1):
            try:
                result = operation()
                if isinstance(result, Awaitable):
                    result = await result

                # Check if result indicates rate limit
                if is_rate_limit and is_rate_limit(result) and self.should_retry(attempt, 429):
                    delay = self.calculate_backoff(attempt)
                    await asyncio.sleep(delay)
                    continue

                return result

            except Exception as e:
                last_error = e

                # Check if it's a rate limit error
                is_ratelimit = self._is_rate_limit_error(e)

                if is_ratelimit and self.should_retry(attempt):
                    delay = self.calculate_backoff(attempt)
                    await asyncio.sleep(delay)
                else:
                    raise

        raise last_error if last_error else RuntimeError("Retry failed without exception")

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if an exception is a rate limit error.

        Supports OpenAI, Anthropic, and generic rate limit errors.
        """
        error_str = str(error).lower()

        # Check error type and message
        if isinstance(error, Exception):
            if "rate" in error_str and ("limit" in error_str or "429" in error_str):
                return True
            if "429" in error_str or "too many requests" in error_str:
                return True
            if "rate_limit" in error_str or "ratelimit" in error_str:
                return True

        return False


def create_retry_handler(
    max_retries: int = 3,
    base_delay: float = 1.0,
    strategy: RetryBackoff = RetryBackoff.EXPONENTIAL,
) -> RateLimitRetryHandler:
    """Factory function to create a retry handler.

    Args:
        max_retries: Maximum retry attempts
        base_delay: Initial delay in seconds
        strategy: Backoff strategy

    Returns:
        Configured RateLimitRetryHandler
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        backoff_strategy=strategy,
    )
    return RateLimitRetryHandler(config)


__all__ = [
    "RetryConfig",
    "RateLimitRetryHandler",
    "create_retry_handler",
]
