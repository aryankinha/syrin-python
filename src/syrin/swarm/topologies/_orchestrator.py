"""ORCHESTRATOR topology — first agent decomposes, rest execute."""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

from syrin.enums import AgentStatus, Hook

if TYPE_CHECKING:
    from syrin.agent._core import Agent
    from syrin.response import Response
    from syrin.swarm._core import Swarm
    from syrin.swarm._result import SwarmResult

logger = logging.getLogger(__name__)


def _parse_task_list(content: str) -> list[dict[str, str]]:
    """Extract a JSON task list from *content*.

    Looks for the first ``[...]`` block in *content* and tries to parse it as
    ``list[dict]`` where each dict has ``"agent"`` and ``"task"`` keys.

    Args:
        content: Orchestrator output string.

    Returns:
        List of ``{"agent": str, "task": str}`` dicts.  Empty list if no
        valid task list is found.
    """
    # Try to extract a JSON array from the output
    match = re.search(r"\[.*\]", content, re.DOTALL)
    if not match:
        return []
    try:
        raw = json.loads(match.group())
    except json.JSONDecodeError:
        return []
    if not isinstance(raw, list):
        return []
    tasks: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        agent_name = item.get("agent")
        task_text = item.get("task")
        if isinstance(agent_name, str) and isinstance(task_text, str):
            tasks.append({"agent": agent_name, "task": task_text})
    return tasks


async def run_orchestrator(
    swarm: Swarm,
    agents: list[Agent],
    goal: str,
    input: str,
) -> SwarmResult:
    """ORCHESTRATOR topology: first agent decomposes, rest execute.

    The first agent in *agents* acts as the orchestrator.  It receives
    *input* and is expected to emit a JSON task list of the form::

        [{"agent": "AgentName", "task": "task description"}, ...]

    Each assignment is dispatched to the matching agent from *agents* (by
    class name).  Results are aggregated into a :class:`~syrin.swarm._result.SwarmResult`.

    Unknown agent names in the orchestrator output are skipped with a
    warning.  If the orchestrator produces no task assignments the
    orchestrator's own output is returned directly.

    Args:
        swarm: The owning :class:`~syrin.swarm.Swarm` instance.
        agents: Full list of agents, where ``agents[0]`` is the orchestrator.
        goal: Shared swarm goal string.
        input: Input to pass to the orchestrator.

    Returns:
        :class:`~syrin.swarm._result.SwarmResult` with aggregated content.
    """
    from syrin.swarm._result import AgentBudgetSummary, SwarmBudgetReport, SwarmResult

    swarm._fire_event(
        Hook.SWARM_STARTED,
        {"goal": goal, "agent_count": len(agents), "topology": "orchestrator"},
    )

    orchestrator = agents[0]
    worker_by_name: dict[str, Agent] = {type(a).__name__: a for a in agents[1:]}

    orch_name = type(orchestrator).__name__
    swarm._set_agent_status(orch_name, AgentStatus.RUNNING)
    swarm._fire_event(Hook.AGENT_JOINED_SWARM, {"agent_name": orch_name})

    orch_response: Response[str] = await orchestrator.arun(input)
    orch_cost = getattr(orch_response, "cost", 0.0) or 0.0

    swarm._set_agent_status(orch_name, AgentStatus.STOPPED)
    swarm._fire_event(Hook.AGENT_LEFT_SWARM, {"agent_name": orch_name, "cost": orch_cost})

    task_list = _parse_task_list(getattr(orch_response, "content", "") or "")

    if not task_list:
        # No tasks assigned — return the orchestrator's output directly
        swarm._fire_event(
            Hook.SWARM_ENDED,
            {"goal": goal, "status": "success", "total_agents": 1, "succeeded": 1},
        )
        return SwarmResult(
            content=getattr(orch_response, "content", "") or "",
            cost_breakdown={orch_name: orch_cost},
            agent_results=[orch_response],
        )

    # Dispatch tasks
    cost_breakdown: dict[str, float] = {orch_name: orch_cost}
    agent_results: list[Response[str]] = [orch_response]
    succeeded = 1

    for assignment in task_list:
        worker_name = assignment["agent"]
        task_text = assignment["task"]

        worker = worker_by_name.get(worker_name)
        if worker is None:
            logger.warning(
                "Orchestrator assigned task to unknown agent %r — skipping. Known workers: %s",
                worker_name,
                sorted(worker_by_name.keys()),
            )
            continue

        swarm._set_agent_status(worker_name, AgentStatus.RUNNING)
        swarm._fire_event(Hook.AGENT_JOINED_SWARM, {"agent_name": worker_name})

        # Build handoff context and emit SWARM_AGENT_HANDOFF
        from syrin.swarm._handoff import SwarmHandoffContext

        # Determine next agent name (if any)
        remaining = task_list[task_list.index(assignment) + 1 :]
        for nxt in remaining:
            if nxt["agent"] in worker_by_name:
                nxt["agent"]
                break

        handoff = SwarmHandoffContext(
            next_input=task_text,
            result=orch_response,
            current_agent=orch_name,
            next_agent=worker_name,
        )
        swarm._fire_event(
            Hook.SWARM_AGENT_HANDOFF,
            {
                "from_agent": orch_name,
                "to_agent": worker_name,
                "task": task_text,
                "handoff": handoff,
            },
        )

        if handoff.skip_next:
            swarm._set_agent_status(worker_name, AgentStatus.STOPPED)
            continue

        effective_input = handoff.next_input
        worker_response: Response[str] = await worker.arun(effective_input)
        worker_cost = getattr(worker_response, "cost", 0.0) or 0.0

        swarm._set_agent_status(worker_name, AgentStatus.STOPPED)
        swarm._fire_event(
            Hook.AGENT_LEFT_SWARM,
            {"agent_name": worker_name, "cost": worker_cost},
        )

        cost_breakdown[worker_name] = worker_cost
        agent_results.append(worker_response)
        succeeded += 1

    merged_content = "\n".join(getattr(r, "content", "") or "" for r in agent_results)
    total_spent = sum(cost_breakdown.values())
    per_agent = [
        AgentBudgetSummary(agent_name=n, allocated=0.0, spent=c) for n, c in cost_breakdown.items()
    ]
    budget_report = SwarmBudgetReport(per_agent=per_agent, total_spent=total_spent)

    swarm._fire_event(
        Hook.SWARM_ENDED,
        {
            "goal": goal,
            "status": "success",
            "total_agents": len(agents),
            "succeeded": succeeded,
            "total_spent": total_spent,
        },
    )

    return SwarmResult(
        content=merged_content,
        cost_breakdown=cost_breakdown,
        agent_results=agent_results,
        budget_report=budget_report,
    )


__all__ = ["run_orchestrator"]
