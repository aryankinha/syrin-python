"""Tests for A2A messaging core — P3-T4."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

import pytest
from pydantic import BaseModel

from syrin.enums import A2AChannel, Hook
from syrin.events import EventContext, Events
from syrin.swarm._a2a import A2ARouter, A2ATimeoutError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _PingMessage(BaseModel):
    """A simple test message."""

    text: str
    value: int = 0


class _DataMessage(BaseModel):
    """A message with typed fields."""

    name: str
    score: float
    tags: list[str] = []


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
# P3-T4-1: Router manages per-agent inboxes
# ---------------------------------------------------------------------------


def test_a2a_router_register_agent() -> None:
    """A2ARouter creates a per-agent inbox when register_agent is called."""
    router = A2ARouter()
    router.register_agent("writer")
    router.register_agent("reader")

    assert router.has_inbox("writer")
    assert router.has_inbox("reader")


# ---------------------------------------------------------------------------
# P3-T4-2: send delivers message to recipient's queue
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a2a_router_send_delivers_to_inbox() -> None:
    """router.send() places the message envelope in the recipient's inbox."""
    router = A2ARouter()
    router.register_agent("reader")
    router.register_agent("writer")

    msg = _PingMessage(text="hello", value=42)
    await router.send(from_agent="reader", to_agent="writer", message=msg)

    envelope = await router.receive(agent_id="writer", timeout=1.0)
    assert envelope is not None
    assert isinstance(envelope.payload, _PingMessage)
    assert envelope.payload.text == "hello"
    assert envelope.payload.value == 42


# ---------------------------------------------------------------------------
# P3-T4-3: receive returns next message from inbox
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a2a_router_receive_returns_message() -> None:
    """router.receive() returns the next message from the agent's inbox."""
    router = A2ARouter()
    router.register_agent("agent-b")
    router.register_agent("agent-a")

    msg = _PingMessage(text="ping")
    await router.send(from_agent="agent-a", to_agent="agent-b", message=msg)

    envelope = await router.receive(agent_id="agent-b", timeout=1.0)
    assert envelope is not None
    assert envelope.from_agent == "agent-a"
    assert envelope.to_agent == "agent-b"


@pytest.mark.asyncio
async def test_a2a_router_receive_timeout_returns_none() -> None:
    """router.receive() returns None when inbox is empty and timeout expires."""
    router = A2ARouter()
    router.register_agent("lonely-agent")

    result = await router.receive(agent_id="lonely-agent", timeout=0.05)
    assert result is None


# ---------------------------------------------------------------------------
# P3-T4-4: send_with_ack waits for acknowledgement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a2a_router_send_with_ack_success() -> None:
    """send_with_ack() succeeds when recipient acks within timeout."""
    router = A2ARouter()
    router.register_agent("sender")
    router.register_agent("receiver")

    msg = _PingMessage(text="need ack")

    async def _ack_receiver() -> None:
        envelope = await router.receive(agent_id="receiver", timeout=2.0)
        assert envelope is not None
        await router.ack(agent_id="receiver", message_id=envelope.message_id)

    ack_task = asyncio.create_task(_ack_receiver())
    await router.send_with_ack(from_agent="sender", to_agent="receiver", message=msg, timeout=5.0)
    await ack_task


# ---------------------------------------------------------------------------
# P3-T4-5: send_with_ack timeout raises A2ATimeoutError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a2a_router_send_with_ack_timeout_raises() -> None:
    """send_with_ack raises A2ATimeoutError when ack doesn't arrive in time."""
    router = A2ARouter()
    router.register_agent("sender")
    router.register_agent("slow-receiver")

    msg = _PingMessage(text="ack me please")

    with pytest.raises(A2ATimeoutError):
        await router.send_with_ack(
            from_agent="sender",
            to_agent="slow-receiver",
            message=msg,
            timeout=0.05,
        )


# ---------------------------------------------------------------------------
# P3-T4-6: A2AChannel.BROADCAST delivers to all agents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a2a_router_broadcast_delivers_to_all() -> None:
    """BROADCAST channel delivers message to all registered agents."""
    router = A2ARouter()
    router.register_agent("broadcaster")
    router.register_agent("agent-1")
    router.register_agent("agent-2")
    router.register_agent("agent-3")

    msg = _PingMessage(text="broadcast message")
    await router.send(
        from_agent="broadcaster",
        to_agent="broadcast",
        message=msg,
        channel=A2AChannel.BROADCAST,
    )

    for agent_id in ("agent-1", "agent-2", "agent-3"):
        envelope = await router.receive(agent_id=agent_id, timeout=0.5)
        assert envelope is not None, f"{agent_id} did not receive broadcast"
        assert envelope.payload.text == "broadcast message"  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# P3-T4-7: A2AChannel.TOPIC delivers only to subscribers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a2a_router_topic_delivers_to_subscribers() -> None:
    """TOPIC channel delivers only to agents subscribed to that topic."""
    router = A2ARouter()
    router.register_agent("publisher")
    router.register_agent("subscriber-a")
    router.register_agent("subscriber-b")
    router.register_agent("non-subscriber")

    router.subscribe("subscriber-a", topic="news")
    router.subscribe("subscriber-b", topic="news")

    msg = _PingMessage(text="breaking news")
    await router.send(
        from_agent="publisher",
        to_agent="news",
        message=msg,
        channel=A2AChannel.TOPIC,
    )

    env_a = await router.receive(agent_id="subscriber-a", timeout=0.5)
    env_b = await router.receive(agent_id="subscriber-b", timeout=0.5)
    env_non = await router.receive(agent_id="non-subscriber", timeout=0.05)

    assert env_a is not None, "subscriber-a should receive topic message"
    assert env_b is not None, "subscriber-b should receive topic message"
    assert env_non is None, "non-subscriber should not receive topic message"


