"""Swarm test fixtures."""

from __future__ import annotations

import pytest

from syrin import Agent, Budget, Model
from syrin.swarm import Swarm


class _StubAgent(Agent):
    """Minimal stub agent for swarm tests."""

    model = Model.Almock()
    system_prompt = "Stub swarm agent."


@pytest.fixture
def stub_agent() -> type[Agent]:
    """A minimal stub agent class."""
    return _StubAgent


@pytest.fixture
def swarm_budget() -> Budget:
    """$5 shared swarm budget."""
    return Budget(max_cost=5.00)


@pytest.fixture
def minimal_swarm(stub_agent: type[Agent], swarm_budget: Budget) -> Swarm:
    """A minimal swarm with one stub agent."""
    return Swarm(
        goal="Test goal",
        agents=[stub_agent()],
        budget=swarm_budget,
    )
