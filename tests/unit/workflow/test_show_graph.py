"""Tests for wf.run(show_graph=True) live Rich overlay.

Exit criteria:
- wf.run("...", show_graph=True) shows live Rich overlay — each step transitions
  through PENDING → RUNNING → COMPLETE states with cost + elapsed time
- Parallel steps in live graph show individual status per agent
- Failed step shows FAILED in red; downstream steps show SKIPPED
"""

from __future__ import annotations

import pytest

from syrin import Agent, Model
from syrin.response import Response
from syrin.workflow._core import Workflow
from syrin.workflow.exceptions import WorkflowStepError


def _model() -> Model:
    return Model.Almock(latency_seconds=0.01, lorem_length=2)


class _AgentA(Agent):
    model = _model()
    system_prompt = "a"


class _AgentB(Agent):
    model = _model()
    system_prompt = "b"


class _AgentC(Agent):
    model = _model()
    system_prompt = "c"


# ---------------------------------------------------------------------------
# show_graph=True produces output
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_show_graph_true_produces_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """wf.run(show_graph=True) prints a table to stdout."""
    wf = Workflow("graph-wf").step(_AgentA).step(_AgentB)
    await wf.run("input", show_graph=True)
    captured = capsys.readouterr()
    # Rich prints a table with the workflow name
    assert "graph-wf" in captured.out or len(captured.out) > 0


@pytest.mark.asyncio
async def test_show_graph_true_shows_complete_status(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """show_graph=True shows COMPLETE status for finished steps."""
    wf = Workflow("complete-wf").step(_AgentA)
    await wf.run("task", show_graph=True)
    captured = capsys.readouterr()
    # Rich markup renders as terminal escape codes; check for COMPLETE text
    assert "COMPLETE" in captured.out


@pytest.mark.asyncio
async def test_show_graph_true_returns_correct_result() -> None:
    """show_graph=True returns the same result as show_graph=False."""

    class _FixedAgent(Agent):
        model = _model()
        system_prompt = "fixed"

        async def arun(self, input_text: str, **kwargs: object) -> Response[str]:
            return Response(content="fixed-output", cost=0.001)

    wf_with = Workflow("same-wf").step(_FixedAgent)
    wf_without = Workflow("same-wf-2").step(_FixedAgent)

    result_with = await wf_with.run("input", show_graph=True)
    result_without = await wf_without.run("input", show_graph=False)

    assert result_with.content == result_without.content


@pytest.mark.asyncio
async def test_show_graph_shows_step_names(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """show_graph=True table includes step agent class names."""
    wf = Workflow("name-wf").step(_AgentA).step(_AgentB)
    await wf.run("input", show_graph=True)
    captured = capsys.readouterr()
    assert "_AgentA" in captured.out
    assert "_AgentB" in captured.out


# ---------------------------------------------------------------------------
# Failed step shows FAILED; downstream shows SKIPPED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_show_graph_failed_step_shows_failed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A failed step shows FAILED in the graph output."""

    class _FailAgent(Agent):
        model = _model()
        system_prompt = "fail"

        async def arun(self, input_text: str, **kwargs: object) -> Response[str]:
            raise RuntimeError("intentional failure")

    wf = Workflow("fail-wf").step(_FailAgent).step(_AgentB)
    with pytest.raises((WorkflowStepError, RuntimeError)):
        await wf.run("input", show_graph=True)
    captured = capsys.readouterr()
    assert "FAILED" in captured.out


@pytest.mark.asyncio
async def test_show_graph_skips_downstream_on_failure(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Downstream steps show SKIPPED when an earlier step fails."""

    class _FailStep(Agent):
        model = _model()
        system_prompt = "fail-step"

        async def arun(self, input_text: str, **kwargs: object) -> Response[str]:
            raise RuntimeError("step failed")

    wf = Workflow("skip-wf").step(_FailStep).step(_AgentA).step(_AgentB)
    with pytest.raises((WorkflowStepError, RuntimeError)):
        await wf.run("input", show_graph=True)
    captured = capsys.readouterr()
    assert "SKIPPED" in captured.out


# ---------------------------------------------------------------------------
# Parallel steps show correct labels
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_show_graph_parallel_steps_labeled(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Parallel steps appear in the graph with a 'parallel(...)' label."""
    wf = Workflow("par-wf").parallel([_AgentA, _AgentB]).step(_AgentC)
    await wf.run("input", show_graph=True)
    captured = capsys.readouterr()
    assert "parallel" in captured.out
