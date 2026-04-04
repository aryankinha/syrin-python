"""Workflow test fixtures.

Shared fixtures for all workflow unit tests.  Agents here are minimal stubs
backed by :class:`syrin.model.Model.Almock` so no real LLM calls are made.
"""

from __future__ import annotations

import pytest

from syrin import Agent, Budget, Model
from syrin.response import Response
from syrin.types import TokenUsage
from syrin.workflow import Workflow

# ──────────────────────────────────────────────────────────────────────────────
# Minimal agent stubs
# ──────────────────────────────────────────────────────────────────────────────


def make_mock_agent(content: str = "mock response", cost: float = 0.01) -> type[Agent]:
    """Create a minimal Agent subclass that returns a fixed response.

    Args:
        content: Response content the mock agent should return.
        cost: Response cost in USD.

    Returns:
        A new Agent subclass that immediately returns *content*.
    """

    class _MockAgent(Agent):
        model = Model.Almock()
        system_prompt = f"Mock agent returning: {content!r}"

    # Patch arun to return the fixed response without LLM calls
    fixed_response = Response(
        content=content,
        raw=content,
        cost=cost,
        tokens=TokenUsage(input_tokens=5, output_tokens=10, total_tokens=15),
        model="almock/almock",
        trace=[],
    )

    original_init = _MockAgent.__init__

    def patched_init(self, **kwargs: object) -> None:
        original_init(self, **kwargs)

    _MockAgent.__init__ = patched_init  # type: ignore[method-assign]

    async def _arun(self: Agent, input_text: str) -> Response[str]:
        return fixed_response

    def _run(self: Agent, input_text: str) -> Response[str]:
        return fixed_response

    _MockAgent.arun = _arun  # type: ignore[method-assign]
    _MockAgent.run = _run  # type: ignore[method-assign]
    _MockAgent.__name__ = f"MockAgent_{content[:10].replace(' ', '_')}"

    return _MockAgent


@pytest.fixture
def agent_alpha() -> type[Agent]:
    """Agent that returns 'alpha output'."""
    return make_mock_agent("alpha output", cost=0.01)


@pytest.fixture
def agent_beta() -> type[Agent]:
    """Agent that returns 'beta output'."""
    return make_mock_agent("beta output", cost=0.02)


@pytest.fixture
def agent_gamma() -> type[Agent]:
    """Agent that returns 'gamma output'."""
    return make_mock_agent("gamma output", cost=0.03)


@pytest.fixture
def agent_fast() -> type[Agent]:
    """Fast agent that returns 'fast result'."""
    return make_mock_agent("fast result", cost=0.005)


@pytest.fixture
def agent_thorough() -> type[Agent]:
    """Thorough agent that returns 'thorough result'."""
    return make_mock_agent("thorough result", cost=0.05)


@pytest.fixture
def simple_budget() -> Budget:
    """A simple $10 workflow budget."""
    return Budget(max_cost=10.00)


@pytest.fixture
def tight_budget() -> Budget:
    """A tight $0.10 workflow budget."""
    return Budget(max_cost=0.10)


@pytest.fixture
def simple_workflow(agent_alpha: type[Agent]) -> Workflow:
    """A single-step workflow with one mock agent."""
    return Workflow("test-workflow").step(agent_alpha)


@pytest.fixture
def two_step_workflow(agent_alpha: type[Agent], agent_beta: type[Agent]) -> Workflow:
    """A two-step sequential workflow."""
    return Workflow("two-step").step(agent_alpha).step(agent_beta)
