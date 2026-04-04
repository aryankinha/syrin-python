"""Tests for WORKFLOW topology in Swarm (Feature 3)."""

from __future__ import annotations

import pytest

from syrin import Agent, Model
from syrin.enums import SwarmTopology
from syrin.response import Response
from syrin.swarm import Swarm, SwarmConfig
from syrin.workflow import Workflow

# ---------------------------------------------------------------------------
# Stub agents
# ---------------------------------------------------------------------------


class _StepAgent(Agent):
    model = Model.Almock()
    system_prompt = "step agent"

    async def arun(self, input_text: str) -> Response[str]:
        return Response(content=f"processed: {input_text}", cost=0.01)


class _PlaceholderAgent(Agent):
    """Placeholder agent required by Swarm (agents= cannot be empty)."""

    model = Model.Almock()
    system_prompt = "placeholder"

    async def arun(self, input_text: str) -> Response[str]:
        return Response(content="placeholder", cost=0.00)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.phase_5
class TestWorkflowTopology:
    """WORKFLOW topology — wraps a Workflow inside Swarm."""

    async def test_swarm_with_workflow_topology_runs_workflow(self) -> None:
        """Swarm with WORKFLOW topology and workflow= runs the wrapped workflow."""
        wf = Workflow("test-wf").step(_StepAgent)
        placeholder = _PlaceholderAgent()

        swarm = Swarm(
            agents=[placeholder],
            goal="hello world",
            config=SwarmConfig(topology=SwarmTopology.WORKFLOW),
            workflow=wf,
        )
        result = await swarm.run()
        assert "processed: hello world" in result.content

    async def test_workflow_topology_missing_workflow_raises(self) -> None:
        """WORKFLOW topology without workflow= raises ValueError."""
        placeholder = _PlaceholderAgent()
        swarm = Swarm(
            agents=[placeholder],
            goal="no workflow",
            config=SwarmConfig(topology=SwarmTopology.WORKFLOW),
        )
        with pytest.raises(ValueError, match="workflow="):
            await swarm.run()

    async def test_workflow_results_become_swarm_result(self) -> None:
        """Workflow output is surfaced as SwarmResult.content."""
        wf = Workflow("result-wf").step(_StepAgent)
        placeholder = _PlaceholderAgent()

        swarm = Swarm(
            agents=[placeholder],
            goal="my input",
            config=SwarmConfig(topology=SwarmTopology.WORKFLOW),
            workflow=wf,
        )
        result = await swarm.run()
        assert result.content != ""

    async def test_swarm_pause_cascades_to_workflow(self) -> None:
        """swarm.pause() forwards to the inner workflow's pause() method."""
        paused: list[bool] = []

        class _PauseTrackingWorkflow(Workflow):
            async def pause(self, *args: object, **kwargs: object) -> None:  # type: ignore[override]
                paused.append(True)

        wf = _PauseTrackingWorkflow("pause-wf").step(_StepAgent)
        placeholder = _PlaceholderAgent()

        swarm = Swarm(
            agents=[placeholder],
            goal="pause test",
            config=SwarmConfig(topology=SwarmTopology.WORKFLOW),
            workflow=wf,
        )

        # Run in background then pause
        swarm.play()
        await swarm.pause()
        # Verify workflow.pause() was called
        assert paused, "Expected workflow.pause() to be called when swarm.pause() is called"
        # Cancel to clean up
        await swarm.cancel()

    async def test_workflow_topology_injects_swarm_context(self) -> None:
        """WORKFLOW topology injects SwarmContext into the workflow before running."""
        from syrin.swarm._registry import SwarmContext

        injected_ctx: list[object] = []

        class _CtxCapture(Agent):
            model = Model.Almock()
            system_prompt = "ctx capture"

            async def arun(self, input_text: str) -> object:  # type: ignore[override]
                ctx = getattr(self, "_swarm_context", None)
                if ctx is not None:
                    injected_ctx.append(ctx)
                from syrin.response import Response

                return Response(content="ok", cost=0.0)

        wf = Workflow("ctx-wf").step(_CtxCapture)
        placeholder = _PlaceholderAgent()

        swarm = Swarm(
            agents=[placeholder],
            goal="inject test",
            config=SwarmConfig(topology=SwarmTopology.WORKFLOW),
            workflow=wf,
        )
        await swarm.run()
        assert len(injected_ctx) == 1, "SwarmContext should have been injected into workflow agent"
        assert isinstance(injected_ctx[0], SwarmContext)
        assert injected_ctx[0].goal == "inject test"

    async def test_workflow_topology_swarm_id_propagated(self) -> None:
        """Injected SwarmContext has swarm_id matching the swarm's run ID."""
        from syrin.swarm._registry import SwarmContext

        captured: list[SwarmContext] = []

        class _SwarmIdAgent(Agent):
            model = Model.Almock()
            system_prompt = "swarm id"

            async def arun(self, input_text: str) -> object:  # type: ignore[override]
                ctx = getattr(self, "_swarm_context", None)
                if isinstance(ctx, SwarmContext):
                    captured.append(ctx)
                from syrin.response import Response

                return Response(content="ok", cost=0.0)

        wf = Workflow("id-wf").step(_SwarmIdAgent)
        placeholder = _PlaceholderAgent()

        swarm = Swarm(
            agents=[placeholder],
            goal="id test",
            config=SwarmConfig(topology=SwarmTopology.WORKFLOW),
            workflow=wf,
        )
        await swarm.run()
        assert len(captured) == 1
        assert len(captured[0].swarm_id) > 0
