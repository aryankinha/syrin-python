"""WORKFLOW topology — wraps a Workflow inside a Swarm."""

from __future__ import annotations

from typing import TYPE_CHECKING

from syrin.enums import Hook

if TYPE_CHECKING:
    from syrin.swarm._core import Swarm
    from syrin.swarm._result import SwarmResult
    from syrin.workflow._core import Workflow


async def run_workflow_topology(
    swarm: Swarm,
    workflow: Workflow,
) -> SwarmResult:
    """WORKFLOW topology: wraps a :class:`~syrin.workflow.Workflow` with Swarm capabilities.

    Runs *workflow* with the swarm's ``goal`` as input.  The workflow result is
    wrapped in a :class:`~syrin.swarm._result.SwarmResult` so callers receive a
    uniform return type regardless of topology.

    ``swarm.pause()`` on a WORKFLOW topology swarm cascades to the inner
    workflow's ``pause()`` method (handled in
    :meth:`~syrin.swarm.Swarm.pause`).

    Args:
        swarm: The owning :class:`~syrin.swarm.Swarm` instance.
        workflow: The :class:`~syrin.workflow.Workflow` to execute.

    Returns:
        :class:`~syrin.swarm._result.SwarmResult` whose ``content`` field
        holds the workflow's final output.
    """
    from syrin.swarm._registry import SwarmContext  # noqa: PLC0415
    from syrin.swarm._result import SwarmResult  # noqa: PLC0415

    swarm._fire_event(
        Hook.SWARM_STARTED,
        {
            "goal": swarm.goal,
            "agent_count": swarm.agent_count,
            "topology": "workflow",
        },
    )

    # Inject swarm context into the workflow so its agents get
    # MemoryBus, A2A, and pool access via _swarm_context.
    swarm_ctx = SwarmContext(
        goal=swarm.goal,
        pool=None,  # BudgetPool not required for WORKFLOW topology
        config=swarm.config,
        swarm_id=swarm._run_id,
    )
    workflow._swarm_context = swarm_ctx

    # Store executor so swarm.pause() can forward to workflow.pause()
    # (Workflow.play() sets self._executor internally).
    handle = workflow.play(swarm.goal)
    response = await handle.wait()

    content = getattr(response, "content", "") or ""
    cost = getattr(response, "cost", 0.0) or 0.0

    swarm._fire_event(
        Hook.SWARM_ENDED,
        {
            "goal": swarm.goal,
            "status": "success",
            "total_agents": swarm.agent_count,
            "succeeded": swarm.agent_count,
            "total_spent": cost,
        },
    )

    return SwarmResult(
        content=content,
        cost_breakdown={"workflow": cost},
    )


__all__ = ["run_workflow_topology"]
