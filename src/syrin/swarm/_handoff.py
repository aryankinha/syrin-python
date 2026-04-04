"""SwarmHandoffContext — mutable context passed between sequential swarm agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from syrin.response import Response


@dataclass
class SwarmHandoffContext:
    """Mutable context emitted via :attr:`~syrin.enums.Hook.SWARM_AGENT_HANDOFF`.

    Hook handlers can mutate :attr:`next_input` to change what the next agent
    receives, or set :attr:`skip_next` to ``True`` to skip the next agent
    entirely.  These attributes are ignored for
    :attr:`~syrin.enums.SwarmTopology.PARALLEL` topology where all agents run
    simultaneously.

    Attributes:
        next_input: Input string that will be passed to the next agent.
            Hook handlers may overwrite this to inject modified content.
        skip_next: When set to ``True`` by a hook handler, the next agent in
            sequence will not be run.  Defaults to ``False``.
        result: The :class:`~syrin.response.Response` produced by the agent
            that just completed.
        current_agent: Class name of the agent that just finished.
        next_agent: Class name of the agent scheduled to run next, or
            ``None`` if this was the last agent.

    Example::

        @swarm.events.on(Hook.SWARM_AGENT_HANDOFF)
        def gatekeeper(ctx: EventContext) -> None:
            handoff = ctx["handoff"]
            if "skip this" in handoff.result.content:
                handoff.skip_next = True
            else:
                handoff.next_input = handoff.next_input.upper()
    """

    next_input: str
    """Input passed to the next agent (writable by hook handlers)."""

    result: Response[str]
    """Output from the agent that just completed."""

    current_agent: str
    """Class name of the agent that just completed."""

    next_agent: str | None = None
    """Class name of the next scheduled agent, or ``None`` if last."""

    skip_next: bool = False
    """Set to ``True`` to skip the next agent in sequence."""


__all__ = ["SwarmHandoffContext"]
