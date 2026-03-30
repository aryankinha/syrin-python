"""Circuit breaker concurrency correctness in HALF_OPEN state.

Tests that:
- Only half_open_max requests are allowed through in HALF_OPEN state under concurrent load
- Concurrent allow_request() calls don't both see half_open_attempts < half_open_max
- State transitions (OPEN→HALF_OPEN) are atomic under concurrent access
"""

from __future__ import annotations

import threading
import time

from syrin.circuit._breaker import CircuitBreaker
from syrin.enums import CircuitState


class TestCircuitBreakerHalfOpenConcurrency:
    def _trip_to_open(self, cb: CircuitBreaker) -> None:
        """Trip the circuit to OPEN state."""
        for _ in range(cb.failure_threshold):
            cb.record_failure()

    def test_allow_request_half_open_atomic_single_thread(self) -> None:
        """Single-thread: allow_request() in HALF_OPEN allows exactly half_open_max requests."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1, half_open_max=1)
        self._trip_to_open(cb)
        # Wait for recovery
        time.sleep(1.1)
        # First allow_request transitions to HALF_OPEN and returns True
        assert cb.allow_request() is True
        # Second should be blocked (at capacity)
        assert cb.allow_request() is False

    def test_allow_request_half_open_concurrent_respects_max(self) -> None:
        """Concurrent allow_request() in HALF_OPEN must not exceed half_open_max=1."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1, half_open_max=1)
        self._trip_to_open(cb)
        time.sleep(1.1)  # Allow recovery_timeout to elapse

        allowed_count = 0
        lock = threading.Lock()
        barrier = threading.Barrier(10)

        def try_allow() -> None:
            nonlocal allowed_count
            barrier.wait()  # All threads start at the same time
            result = cb.allow_request()
            if result:
                with lock:
                    allowed_count += 1

        threads = [threading.Thread(target=try_allow) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert allowed_count == 1, (
            f"Only 1 request should be allowed in HALF_OPEN with half_open_max=1, "
            f"but {allowed_count} got through (race condition)"
        )

    def test_allow_request_half_open_max_2_concurrent(self) -> None:
        """With half_open_max=2, exactly 2 concurrent requests are allowed."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1, half_open_max=2)
        self._trip_to_open(cb)
        time.sleep(1.1)

        allowed_count = 0
        lock = threading.Lock()
        barrier = threading.Barrier(10)

        def try_allow() -> None:
            nonlocal allowed_count
            barrier.wait()
            result = cb.allow_request()
            if result:
                with lock:
                    allowed_count += 1

        threads = [threading.Thread(target=try_allow) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert allowed_count == 2, (
            f"Exactly 2 requests should be allowed (half_open_max=2), got {allowed_count}"
        )

    def test_record_success_thread_safe(self) -> None:
        """Concurrent record_success() calls don't corrupt state."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1, half_open_max=2)
        self._trip_to_open(cb)
        time.sleep(1.1)
        # Allow both probes
        cb.allow_request()
        cb.allow_request()

        barrier = threading.Barrier(2)

        def record_success() -> None:
            barrier.wait()
            cb.record_success()

        threads = [threading.Thread(target=record_success) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # After both successes, should be CLOSED
        assert cb.state == CircuitState.CLOSED
