"""SwarmController — agent control actions for a swarm."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from syrin.enums import AgentPermission, AgentRole, AgentStatus, PauseMode
from syrin.swarm._agent_ref import AgentRef, _aid
from syrin.swarm._authority import SwarmAuthorityGuard

_MAX_SUMMARY_LEN: int = 500


# ---------------------------------------------------------------------------
# AgentStateSnapshot
# ---------------------------------------------------------------------------


@dataclass
class AgentStateSnapshot:
    """State snapshot for a single agent.

    Attributes:
        agent_id: Unique identifier of the agent.
        status: Current :class:`~syrin.enums.AgentStatus`.
        role: :class:`~syrin.enums.AgentRole` assigned to this agent.
        last_output_summary: Truncated (≤ 500 chars) summary of the last output.
        cost_spent: Total cost spent by this agent so far.
        task: Description of the current task.
        context_override: Injected context string, or ``None`` if unset.
        supervisor_id: ID of the supervisor agent, or ``None`` if this agent
            has no supervisor.
    """

    agent_id: str
    status: AgentStatus
    role: AgentRole
    last_output_summary: str
    cost_spent: float
    task: str
    context_override: str | None
    supervisor_id: str | None

    def __post_init__(self) -> None:
        """Truncate last_output_summary to ≤ 500 characters."""
        if len(self.last_output_summary) > _MAX_SUMMARY_LEN:
            self.last_output_summary = self.last_output_summary[:_MAX_SUMMARY_LEN]


# ---------------------------------------------------------------------------
# SwarmController
# ---------------------------------------------------------------------------


class SwarmController:
    """Agent control actions for a swarm.

    All actions pass through a :class:`~syrin.swarm._authority.SwarmAuthorityGuard`
    before executing.  Successful actions are recorded via
    :meth:`~syrin.swarm._authority.SwarmAuthorityGuard.record_action`.

    Example::

        guard = SwarmAuthorityGuard(
            roles={"sup": AgentRole.SUPERVISOR, "w1": AgentRole.WORKER},
            teams={"sup": ["w1"]},
        )
        ctrl = SwarmController(
            actor_id="sup",
            guard=guard,
            state_registry=state,
            task_registry=tasks,
        )
        await ctrl.pause_agent("w1")
    """

    def __init__(
        self,
        actor_id: AgentRef | str,
        guard: SwarmAuthorityGuard,
        state_registry: dict[str, AgentStateSnapshot],
        task_registry: dict[str, asyncio.Task[object]],
    ) -> None:
        """Initialise SwarmController.

        Args:
            actor_id: Agent instance or agent ID string initiating control actions.
            guard: Authority guard for permission checks.
            state_registry: Mapping of agent_id → :class:`AgentStateSnapshot`.
            task_registry: Mapping of agent_id → running :class:`asyncio.Task`.
        """
        self._actor: AgentRef | str = actor_id
        self._actor_id: str = _aid(actor_id)
        self._guard = guard
        self._state: dict[str, AgentStateSnapshot] = state_registry
        self._tasks: dict[str, asyncio.Task[object]] = task_registry

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require(self, target: AgentRef | str, permission: AgentPermission) -> None:
        """Check permission via guard; raise AgentPermissionError if denied."""
        self._guard.require(self._actor, permission, target)

    def _cancel_task(self, target_id: str) -> None:
        """Cancel the asyncio task for *target_id* if one exists."""
        task = self._tasks.get(target_id)
        if task is not None and not task.done():
            task.cancel()

    def _set_status(self, target_id: str, status: AgentStatus) -> None:
        """Update the status in the state registry for *target_id*."""
        snap = self._state.get(target_id)
        if snap is not None:
            snap.status = status

    # ------------------------------------------------------------------
    # Control actions
    # ------------------------------------------------------------------

    async def pause_agent(self, target: AgentRef, *, mode: PauseMode = PauseMode.IMMEDIATE) -> None:
        """Pause the target agent.

        Args:
            target: Agent instance to pause.
            mode: When to apply the pause.
                :attr:`~syrin.enums.PauseMode.IMMEDIATE` pauses right away.
                :attr:`~syrin.enums.PauseMode.DRAIN` waits for the current
                step to complete before pausing.

        Raises:
            AgentPermissionError: If the actor lacks CONTROL permission.
        """
        target_id = _aid(target)
        self._require(target, AgentPermission.CONTROL)
        if mode == PauseMode.DRAIN:
            self._set_status(target_id, AgentStatus.DRAINING)
        else:
            self._set_status(target_id, AgentStatus.PAUSED)
        self._guard.record_action(self._actor_id, target_id, "pause")

    async def resume_agent(self, target: AgentRef) -> None:
        """Resume a paused agent.

        Args:
            target: Agent instance to resume.

        Raises:
            AgentPermissionError: If the actor lacks CONTROL permission.
        """
        target_id = _aid(target)
        self._require(target, AgentPermission.CONTROL)
        self._set_status(target_id, AgentStatus.RUNNING)
        self._guard.record_action(self._actor_id, target_id, "resume")

    async def skip_agent(self, target: AgentRef) -> None:
        """Skip the target agent's current task and set status to IDLE.

        Args:
            target: Agent instance to skip.

        Raises:
            AgentPermissionError: If the actor lacks CONTROL permission.
        """
        target_id = _aid(target)
        self._require(target, AgentPermission.CONTROL)
        self._cancel_task(target_id)
        self._set_status(target_id, AgentStatus.IDLE)
        self._guard.record_action(self._actor_id, target_id, "skip")

    async def change_context(self, target: AgentRef, new_context: str) -> None:
        """Inject a new context override for the target agent.

        Args:
            target: Agent instance whose context to change.
            new_context: The new context string to inject.

        Raises:
            AgentPermissionError: If the actor lacks CONTROL permission.
        """
        target_id = _aid(target)
        self._require(target, AgentPermission.CONTROL)
        snap = self._state.get(target_id)
        if snap is not None:
            snap.context_override = new_context
        self._guard.record_action(self._actor_id, target_id, "change_context")

    async def kill_agent(self, target: AgentRef) -> None:
        """Forcibly terminate the target agent.

        Args:
            target: Agent instance to terminate.

        Raises:
            AgentPermissionError: If the actor lacks CONTROL permission.
        """
        target_id = _aid(target)
        self._require(target, AgentPermission.CONTROL)
        self._cancel_task(target_id)
        self._set_status(target_id, AgentStatus.KILLED)
        self._guard.record_action(self._actor_id, target_id, "kill")

    async def read_agent_state(self, target: AgentRef) -> AgentStateSnapshot:
        """Return the current :class:`AgentStateSnapshot` for *target*.

        Args:
            target: Agent instance to read.

        Returns:
            :class:`AgentStateSnapshot` for the target agent.

        Raises:
            AgentPermissionError: If the actor lacks READ permission.
            KeyError: If the agent is not registered in the state registry.
        """
        target_id = _aid(target)
        self._require(target, AgentPermission.READ)
        return self._state[target_id]
