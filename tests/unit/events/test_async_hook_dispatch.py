"""Async hook dispatch — async handlers must not be silently dropped.

Tests that:
- Sync handlers still work as before
- Async handlers registered via on() are invoked (not silently dropped)
- Async handlers registered via before() / after() are invoked
- Works when there is a running event loop (asyncio.create_task)
- Graceful fallback when no running loop
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from syrin.events import EventContext, Events


def _make_events() -> Events:
    emit = MagicMock()
    return Events(emit_fn=emit)


def _make_hook():
    from syrin.enums import Hook

    return Hook.AGENT_RUN_START


class TestSyncHandlersStillWork:
    def test_sync_on_handler_called(self) -> None:
        events = _make_events()
        hook = _make_hook()
        called: list[int] = []
        events.on(hook, lambda _: called.append(1))
        ctx = EventContext()
        events._trigger(hook, ctx)
        assert called == [1]

    def test_sync_before_handler_called(self) -> None:
        events = _make_events()
        hook = _make_hook()
        called: list[int] = []
        events.before(hook, lambda _: called.append(2))
        ctx = EventContext()
        events._trigger_before(hook, ctx)
        assert called == [2]

    def test_sync_after_handler_called(self) -> None:
        events = _make_events()
        hook = _make_hook()
        called: list[int] = []
        events.after(hook, lambda _: called.append(3))
        ctx = EventContext()
        events._trigger_after(hook, ctx)
        assert called == [3]


class TestAsyncHandlersInvokedOnLoop:
    @pytest.mark.asyncio
    async def test_async_on_handler_invoked(self) -> None:
        """Async handler registered with on() is awaited/scheduled."""
        events = _make_events()
        hook = _make_hook()
        called: list[int] = []

        async def async_handler(ctx: EventContext) -> None:
            called.append(1)

        events.on(hook, async_handler)  # type: ignore[arg-type]
        ctx = EventContext()
        events._trigger(hook, ctx)
        # Give the event loop a chance to run scheduled tasks
        await asyncio.sleep(0)
        assert called == [1], "Async on() handler was not invoked"

    @pytest.mark.asyncio
    async def test_async_before_handler_invoked(self) -> None:
        """Async handler registered with before() is scheduled."""
        events = _make_events()
        hook = _make_hook()
        called: list[int] = []

        async def async_handler(ctx: EventContext) -> None:
            called.append(2)

        events.before(hook, async_handler)  # type: ignore[arg-type]
        ctx = EventContext()
        events._trigger_before(hook, ctx)
        await asyncio.sleep(0)
        assert called == [2], "Async before() handler was not invoked"

    @pytest.mark.asyncio
    async def test_async_after_handler_invoked(self) -> None:
        """Async handler registered with after() is scheduled."""
        events = _make_events()
        hook = _make_hook()
        called: list[int] = []

        async def async_handler(ctx: EventContext) -> None:
            called.append(3)

        events.after(hook, async_handler)  # type: ignore[arg-type]
        ctx = EventContext()
        events._trigger_after(hook, ctx)
        await asyncio.sleep(0)
        assert called == [3], "Async after() handler was not invoked"

    @pytest.mark.asyncio
    async def test_mixed_sync_async_handlers_both_called(self) -> None:
        """Both sync and async handlers for the same hook are called."""
        events = _make_events()
        hook = _make_hook()
        called: list[str] = []

        def sync_handler(ctx: EventContext) -> None:
            called.append("sync")

        async def async_handler(ctx: EventContext) -> None:
            called.append("async")

        events.on(hook, sync_handler)
        events.on(hook, async_handler)  # type: ignore[arg-type]
        ctx = EventContext()
        events._trigger(hook, ctx)
        await asyncio.sleep(0)
        assert "sync" in called
        assert "async" in called


class TestAsyncHandlerNoRunningLoop:
    def test_async_handler_no_loop_does_not_raise(self) -> None:
        """When no event loop is running, async handler must not raise — fire-and-forget."""
        events = _make_events()
        hook = _make_hook()

        async def async_handler(ctx: EventContext) -> None:
            pass  # Would be silently dropped pre-fix

        events.on(hook, async_handler)  # type: ignore[arg-type]
        ctx = EventContext()
        # This must not raise RuntimeError or leave unraisable exceptions
        events._trigger(hook, ctx)
