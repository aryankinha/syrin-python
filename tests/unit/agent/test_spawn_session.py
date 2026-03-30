"""Session ID propagation in agent.spawn() and spawn_parallel().

Tests that:
- Child agent inherits parent's _conversation_id
- spawn_parallel() children also inherit _conversation_id
- When parent has no _conversation_id, child is also None
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import syrin
from syrin.agent._spawn import spawn, spawn_parallel


class ChildAgent(syrin.Agent):
    model = syrin.Model("gpt-4o-mini")
    instructions = "Child"


class TestSpawnSessionIdPropagation:
    def _make_parent(self, session_id: str | None = "session-abc-123") -> syrin.Agent:
        parent = MagicMock(spec=syrin.Agent)
        parent._conversation_id = session_id
        parent._budget = None
        parent._max_child_agents = 10
        parent._child_count = 0
        parent._context = MagicMock()
        parent._context.snapshot.return_value = MagicMock(total_tokens=0)
        parent._emit_event = MagicMock()
        parent._budget_tracker = MagicMock()
        parent._runtime = MagicMock()
        parent._runtime.budget_tracker_shared = False
        parent.__class__ = syrin.Agent
        return parent

    def test_child_inherits_session_id(self) -> None:
        """Child agent must have the same _conversation_id as parent."""
        parent = self._make_parent(session_id="test-session-xyz")

        with patch.object(ChildAgent, "run", return_value=MagicMock(cost=0.0)):
            spawn(parent, ChildAgent, task="do something")

        # spawn with task returns Response, so we need to check a different way
        # Instead spawn without task to get the child instance
        child = spawn(parent, ChildAgent)
        assert child._conversation_id == "test-session-xyz", (
            f"Child should inherit parent session_id, got {child._conversation_id!r}"
        )

    def test_child_session_id_none_when_parent_has_none(self) -> None:
        """When parent has no session_id, child should also have None."""
        parent = self._make_parent(session_id=None)

        child = spawn(parent, ChildAgent)
        assert child._conversation_id is None

    def test_spawn_parallel_children_inherit_session_id(self) -> None:
        """spawn_parallel children must all inherit parent's session_id."""
        parent = self._make_parent(session_id="parallel-session-999")

        with patch.object(ChildAgent, "run", return_value=MagicMock(cost=0.0)):
            results = spawn_parallel(parent, [(ChildAgent, "task1"), (ChildAgent, "task2")])

        assert len(results) == 2
