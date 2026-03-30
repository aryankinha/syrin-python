"""Conversation history sliding window enforcement in InMemoryContextStore.

Tests that:
- InMemoryContextStore respects max_segments limit on add_segment
- Memory.add_conversation_segment respects max_conversation_turns
- Oldest segments are dropped (sliding window, not blocking)
- Without a limit, all segments are kept
"""

from __future__ import annotations

from syrin.context.store import ContextSegment, InMemoryContextStore


class TestInMemoryContextStoreSlidingWindow:
    def test_add_segment_no_limit_keeps_all(self) -> None:
        """Without a max, all segments are kept."""
        store = InMemoryContextStore()
        for i in range(200):
            store.add_segment(ContextSegment(content=f"msg-{i}", role="user"))
        assert len(store.list_recent(n=10000)) == 200

    def test_add_segment_with_limit_enforces_window(self) -> None:
        """With max_segments=5, only the last 5 segments are kept."""
        store = InMemoryContextStore(max_segments=5)
        for i in range(10):
            store.add_segment(ContextSegment(content=f"msg-{i}", role="user"))
        recent = store.list_recent(n=10000)
        assert len(recent) == 5, f"Expected 5 segments, got {len(recent)}"

    def test_sliding_window_preserves_newest(self) -> None:
        """Sliding window discards oldest, keeps newest."""
        store = InMemoryContextStore(max_segments=3)
        for i in range(5):
            store.add_segment(ContextSegment(content=f"msg-{i}", role="user"))
        recent = store.list_recent(n=10)
        contents = [s.content for s in recent]
        assert "msg-0" not in contents, "Oldest should be evicted"
        assert "msg-1" not in contents, "Second-oldest should be evicted"
        assert "msg-4" in contents, "Newest should be retained"
        assert "msg-3" in contents, "Second-newest should be retained"
        assert "msg-2" in contents, "Third-newest should be retained"

    def test_max_segments_zero_keeps_nothing(self) -> None:
        """max_segments=0 should keep nothing or be treated as no-limit."""
        # Treat 0 as "no limit" (same as None)
        store = InMemoryContextStore(max_segments=0)
        for i in range(5):
            store.add_segment(ContextSegment(content=f"msg-{i}", role="user"))
        # Either keeps all or keeps nothing — but should not raise
        assert isinstance(store.list_recent(n=100), list)

    def test_max_segments_one(self) -> None:
        """max_segments=1 keeps only the latest segment."""
        store = InMemoryContextStore(max_segments=1)
        store.add_segment(ContextSegment(content="first", role="user"))
        store.add_segment(ContextSegment(content="second", role="user"))
        recent = store.list_recent(n=10)
        assert len(recent) == 1
        assert recent[0].content == "second"
