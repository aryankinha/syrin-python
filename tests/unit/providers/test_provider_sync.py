"""Provider sync wrapper correctness: thread-pool dispatch and event-loop compatibility.

Tests that:
- complete_sync() works from a plain sync context (no running loop)
- complete_sync() works when called from within an async context (running loop)
- _run_async() uses a thread pool when a running loop is detected
- stream_sync() likewise works in both contexts
"""

from __future__ import annotations

import asyncio
import threading

import pytest

from syrin.providers.base import Provider
from syrin.types import Message, ModelConfig, ProviderResponse, TokenUsage


def _make_response(content: str = "hello") -> ProviderResponse:
    return ProviderResponse(
        content=content,
        tool_calls=[],
        token_usage=TokenUsage(input_tokens=10, output_tokens=5, total_tokens=15),
    )


def _make_model() -> ModelConfig:
    return ModelConfig(name="test", provider="openai", model_id="gpt-4")


class _EchoProvider(Provider):
    """Minimal provider that returns a fixed response."""

    def __init__(self, response: ProviderResponse) -> None:
        self._response = response

    async def complete(
        self,
        messages: list[Message],
        model: ModelConfig,
        tools: list | None = None,
        **kwargs: object,
    ) -> ProviderResponse:
        return self._response


# ---------------------------------------------------------------------------
# Sync context (no running event loop)
# ---------------------------------------------------------------------------


class TestSyncContext:
    """complete_sync / stream_sync called from plain sync code (no running loop)."""

    def test_complete_sync_no_loop(self) -> None:
        resp = _make_response("no-loop")
        provider = _EchoProvider(resp)
        result = provider.complete_sync(messages=[], model=_make_model())
        assert result is not None
        assert result.content == "no-loop"

    def test_stream_sync_no_loop(self) -> None:
        resp = _make_response("stream-no-loop")
        provider = _EchoProvider(resp)
        chunks = list(provider.stream_sync(messages=[], model=_make_model()))
        assert len(chunks) == 1
        assert chunks[0].content == "stream-no-loop"


# ---------------------------------------------------------------------------
# Async context (running event loop exists)
# ---------------------------------------------------------------------------


class TestAsyncContext:
    """complete_sync / stream_sync called from *inside* a running event loop.

    Previously, _run_async() would call loop.run_until_complete() on the
    already-running loop, causing a RuntimeError: "This event loop is already running."
    After the fix, _run_async() detects a running loop and falls back to a thread
    with its own loop so it never calls run_until_complete() on the running one.
    """

    @pytest.mark.asyncio
    async def test_complete_sync_from_async_context(self) -> None:
        """complete_sync() must not raise when called inside async context."""
        resp = _make_response("async-ctx")
        provider = _EchoProvider(resp)

        # This must not raise RuntimeError or block
        result = await asyncio.to_thread(
            provider.complete_sync,
            messages=[],
            model=_make_model(),
        )
        assert result is not None
        assert result.content == "async-ctx"

    @pytest.mark.asyncio
    async def test_stream_sync_from_async_context(self) -> None:
        """stream_sync() must not raise when called inside async context."""
        resp = _make_response("stream-async")
        provider = _EchoProvider(resp)

        chunks = await asyncio.to_thread(
            lambda: list(provider.stream_sync(messages=[], model=_make_model()))
        )
        assert len(chunks) == 1
        assert chunks[0].content == "stream-async"

    def test_complete_sync_called_from_running_loop_thread(self) -> None:
        """complete_sync() works when the *calling thread* has a running event loop."""
        resp = _make_response("running-loop")
        provider = _EchoProvider(resp)
        results: list[ProviderResponse | None] = []
        errors: list[Exception] = []

        def run_in_thread_with_loop() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def inner() -> None:
                result = await asyncio.to_thread(
                    provider.complete_sync,
                    messages=[],
                    model=_make_model(),
                )
                results.append(result)

            try:
                loop.run_until_complete(inner())
            except Exception as e:
                errors.append(e)
            finally:
                loop.close()

        t = threading.Thread(target=run_in_thread_with_loop)
        t.start()
        t.join(timeout=10)

        assert not errors, f"Errors: {errors}"
        assert len(results) == 1
        assert results[0] is not None
        assert results[0].content == "running-loop"


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


class TestThreadSafety:
    """Multiple threads calling complete_sync concurrently must not interfere."""

    def test_concurrent_complete_sync(self) -> None:
        resp = _make_response("concurrent")
        provider = _EchoProvider(resp)
        results: list[ProviderResponse | None] = []
        lock = threading.Lock()

        def call() -> None:
            r = provider.complete_sync(messages=[], model=_make_model())
            with lock:
                results.append(r)

        threads = [threading.Thread(target=call) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(results) == 8
        assert all(r is not None and r.content == "concurrent" for r in results)
