"""
E2E smoke test: full agent flow without mocks inside the library.

Runs a complete path: Agent → provider (Almock) → response. No patching of
syrin internals; exercises the real call stack. Use this as a template for
e2e tests that hit real APIs (with skip when keys are missing).
"""

from __future__ import annotations

from syrin import Agent, Model


def test_e2e_agent_response_full_stack() -> None:
    """Full stack: Agent creation → response() → valid Response (no internal mocks)."""
    model = Model.Almock(latency_seconds=0.01, lorem_length=20)
    agent = Agent(model=model, system_prompt="You are a test assistant.")

    response = agent.run("Say hello in one sentence.")

    assert response is not None
    assert isinstance(response.content, str)
    assert len(response.content) > 0
    assert response.cost >= 0
    assert response.tokens is not None
    assert response.tokens.total_tokens >= 0
