"""Tests for A2A budget enforcement — budget_per_message and max_messages_per_sender."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from syrin.swarm._a2a import A2ABudgetExceededError, A2AConfig, A2ARouter


class SimpleMsg(BaseModel):
    """Simple test message payload."""

    text: str


# ---------------------------------------------------------------------------
# A2AConfig field tests
# ---------------------------------------------------------------------------


def test_a2a_config_budget_defaults() -> None:
    config = A2AConfig()
    assert config.budget_per_message == 0.0
    assert config.max_messages_per_sender == 0


def test_a2a_config_budget_fields() -> None:
    config = A2AConfig(budget_per_message=0.05, max_messages_per_sender=3)
    assert config.budget_per_message == 0.05
    assert config.max_messages_per_sender == 3


# ---------------------------------------------------------------------------
# send() — message count enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_within_limits_succeeds() -> None:
    config = A2AConfig(max_messages_per_sender=2)
    router = A2ARouter(config=config)
    router.register_agent("sender")
    router.register_agent("receiver")

    msg = SimpleMsg(text="hello")
    await router.send(from_agent="sender", to_agent="receiver", message=msg)
    await router.send(from_agent="sender", to_agent="receiver", message=msg)
    # Should not raise


@pytest.mark.asyncio
async def test_send_exceeds_max_messages_raises() -> None:
    config = A2AConfig(max_messages_per_sender=2)
    router = A2ARouter(config=config)
    router.register_agent("sender")
    router.register_agent("receiver")

    msg = SimpleMsg(text="hello")
    await router.send(from_agent="sender", to_agent="receiver", message=msg)
    await router.send(from_agent="sender", to_agent="receiver", message=msg)

    with pytest.raises(A2ABudgetExceededError) as exc_info:
        await router.send(from_agent="sender", to_agent="receiver", message=msg)

    err = exc_info.value
    assert err.sender_id == "sender"
    assert err.limit == 2
    assert err.actual == 3


@pytest.mark.asyncio
async def test_send_zero_max_messages_is_unlimited() -> None:
    config = A2AConfig(max_messages_per_sender=0)  # 0 = unlimited
    router = A2ARouter(config=config)
    router.register_agent("sender")
    router.register_agent("receiver")

    msg = SimpleMsg(text="hello")
    for _ in range(10):
        await router.send(from_agent="sender", to_agent="receiver", message=msg)
    # No exception raised


@pytest.mark.asyncio
async def test_send_different_senders_independent_counts() -> None:
    config = A2AConfig(max_messages_per_sender=1)
    router = A2ARouter(config=config)
    router.register_agent("sender_a")
    router.register_agent("sender_b")
    router.register_agent("receiver")

    msg = SimpleMsg(text="hello")
    await router.send(from_agent="sender_a", to_agent="receiver", message=msg)
    await router.send(from_agent="sender_b", to_agent="receiver", message=msg)
    # Both senders each sent 1 message (limit=1), so no error raised


# ---------------------------------------------------------------------------
# A2ABudgetExceededError fields
# ---------------------------------------------------------------------------


def test_a2a_budget_exceeded_error_fields() -> None:
    err = A2ABudgetExceededError(sender_id="agent_x", limit=5.0, actual=6.0)
    assert err.sender_id == "agent_x"
    assert err.limit == 5.0
    assert err.actual == 6.0
    assert "agent_x" in str(err)
