"""Tests for spawning a Workflow instance from an Agent.

Exit criteria:
- Workflow spawned from agent: await self.spawn(my_workflow, task="...", budget=2.00) works correctly
"""

from __future__ import annotations

import asyncio

import pytest

from syrin import Agent, Model
from syrin.workflow._core import Workflow


def _model() -> Model:
    return Model.Almock(latency_seconds=0.01, lorem_length=3)


class _StubAgent(Agent):
    model = _model()
    system_prompt = "stub"


class _WorkflowStep(Agent):
    model = _model()
    system_prompt = "step"


# ---------------------------------------------------------------------------
# Basic workflow spawn
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_spawn_workflow_returns_spawn_result() -> None:
    """await agent.spawn(workflow, task='...', budget=2.00) returns SpawnResult."""
    from syrin.swarm._spawn import SpawnResult

    wf = Workflow("spawned-wf").step(_WorkflowStep, "do task")

    class _ParentAgent(Agent):
        model = _model()
        system_prompt = "parent"

        async def arun(self, prompt: str, **kwargs: object) -> object:
            result = await self.spawn(wf, task=prompt, budget=2.00)
            assert isinstance(result, SpawnResult)
            return result

    parent = _ParentAgent()
    result = await parent.arun("hello")
    assert result is not None


@pytest.mark.asyncio
async def test_spawn_workflow_content_is_string() -> None:
    """SpawnResult.content from workflow spawn is a non-empty string."""
    from syrin.swarm._spawn import SpawnResult

    wf = Workflow("content-wf").step(_WorkflowStep, "answer")

    class _ParentB(Agent):
        model = _model()
        system_prompt = "parent-b"

        async def arun(self, prompt: str, **kwargs: object) -> object:
            return await self.spawn(wf, task=prompt, budget=1.00)

    parent = _ParentB()
    result = await parent.arun("task")
    assert isinstance(result, SpawnResult)
    assert isinstance(result.content, str)
    assert len(result.content) > 0


@pytest.mark.asyncio
async def test_spawn_workflow_cost_is_float() -> None:
    """SpawnResult.cost from workflow spawn is a non-negative float."""
    from syrin.swarm._spawn import SpawnResult

    wf = Workflow("cost-wf").step(_WorkflowStep, "compute")

    class _ParentC(Agent):
        model = _model()
        system_prompt = "parent-c"

        async def arun(self, prompt: str, **kwargs: object) -> object:
            return await self.spawn(wf, task=prompt, budget=1.00)

    parent = _ParentC()
    result = await parent.arun("test")
    assert isinstance(result, SpawnResult)
    assert result.cost >= 0.0


@pytest.mark.asyncio
async def test_spawn_workflow_multi_step() -> None:
    """Spawning a multi-step workflow runs all steps and returns final output."""

    class _StepX(Agent):
        model = _model()
        system_prompt = "x"

    class _StepY(Agent):
        model = _model()
        system_prompt = "y"

    wf = Workflow("multi-wf").step(_StepX).step(_StepY)

    class _ParentD(Agent):
        model = _model()
        system_prompt = "parent-d"

        async def arun(self, prompt: str, **kwargs: object) -> object:
            return await self.spawn(wf, task=prompt, budget=3.00)

    parent = _ParentD()
    from syrin.swarm._spawn import SpawnResult

    result = await parent.arun("research this")
    assert isinstance(result, SpawnResult)
    assert len(result.content) > 0


# ---------------------------------------------------------------------------
# Without budget=float: workflow instance is returned or run
# ---------------------------------------------------------------------------


def test_spawn_workflow_instance_detects_correctly() -> None:
    """Agent.spawn() detects a Workflow instance (not a class) correctly."""
    wf = Workflow("detect-wf").step(_WorkflowStep)

    class _DetectAgent(Agent):
        model = _model()
        system_prompt = "detect"

    agent = _DetectAgent()
    # With budget=float, returns a coroutine (SpawnResult)
    coro = agent.spawn(wf, task="test", budget=1.00)
    # It should be a coroutine, not a plain Response
    assert asyncio.iscoroutine(coro)
    # Clean up
    coro.close()
