"""Swarm integration test fixtures."""

from __future__ import annotations

import pytest

from syrin import Agent, Budget, Model


class _IntegrationAgent(Agent):
    """Minimal agent for swarm integration tests."""

    model = Model.Almock()
    system_prompt = "Integration test swarm agent."


@pytest.fixture
def integration_agent() -> type[Agent]:
    """An integration test agent class."""
    return _IntegrationAgent


@pytest.fixture
def integration_swarm_budget() -> Budget:
    """$10 shared budget for integration tests."""
    return Budget(max_cost=10.00)
