"""Checkpoint use-case helpers for Agent public methods."""

from __future__ import annotations

from typing import TYPE_CHECKING

from syrin.agent._checkpoint import (
    get_checkpoint_report as _checkpoint_get_report,
)
from syrin.agent._checkpoint import (
    list_checkpoints as _checkpoint_list,
)
from syrin.agent._checkpoint import (
    load_checkpoint as _checkpoint_load,
)
from syrin.agent._checkpoint import (
    maybe_checkpoint as _checkpoint_maybe,
)
from syrin.agent._checkpoint import (
    save_checkpoint as _checkpoint_save,
)
from syrin.response import AgentReport

if TYPE_CHECKING:
    from syrin.agent import Agent


def save_checkpoint(agent: Agent, name: str | None = None, reason: str | None = None) -> str | None:
    """Save a snapshot of the agent state via the configured checkpointer."""
    return _checkpoint_save(agent, name=name, reason=reason)


def maybe_checkpoint(agent: Agent, reason: str) -> None:
    """Create an automatic checkpoint when trigger settings allow it."""
    _checkpoint_maybe(agent, reason)


def load_checkpoint(agent: Agent, checkpoint_id: str) -> bool:
    """Restore a previously saved checkpoint by identifier."""
    return _checkpoint_load(agent, checkpoint_id)


def list_checkpoints(agent: Agent, name: str | None = None) -> list[str]:
    """List checkpoint identifiers for the given agent name."""
    return _checkpoint_list(agent, name=name)


def get_checkpoint_report(agent: Agent) -> AgentReport:
    """Return checkpoint information inside the agent report structure."""
    return _checkpoint_get_report(agent)
