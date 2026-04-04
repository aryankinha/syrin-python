"""MonitorLoop — async supervisor quality assessment loop."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass

from syrin.enums import Hook, InterventionAction, MonitorEventType
from syrin.swarm._agent_ref import AgentRef, _aid

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass
class MonitorEvent:
    """Event emitted by :class:`MonitorLoop`.

    Attributes:
        agent_id: ID of the agent this event relates to.
        event_type: :class:`~syrin.enums.MonitorEventType` classifying the event.
        data: Arbitrary metadata dict accompanying the event.
    """

    agent_id: str
    event_type: MonitorEventType
    data: dict[str, object]


class MaxInterventionsExceeded(Exception):
    """Raised when the :class:`MonitorLoop` intervention limit is exceeded.

    Attributes:
        limit: The configured maximum intervention count.
        count: The number of interventions attempted.
    """

    def __init__(self, limit: int, count: int) -> None:
        """Initialise MaxInterventionsExceeded.

        Args:
            limit: Configured maximum.
            count: Number of interventions attempted.
        """
        super().__init__(
            f"MaxInterventionsExceeded: attempted {count} interventions, limit is {limit}"
        )
        self.limit = limit
        self.count = count


# ---------------------------------------------------------------------------
# MonitorLoop
# ---------------------------------------------------------------------------


class MonitorLoop:
    """Async context manager that monitors agents and yields :class:`MonitorEvent` objects.

    Each monitored agent gets a polling task that pushes HEARTBEAT events into
    an internal :class:`asyncio.Queue` at ``poll_interval`` seconds.  External
    callers can push OUTPUT_READY events via :meth:`notify_agent_output` and
    perform bounded interventions via :meth:`intervene`.

    Example::

        async with MonitorLoop(targets=["w1", "w2"], poll_interval=1.0) as monitor:
            async for event in monitor:
                if event.event_type == MonitorEventType.OUTPUT_READY:
                    print(f"{event.agent_id} produced output: {event.data}")
                    break
    """

    def __init__(
        self,
        targets: list[AgentRef],
        poll_interval: float = 1.0,
        max_interventions: int = 0,
        fire_event_fn: Callable[[Hook, dict[str, object]], None] | None = None,
    ) -> None:
        """Initialise MonitorLoop.

        Args:
            targets: Agent instances to monitor.
            poll_interval: Seconds between HEARTBEAT polls.  Defaults to 1.0.
            max_interventions: Maximum number of :meth:`intervene` calls
                allowed.  ``0`` means unlimited.
            fire_event_fn: Optional hook emitter.
        """
        target_ids = [_aid(a) for a in targets]
        self._targets: list[str] = target_ids
        self._active_targets: set[str] = set(target_ids)
        self._poll_interval = poll_interval
        self._max_interventions = max_interventions
        self._intervention_count = 0
        self._fire: Callable[[Hook, dict[str, object]], None] = fire_event_fn or (
            lambda _h, _d: None
        )
        self._queue: asyncio.Queue[MonitorEvent] = asyncio.Queue()
        self._poll_tasks: list[asyncio.Task[None]] = []

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> MonitorLoop:
        """Start polling tasks for all target agents.

        Returns:
            The :class:`MonitorLoop` instance itself.
        """
        for agent_id in self._targets:
            task: asyncio.Task[None] = asyncio.create_task(
                self._poll_agent(agent_id), name=f"monitor-poll-{agent_id}"
            )
            self._poll_tasks.append(task)
        return self

    async def __aexit__(self, *args: object) -> None:
        """Cancel all internal poll tasks and drain the queue."""
        for task in self._poll_tasks:
            if not task.done():
                task.cancel()
        # Wait for tasks to finish cancellation
        if self._poll_tasks:
            await asyncio.gather(*self._poll_tasks, return_exceptions=True)
        self._poll_tasks.clear()

    # ------------------------------------------------------------------
    # Async iteration
    # ------------------------------------------------------------------

    def __aiter__(self) -> MonitorLoop:
        """Return self as the async iterator."""
        return self

    async def __anext__(self) -> MonitorEvent:
        """Pull the next event from the internal queue.

        Returns:
            The next :class:`MonitorEvent`.
        """
        return await self._queue.get()

    # ------------------------------------------------------------------
    # Internal polling
    # ------------------------------------------------------------------

    async def _poll_agent(self, agent_id: str) -> None:
        """Continuously emit HEARTBEAT events for *agent_id*.

        Args:
            agent_id: Agent to poll.
        """
        try:
            while True:
                await asyncio.sleep(self._poll_interval)
                if agent_id in self._active_targets:
                    await self._queue.put(
                        MonitorEvent(
                            agent_id=agent_id,
                            event_type=MonitorEventType.HEARTBEAT,
                            data={},
                        )
                    )
        except asyncio.CancelledError:
            pass

    # ------------------------------------------------------------------
    # Public controls
    # ------------------------------------------------------------------

    def release(self, agent: AgentRef) -> None:
        """Stop monitoring *agent*.

        After calling this, no further HEARTBEAT events will be produced
        for *agent*.  In-flight events already in the queue are unaffected.

        Args:
            agent: Agent instance to release from monitoring.
        """
        self._active_targets.discard(_aid(agent))

    async def intervene(
        self, agent: AgentRef, action: InterventionAction, **kwargs: object
    ) -> None:
        """Perform an intervention on *agent*.

        Args:
            agent: Target agent instance for the intervention.
            action: :class:`~syrin.enums.InterventionAction` to perform.
            **kwargs: Additional keyword arguments (e.g. ``context=...``).

        Raises:
            MaxInterventionsExceeded: If the configured *max_interventions*
                limit has been reached.
        """
        aid = _aid(agent)
        if self._max_interventions > 0 and self._intervention_count >= self._max_interventions:
            self._fire(
                Hook.AGENT_ESCALATION,
                {
                    "agent_id": aid,
                    "action": str(action),
                    "intervention_count": self._intervention_count,
                    "max_interventions": self._max_interventions,
                },
            )
            raise MaxInterventionsExceeded(
                limit=self._max_interventions,
                count=self._intervention_count + 1,
            )
        self._intervention_count += 1

    def notify_agent_output(self, agent: AgentRef, output: str) -> None:
        """Enqueue an OUTPUT_READY event for *agent*.

        Called externally (e.g. from a swarm executor or test) when an agent
        produces a new output.

        Args:
            agent: Agent instance that produced the output.
            output: The output string (stored in ``data["output"]``).
        """
        event = MonitorEvent(
            agent_id=_aid(agent),
            event_type=MonitorEventType.OUTPUT_READY,
            data={"output": output},
        )
        self._queue.put_nowait(event)
