"""Stress test fixtures and configuration."""

from __future__ import annotations

import pytest

from syrin import Agent, Model


class _StressAgent(Agent):
    """Minimal agent for stress tests."""

    model = Model.Almock()
    system_prompt = "Stress test agent."


@pytest.fixture
def stress_agent() -> type[Agent]:
    """A minimal stress test agent class."""
    return _StressAgent
