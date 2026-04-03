"""Agent reference Protocol — shared duck-type for agent identity.

All swarm subsystems (A2ARouter, BroadcastBus, MemoryBus, SwarmController,
SwarmAuthorityGuard, MonitorLoop) accept :class:`AgentRef` instances instead
of raw string IDs.  This avoids typo-silenced routing bugs and keeps
multi-agent communication fully type-safe.

Any object that exposes an ``agent_id`` property satisfies ``AgentRef``.
:class:`~syrin.agent._core.Agent` instances satisfy it automatically.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AgentRef(Protocol):
    """Structural protocol satisfied by any :class:`~syrin.agent._core.Agent` instance.

    All swarm APIs accept ``AgentRef`` so developers pass agent objects
    directly rather than constructing string IDs manually.

    Attributes:
        agent_id: Unique identifier automatically assigned to the agent.
    """

    @property
    def agent_id(self) -> str:
        """Unique identifier for this agent."""
        ...


def _aid(agent: AgentRef | str) -> str:
    """Extract the ``agent_id`` string from an :class:`AgentRef` or plain string.

    Args:
        agent: Any object satisfying the :class:`AgentRef` protocol, or a
            plain string agent ID.

    Returns:
        The agent's unique identifier string.
    """
    if isinstance(agent, str):
        return agent
    return agent.agent_id


__all__ = ["AgentRef", "_aid"]
