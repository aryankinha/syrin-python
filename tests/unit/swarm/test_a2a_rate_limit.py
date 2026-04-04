"""Tests for A2A rate limiting — P3-T5."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from pydantic import BaseModel

from syrin.enums import Hook
from syrin.events import EventContext, Events
from syrin.swarm._a2a import A2AConfig, A2AMessageTooLarge, A2ARouter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _TestMessage(BaseModel):
    """Simple test message."""

    data: str


def _events_with_capture(captured: list[tuple[Hook, EventContext]]) -> Events:
    """Return an Events instance that records all hooks via on() handlers."""
    events = Events(lambda _h, _c: None)

    for hook in Hook:

        def _make_handler(h: Hook) -> Callable[[EventContext], None]:
            def _handler(ctx: EventContext) -> None:
                captured.append((h, ctx))

            return _handler

        events.on(hook, _make_handler(hook))

    return events


# ---------------------------------------------------------------------------
# P3-T5-1: max_message_size — oversized message raises A2AMessageTooLarge
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a2a_max_message_size_raises_for_large_payload() -> None:
    """A2AConfig(max_message_size=1000) rejects a 1001-byte payload."""
    config = A2AConfig(max_message_size=1000)
    router = A2ARouter(config=config)
    router.register_agent("sender")
    router.register_agent("receiver")

    # Create a message whose serialized size exceeds 1000 bytes
    big_data = "x" * 1001
    msg = _TestMessage(data=big_data)

    with pytest.raises(A2AMessageTooLarge):
        await router.send(from_agent="sender", to_agent="receiver", message=msg)


@pytest.mark.asyncio
async def test_a2a_max_message_size_allows_small_payload() -> None:
    """A2AConfig(max_message_size=1000) allows a small payload through."""
    config = A2AConfig(max_message_size=1000)
    router = A2ARouter(config=config)
    router.register_agent("sender")
    router.register_agent("receiver")

    msg = _TestMessage(data="small")

    await router.send(from_agent="sender", to_agent="receiver", message=msg)
    env = await router.receive(agent_id="receiver", timeout=0.5)
    assert env is not None


# ---------------------------------------------------------------------------
# P3-T5-2: max_queue_depth — 6th message triggers A2A_QUEUE_FULL + dropped
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a2a_max_queue_depth_fires_hook_and_drops() -> None:
    """A2AConfig(max_queue_depth=5) fires A2A_QUEUE_FULL on 6th message and drops it."""
    captured: list[tuple[Hook, EventContext]] = []
    events = _events_with_capture(captured)

    config = A2AConfig(max_queue_depth=5)
    router = A2ARouter(config=config, swarm_events=events)
    router.register_agent("sender")
    router.register_agent("receiver")

    # Send 5 messages (should all succeed)
    for i in range(5):
        await router.send(
            from_agent="sender",
            to_agent="receiver",
            message=_TestMessage(data=f"msg-{i}"),
        )

    # 6th message should trigger A2A_QUEUE_FULL
    await router.send(
        from_agent="sender",
        to_agent="receiver",
        message=_TestMessage(data="overflow"),
    )

    hooks = [h for h, _ in captured]
    assert Hook.A2A_QUEUE_FULL in hooks, "A2A_QUEUE_FULL should fire on 6th message"

    # The queue should only have 5 messages (6th was dropped)
    messages = []
    for _ in range(10):
        env = await router.receive(agent_id="receiver", timeout=0.05)
        if env is None:
            break
        messages.append(env)

    assert len(messages) == 5, f"Queue should only have 5 messages, got {len(messages)}"
    payloads = [m.payload.data for m in messages]  # type: ignore[union-attr]
    assert "overflow" not in payloads, "Overflow message should be dropped"


@pytest.mark.asyncio
async def test_a2a_unlimited_queue_depth_allows_many() -> None:
    """A2AConfig(max_queue_depth=0) (unlimited) allows many messages through."""
    config = A2AConfig(max_queue_depth=0)
    router = A2ARouter(config=config)
    router.register_agent("sender")
    router.register_agent("receiver")

    for i in range(20):
        await router.send(
            from_agent="sender",
            to_agent="receiver",
            message=_TestMessage(data=f"msg-{i}"),
        )

    count = 0
    for _ in range(25):
        env = await router.receive(agent_id="receiver", timeout=0.05)
        if env is None:
            break
        count += 1

    assert count == 20
