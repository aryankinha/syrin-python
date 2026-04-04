"""Tests for A2A audit trail — P3-T6."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from syrin.swarm._a2a import A2AConfig, A2ARouter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _SimpleMessage(BaseModel):
    """A simple test message for audit tests."""

    content: str


# ---------------------------------------------------------------------------
# P3-T6-1: audit_all=True — every sent message appears in audit log
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a2a_audit_all_records_sent_messages() -> None:
    """A2AConfig(audit_all=True) records every sent message in audit log."""
    config = A2AConfig(audit_all=True)
    router = A2ARouter(config=config)
    router.register_agent("sender")
    router.register_agent("receiver")

    msg1 = _SimpleMessage(content="first message")
    msg2 = _SimpleMessage(content="second message")

    await router.send(from_agent="sender", to_agent="receiver", message=msg1)
    await router.send(from_agent="sender", to_agent="receiver", message=msg2)

    log = router.audit_log()
    assert len(log) == 2, f"Expected 2 audit entries, got {len(log)}"


# ---------------------------------------------------------------------------
# P3-T6-2: Audit entry includes required fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a2a_audit_entry_fields() -> None:
    """Audit entry includes from_agent, to_agent, message_type, timestamp, size_bytes."""
    config = A2AConfig(audit_all=True)
    router = A2ARouter(config=config)
    router.register_agent("alpha")
    router.register_agent("beta")

    msg = _SimpleMessage(content="audited message")
    await router.send(from_agent="alpha", to_agent="beta", message=msg)

    log = router.audit_log()
    assert len(log) == 1

    entry = log[0]
    assert entry.from_agent == "alpha"
    assert entry.to_agent == "beta"
    assert entry.message_type == "_SimpleMessage"
    assert entry.timestamp is not None
    assert entry.size_bytes > 0


# ---------------------------------------------------------------------------
# P3-T6-3: audit_all=False — messages not recorded
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a2a_no_audit_when_disabled() -> None:
    """audit_all=False (default) means messages do NOT appear in audit log."""
    config = A2AConfig(audit_all=False)
    router = A2ARouter(config=config)
    router.register_agent("sender")
    router.register_agent("receiver")

    msg = _SimpleMessage(content="silent message")
    await router.send(from_agent="sender", to_agent="receiver", message=msg)

    log = router.audit_log()
    assert log == [], "Audit log should be empty when audit_all=False"


@pytest.mark.asyncio
async def test_a2a_default_config_no_audit() -> None:
    """Default A2AConfig does not enable auditing."""
    router = A2ARouter()  # no config = defaults
    router.register_agent("x")
    router.register_agent("y")

    await router.send(from_agent="x", to_agent="y", message=_SimpleMessage(content="test"))

    assert router.audit_log() == []


# ---------------------------------------------------------------------------
# P3-T6-4: Audit records multiple messages in order
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a2a_audit_multiple_messages_in_order() -> None:
    """Audit log preserves insertion order for multiple messages."""
    config = A2AConfig(audit_all=True)
    router = A2ARouter(config=config)
    router.register_agent("s")
    router.register_agent("r")

    for i in range(5):
        await router.send(
            from_agent="s",
            to_agent="r",
            message=_SimpleMessage(content=f"msg-{i}"),
        )

    log = router.audit_log()
    assert len(log) == 5
    # All entries should be from "s" to "r"
    for entry in log:
        assert entry.from_agent == "s"
        assert entry.to_agent == "r"
