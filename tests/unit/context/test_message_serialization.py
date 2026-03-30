"""Message serialization delta — repeated messages must not re-allocate new dicts.

Tests that:
- The same Message serializes to an identical dict object on repeated calls
  (proves the per-(role, content) cache is active)
- Different messages serialize to different dicts
"""

from __future__ import annotations

from syrin.agent._context_builder import _serialize_message
from syrin.types import Message, MessageRole


class TestMessageSerializationDelta:
    def test_same_message_returns_identical_object(self) -> None:
        """Serializing the same (role, content) twice returns the same dict object."""
        msg = Message(role=MessageRole.USER, content="Hello, world!")
        r1 = _serialize_message(msg)
        r2 = _serialize_message(msg)
        assert r1 is r2, "_serialize_message should cache and return the same dict object"

    def test_different_content_returns_different_dicts(self) -> None:
        """Different messages produce different dicts."""
        m1 = Message(role=MessageRole.USER, content="Hello")
        m2 = Message(role=MessageRole.USER, content="Goodbye")
        assert _serialize_message(m1) != _serialize_message(m2)

    def test_different_roles_are_distinct(self) -> None:
        """Same content but different roles produce different dicts."""
        m1 = Message(role=MessageRole.USER, content="test")
        m2 = Message(role=MessageRole.ASSISTANT, content="test")
        r1 = _serialize_message(m1)
        r2 = _serialize_message(m2)
        assert r1 is not r2
        assert r1["role"] != r2["role"]

    def test_serialized_dict_has_correct_keys(self) -> None:
        """Serialized dict has 'role' and 'content' keys with correct values."""
        msg = Message(role=MessageRole.ASSISTANT, content="I'm an assistant.")
        result = _serialize_message(msg)
        assert result["role"] == "assistant"
        assert result["content"] == "I'm an assistant."
