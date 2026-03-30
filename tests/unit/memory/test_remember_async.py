"""remember() in ASYNC mode must return a Future so callers can propagate failures.

Tests that:
- In SYNC mode: remember() returns bool (True on success, False on failure)
- In ASYNC mode: remember() returns a concurrent.futures.Future[bool]
- The Future resolves to True on success
- The Future resolves to False (or raises) when the backend write fails
- Truthy check on Future still works for callers who ignore the result
"""

from __future__ import annotations

import concurrent.futures

from syrin.enums import WriteMode
from syrin.memory.config import Memory


class TestRememberAsyncWrite:
    def test_sync_mode_returns_bool(self) -> None:
        """In SYNC mode, remember() returns bool True on success."""
        mem = Memory(write_mode=WriteMode.SYNC)
        result = mem.remember("test content")
        assert isinstance(result, bool)
        assert result is True

    def test_async_mode_returns_future(self) -> None:
        """In ASYNC mode, remember() returns a concurrent.futures.Future."""
        mem = Memory(write_mode=WriteMode.ASYNC)
        result = mem.remember("test content")
        assert isinstance(result, concurrent.futures.Future), (
            f"Expected Future in ASYNC mode, got {type(result).__name__}"
        )

    def test_async_future_resolves_true_on_success(self) -> None:
        """Future from async remember() resolves to True when write succeeds."""
        mem = Memory(write_mode=WriteMode.ASYNC)
        future = mem.remember("test content")
        assert isinstance(future, concurrent.futures.Future)
        result = future.result(timeout=5.0)
        assert result is True

    def test_async_future_resolves_false_on_backend_failure(self) -> None:
        """Future resolves to False when the backend write fails."""
        mem = Memory(write_mode=WriteMode.ASYNC)

        # Patch _remember_sync to raise

        def failing_sync(*args, **kwargs):  # type: ignore[no-untyped-def]
            return False

        mem._remember_sync = failing_sync  # type: ignore[method-assign]

        future = mem.remember("test content")
        assert isinstance(future, concurrent.futures.Future)
        result = future.result(timeout=5.0)
        assert result is False

    def test_async_future_is_truthy(self) -> None:
        """A pending/completed Future is truthy — existing code that does `if mem.remember(...)` still works."""
        mem = Memory(write_mode=WriteMode.ASYNC)
        future = mem.remember("test content")
        assert future  # Truthy check still works
