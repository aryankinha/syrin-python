"""Sampling strategies for observability.

This module provides sampling strategies to control which traces
are recorded, helping manage cost and storage for high-volume agents.

Example:
    >>> from syrin.observability.sampling import SamplingPolicy, Sampler
    >>>
    >>> # Sample 10% of traces
    >>> policy = SamplingPolicy(rate=0.1)
    >>>
    >>> # Sample based on conditions
    >>> policy = SamplingPolicy(
    ...     rate=1.0,
    ...     sample_errors=True,
    ...     sample_slow_traces=True,
    ...     slow_threshold_ms=5000,
    ... )
    >>>
    >>> sampler = Sampler(policy)
    >>> if sampler.should_sample():
    ...     # Record trace
"""

from __future__ import annotations

import hashlib
import random
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass

from syrin.observability import Span


@dataclass
class SamplingPolicy:
    """Policy for determining which traces to sample.

    Attributes:
        rate: Sample rate (0.0 to 1.0).
        sample_errors: Always sample traces with errors.
        sample_slow_traces: Always sample slow traces.
        slow_threshold_ms: Threshold for slow traces (ms).
        sample_expensive: Always sample expensive traces.
        expensive_threshold_usd: Threshold for expensive traces (USD).
        sample_by_attribute: Sample by attribute match (dict).
    """

    rate: float = 1.0  # Sample rate (0.0 to 1.0)
    sample_errors: bool = True  # Always sample traces with errors
    sample_slow_traces: bool = True  # Always sample slow traces
    slow_threshold_ms: float = 5000  # Threshold for slow traces (ms)
    sample_expensive: bool = True  # Always sample expensive traces
    expensive_threshold_usd: float = 1.0  # Threshold for expensive traces
    sample_by_attribute: dict[str, object] | None = None  # Sample by attribute match

    # For head-based sampling
    initial_sample_rate: float = 1.0  # Sample rate before any decision
    min_initial_samples: int = 100  # Minimum samples to collect before adjusting

    def __post_init__(self) -> None:
        if not 0.0 <= self.rate <= 1.0:
            raise ValueError("rate must be between 0.0 and 1.0")


class Sampler(ABC):
    """Abstract base class for samplers."""

    @abstractmethod
    def should_sample(self, span: Span | None = None) -> bool:
        """Determine if a span should be sampled."""
        ...


class ProbabilisticSampler(Sampler):
    """Simple probabilistic sampler."""

    def __init__(self, policy: SamplingPolicy) -> None:
        self._policy = policy

    def should_sample(self, span: Span | None = None) -> bool:
        """Sample based on probability."""
        if span is None:
            return random.random() < self._policy.rate

        # Always sample errors if configured
        if self._policy.sample_errors and span.status.value == "error":
            return True

        # Always sample slow traces if configured
        if self._policy.sample_slow_traces and span.duration_ms > self._policy.slow_threshold_ms:
            return True

        # Always sample expensive traces if configured
        if self._policy.sample_expensive:
            cost = span.attributes.get("llm.cost", 0) or span.attributes.get("budget.used", 0)
            if cost and cost > self._policy.expensive_threshold_usd:  # type: ignore[operator]
                return True

        # Check attribute-based sampling
        if self._policy.sample_by_attribute:
            for key, value in self._policy.sample_by_attribute.items():
                if span.attributes.get(key) == value:
                    return True

        # Probabilistic sampling
        return random.random() < self._policy.rate


class DeterministicSampler(Sampler):
    """Deterministic sampler based on trace ID hash."""

    def __init__(self, policy: SamplingPolicy) -> None:
        self._policy = policy

    def should_sample(self, span: Span | None = None) -> bool:
        """Sample based on trace ID hash."""
        if span is None:
            return random.random() < self._policy.rate

        # Use trace ID for deterministic sampling
        hash_value = int(hashlib.md5(span.trace_id.encode()).hexdigest(), 16)
        sample_value = (hash_value % 1000) / 1000.0

        return sample_value < self._policy.rate


class RateLimitingSampler(Sampler):
    """Rate-limiting sampler that limits samples per second."""

    def __init__(
        self,
        policy: SamplingPolicy,
        max_samples_per_second: float = 10.0,
    ) -> None:
        self._policy = policy
        self._max_samples_per_second = max_samples_per_second
        self._lock = threading.Lock()
        self._last_sample_time = 0.0
        self._min_interval = 1.0 / max_samples_per_second

    def should_sample(self, span: Span | None = None) -> bool:
        """Sample with rate limiting."""
        with self._lock:
            current_time = time.time()

            # Always sample errors regardless of rate limit
            if span is not None and self._policy.sample_errors and span.status.value == "error":
                return True

            # Check rate limit
            if current_time - self._last_sample_time >= self._min_interval:
                self._last_sample_time = current_time
                return True

            return False


