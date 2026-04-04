"""Tests for Agent lifecycle — agent_id, goal tracking, and context quality."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from syrin.agent._core import Agent, ContextQuality
from syrin.enums import Hook
from syrin.model import Model

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent(**kwargs: object) -> Agent:
    """Create a minimal Agent instance for testing."""
    model = MagicMock(spec=Model)
    model.context_window = 128000
    return Agent(model=model, **kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# P9-T2: agent_id
# ---------------------------------------------------------------------------


def test_agent_has_agent_id() -> None:
    """Every Agent instance should have an agent_id string attribute."""
    agent = _make_agent()
    assert hasattr(agent, "agent_id")
    assert isinstance(agent.agent_id, str)
    assert len(agent.agent_id) > 0


def test_agent_id_unique_per_instance() -> None:
    """Each Agent instance should have a unique agent_id."""
    a1 = _make_agent()
    a2 = _make_agent()
    assert a1.agent_id != a2.agent_id


# ---------------------------------------------------------------------------
# P9-T2: goal property
# ---------------------------------------------------------------------------


def test_goal_property_initial_none() -> None:
    """Agent.goal should be None before set_goal is called."""
    agent = _make_agent()
    assert agent.goal is None


def test_set_goal_stores_goal() -> None:
    """set_goal() should update the goal property."""
    agent = _make_agent()
    agent.set_goal("Research quantum computing trends")
    assert agent.goal == "Research quantum computing trends"


def test_set_goal_fires_hook() -> None:
    """set_goal() should fire Hook.GOAL_UPDATED with agent_id and goal."""
    fired: list[tuple[object, object]] = []
    agent = _make_agent()
    agent.events.on(Hook.GOAL_UPDATED, lambda ctx: fired.append(("on", ctx)))
    agent.set_goal("My new goal")
    assert len(fired) == 1
    _, ctx = fired[0]
    assert ctx["agent_id"] == agent.agent_id  # type: ignore[index]
    assert ctx["goal"] == "My new goal"  # type: ignore[index]


def test_update_goal_overwrites() -> None:
    """update_goal() should overwrite any previously set goal."""
    agent = _make_agent()
    agent.set_goal("First goal")
    agent.update_goal("Second goal")
    assert agent.goal == "Second goal"


# ---------------------------------------------------------------------------
# P9-T3: ContextQuality
# ---------------------------------------------------------------------------


def test_context_quality_initial_state() -> None:
    """context_quality property should return a ContextQuality dataclass."""
    agent = _make_agent()
    cq = agent.context_quality
    assert isinstance(cq, ContextQuality)
    assert cq.fill_ratio == 0.0
    assert cq.tokens_used == 0
    assert cq.truncated is False
    assert cq.max_tokens > 0


def test_context_quality_fill_ratio() -> None:
    """fill_ratio in ContextQuality should be between 0 and 1."""
    agent = _make_agent()
    cq = agent.context_quality
    assert 0.0 <= cq.fill_ratio <= 1.0


def test_notify_truncation_fires_hook() -> None:
    """_notify_truncation() should fire Hook.MEMORY_TRUNCATED with correct payload."""
    fired: list[object] = []
    agent = _make_agent()
    agent.events.on(Hook.MEMORY_TRUNCATED, lambda ctx: fired.append(ctx))
    agent._notify_truncation(tokens_used=5000, max_tokens=10000)
    assert len(fired) == 1
    ctx = fired[0]
    assert ctx["agent_id"] == agent.agent_id  # type: ignore[index]
    assert ctx["tokens_used"] == 5000  # type: ignore[index]
    assert ctx["max_tokens"] == 10000  # type: ignore[index]
    assert ctx["fill_ratio"] == pytest.approx(0.5)  # type: ignore[index]
