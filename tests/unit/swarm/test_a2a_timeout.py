"""Tests for A2A require_ack timeout firing Hook.A2A_MESSAGE_TIMEOUT (Feature 5)."""

from __future__ import annotations

import asyncio

import pytest
from pydantic import BaseModel

from syrin.enums import Hook
from syrin.events import EventContext, Events
from syrin.swarm._a2a import A2AConfig, A2ARouter, A2ATimeoutError

# ---------------------------------------------------------------------------
# Test message type
# ---------------------------------------------------------------------------


class _PingMessage(BaseModel):
    text: str


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.phase_5
class TestA2ATimeoutHook:
    """A2A send_with_ack timeout fires A2A_MESSAGE_TIMEOUT and raises A2ATimeoutError."""

    async def test_timeout_fires_a2a_message_timeout_hook(self) -> None:
        """send_with_ack with no ack within timeout fires Hook.A2A_MESSAGE_TIMEOUT."""
        timeout_events: list[EventContext] = []

        def _noop_emit(hook: Hook, ctx: EventContext) -> None:
            pass

        events = Events(_noop_emit)
        events.on(Hook.A2A_MESSAGE_TIMEOUT, timeout_events.append)

        router = A2ARouter(config=A2AConfig(), swarm_events=events)
        router.register_agent("sender")
        router.register_agent("receiver")

        with pytest.raises(A2ATimeoutError):
            await router.send_with_ack(
                from_agent="sender",
                to_agent="receiver",
                message=_PingMessage(text="hello"),
                timeout=0.05,  # Very short timeout — no ack will arrive
            )

        assert len(timeout_events) == 1

    async def test_timeout_context_has_correct_fields(self) -> None:
        """A2A_MESSAGE_TIMEOUT event context contains message_id, sender/recipient, timeout."""
        timeout_contexts: list[EventContext] = []

        def _noop_emit(hook: Hook, ctx: EventContext) -> None:
            pass

        events = Events(_noop_emit)
        events.on(Hook.A2A_MESSAGE_TIMEOUT, timeout_contexts.append)

        router = A2ARouter(config=A2AConfig(), swarm_events=events)
        router.register_agent("alice")
        router.register_agent("bob")

        with pytest.raises(A2ATimeoutError):
            await router.send_with_ack(
                from_agent="alice",
                to_agent="bob",
                message=_PingMessage(text="ping"),
                timeout=0.05,
            )

        assert len(timeout_contexts) == 1
        ctx = timeout_contexts[0]
        assert ctx["from_agent"] == "alice"
        assert ctx["to_agent"] == "bob"
        assert ctx["timeout"] == pytest.approx(0.05)
        assert "message_id" in ctx

    async def test_ack_received_in_time_no_error_no_timeout_hook(self) -> None:
        """send_with_ack with timely ack does not raise and does not fire timeout hook."""
        timeout_events: list[EventContext] = []

        def _noop_emit(hook: Hook, ctx: EventContext) -> None:
            pass

        events = Events(_noop_emit)
        events.on(Hook.A2A_MESSAGE_TIMEOUT, timeout_events.append)

        router = A2ARouter(config=A2AConfig(), swarm_events=events)
        router.register_agent("sender")
        router.register_agent("receiver")

        # Coroutine that reads and acks immediately
        async def _auto_ack() -> None:
            envelope = await router.receive(agent_id="receiver", timeout=5.0)
            assert envelope is not None
            await router.ack("receiver", envelope.message_id)

        ack_task = asyncio.create_task(_auto_ack())
        await router.send_with_ack(
            from_agent="sender",
            to_agent="receiver",
            message=_PingMessage(text="ping"),
            timeout=2.0,
        )
        await ack_task

        assert timeout_events == []

    async def test_send_without_require_ack_no_ack_waiting(self) -> None:
        """send() without require_ack completes immediately, no ack machinery."""
        timeout_events: list[EventContext] = []

        def _noop_emit(hook: Hook, ctx: EventContext) -> None:
            pass

        events = Events(_noop_emit)
        events.on(Hook.A2A_MESSAGE_TIMEOUT, timeout_events.append)

        router = A2ARouter(config=A2AConfig(), swarm_events=events)
        router.register_agent("s1")
        router.register_agent("s2")

        # Should complete with no waiting and no error
        await router.send(
            from_agent="s1",
            to_agent="s2",
            message=_PingMessage(text="no-ack message"),
        )

        assert timeout_events == []

    async def test_a2a_timeout_error_has_message_id_and_timeout(self) -> None:
        """A2ATimeoutError carries message_id and timeout attributes."""
        router = A2ARouter()
        router.register_agent("a")
        router.register_agent("b")

        exc: A2ATimeoutError | None = None
        try:
            await router.send_with_ack(
                from_agent="a",
                to_agent="b",
                message=_PingMessage(text="t"),
                timeout=0.05,
            )
        except A2ATimeoutError as e:
            exc = e

        assert exc is not None
        assert exc.timeout == pytest.approx(0.05)
        assert isinstance(exc.message_id, str)
        assert len(exc.message_id) > 0