# ---------------------------------------------------------------------------
# P3-T4-8: Message payload preserves typed Pydantic fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a2a_message_preserves_typed_payload() -> None:
    """Message payload preserves all typed Pydantic model fields."""
    router = A2ARouter()
    router.register_agent("sender")
    router.register_agent("receiver")

    msg = _DataMessage(name="Alice", score=9.5, tags=["ml", "nlp"])
    await router.send(from_agent="sender", to_agent="receiver", message=msg)

    envelope = await router.receive(agent_id="receiver", timeout=1.0)
    assert envelope is not None
    payload = envelope.payload
    assert isinstance(payload, _DataMessage)
    assert payload.name == "Alice"
    assert payload.score == 9.5
    assert payload.tags == ["ml", "nlp"]


# ---------------------------------------------------------------------------
# P3-T4-9: Hook.A2A_MESSAGE_SENT fires on send
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a2a_message_sent_hook_fires() -> None:
    """Hook.A2A_MESSAGE_SENT fires with from_agent, to_agent, message_type, size_bytes."""
    captured: list[tuple[Hook, EventContext]] = []
    events = _events_with_capture(captured)

    router = A2ARouter(swarm_events=events)
    router.register_agent("sender")
    router.register_agent("receiver")

    msg = _PingMessage(text="hello hook")
    await router.send(from_agent="sender", to_agent="receiver", message=msg)

    hooks = [h for h, _ in captured]
    assert Hook.A2A_MESSAGE_SENT in hooks

    sent_ctx = next(ctx for h, ctx in captured if h == Hook.A2A_MESSAGE_SENT)
    assert sent_ctx["from_agent"] == "sender"
    assert sent_ctx["to_agent"] == "receiver"
    assert "message_type" in sent_ctx
    assert "size_bytes" in sent_ctx


# ---------------------------------------------------------------------------
# P3-T4-10: Hook.A2A_MESSAGE_RECEIVED fires when message consumed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a2a_message_received_hook_fires() -> None:
    """Hook.A2A_MESSAGE_RECEIVED fires when a message is consumed via receive()."""
    captured: list[tuple[Hook, EventContext]] = []
    events = _events_with_capture(captured)

    router = A2ARouter(swarm_events=events)
    router.register_agent("sender")
    router.register_agent("receiver")

    msg = _PingMessage(text="consume me")
    await router.send(from_agent="sender", to_agent="receiver", message=msg)
    await router.receive(agent_id="receiver", timeout=1.0)

    hooks = [h for h, _ in captured]
    assert Hook.A2A_MESSAGE_RECEIVED in hooks


# ---------------------------------------------------------------------------
# P3-T4-11: Hook.A2A_MESSAGE_ACKED fires when ack received
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a2a_message_acked_hook_fires() -> None:
    """Hook.A2A_MESSAGE_ACKED fires when ack() is called."""
    captured: list[tuple[Hook, EventContext]] = []
    events = _events_with_capture(captured)

    router = A2ARouter(swarm_events=events)
    router.register_agent("sender")
    router.register_agent("receiver")

    msg = _PingMessage(text="ack this")

    async def _ack_task() -> None:
        env = await router.receive(agent_id="receiver", timeout=2.0)
        assert env is not None
        await router.ack(agent_id="receiver", message_id=env.message_id)

    t = asyncio.create_task(_ack_task())
    await router.send_with_ack(from_agent="sender", to_agent="receiver", message=msg, timeout=5.0)
    await t

    hooks = [h for h, _ in captured]
    assert Hook.A2A_MESSAGE_ACKED in hooks


# ---------------------------------------------------------------------------
# P3-T4-12: FIFO ordering in inbox
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a2a_inbox_fifo_ordering() -> None:
    """Agent inbox maintains FIFO ordering for received messages."""
    router = A2ARouter()
    router.register_agent("sender")
    router.register_agent("receiver")

    for i in range(5):
        await router.send(
            from_agent="sender",
            to_agent="receiver",
            message=_PingMessage(text=f"msg-{i}"),
        )

    received_texts = []
    for _ in range(5):
        env = await router.receive(agent_id="receiver", timeout=0.5)
        assert env is not None
        assert isinstance(env.payload, _PingMessage)
        received_texts.append(env.payload.text)

    assert received_texts == [f"msg-{i}" for i in range(5)]