class AdaptiveSampler(Sampler):
    """Adaptive sampler that adjusts rate based on error rate."""

    def __init__(
        self,
        policy: SamplingPolicy,
        target_error_rate: float = 0.1,
    ) -> None:
        self._policy = policy
        self._target_error_rate = target_error_rate
        self._lock = threading.Lock()
        self._total_samples = 0
        self._error_samples = 0
        self._current_rate = policy.rate

    def should_sample(self, span: Span | None = None) -> bool:
        """Sample with adaptive rate based on error rate."""
        with self._lock:
            # Always sample errors
            if span is not None:
                self._total_samples += 1
                if span.status.value == "error":
                    self._error_samples += 1

                    # Adjust rate based on error rate
                    if self._total_samples >= self._policy.min_initial_samples:
                        error_rate = self._error_samples / self._total_samples

                        # Increase sampling if error rate is high
                        if error_rate > self._target_error_rate:
                            self._current_rate = min(1.0, self._current_rate * 1.5)
                        # Decrease sampling if error rate is low
                        elif error_rate < self._target_error_rate * 0.5:
                            self._current_rate = max(0.01, self._current_rate * 0.8)

            if span is None:
                return random.random() < self._current_rate

            # Use current rate for sampling
            return random.random() < self._current_rate

    def get_current_rate(self) -> float:
        """Get the current sampling rate."""
        return self._current_rate


class CompositeSampler(Sampler):
    """Composite sampler that combines multiple samplers."""

    def __init__(
        self,
        samplers: list[Sampler],
        mode: str = "any",  # "any" or "all"
    ) -> None:
        self._samplers = samplers
        self._mode = mode

    def should_sample(self, span: Span | None = None) -> bool:
        """Sample if any/all samplers say to sample."""
        if self._mode == "any":
            return any(s.should_sample(span) for s in self._samplers)
        return all(s.should_sample(span) for s in self._samplers)


class ConditionalSampler(Sampler):
    """Sampler that uses a custom condition function."""

    def __init__(
        self,
        condition: Callable[[Span | None], bool],
    ) -> None:
        self._condition = condition

    def should_sample(self, span: Span | None = None) -> bool:
        """Sample based on custom condition."""
        return self._condition(span)


# Factory function
def create_sampler(
    strategy: str = "probabilistic",
    **kwargs: object,
) -> Sampler:
    """Create a sampler based on strategy name.

    Args:
        strategy: Sampler strategy ("probabilistic", "deterministic",
                  "rate_limiting", "adaptive", "composite", "conditional")
        **kwargs: Additional arguments for the sampler

    Returns:
        A Sampler instance
    """
    if strategy == "probabilistic":
        return ProbabilisticSampler(SamplingPolicy(**kwargs))  # type: ignore[arg-type]
    elif strategy == "deterministic":
        return DeterministicSampler(SamplingPolicy(**kwargs))  # type: ignore[arg-type]
    elif strategy == "rate_limiting":
        return RateLimitingSampler(
            SamplingPolicy(**kwargs),  # type: ignore[arg-type]
            max_samples_per_second=kwargs.get("max_samples_per_second", 10.0),  # type: ignore[arg-type]
        )
    elif strategy == "adaptive":
        return AdaptiveSampler(
            SamplingPolicy(**kwargs),  # type: ignore[arg-type]
            target_error_rate=kwargs.get("target_error_rate", 0.1),  # type: ignore[arg-type]
        )
    elif strategy == "composite":
        sub_samplers = kwargs.get("samplers", [])
        mode = kwargs.get("mode", "any")
        return CompositeSampler(sub_samplers, mode)  # type: ignore[arg-type]
    elif strategy == "conditional":
        condition = kwargs.get("condition", lambda _: True)
        return ConditionalSampler(condition)  # type: ignore[arg-type]
    else:
        raise ValueError(f"Unknown sampler strategy: {strategy}")


__all__ = [
    "SamplingPolicy",
    "Sampler",
    "ProbabilisticSampler",
    "DeterministicSampler",
    "RateLimitingSampler",
    "AdaptiveSampler",
    "CompositeSampler",
    "ConditionalSampler",
    "create_sampler",
]
