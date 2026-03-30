"""Model/provider use case: switch model, resolve fallback provider.

Agent delegates to functions here. Public API stays on Agent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from syrin.agent._helpers import _resolve_provider
from syrin.model import Model

if TYPE_CHECKING:
    from syrin.agent import Agent
    from syrin.providers.base import Provider
    from syrin.types import ModelConfig


def switch_model(agent: Agent, model: Model | Any, reason: str = "") -> None:  # type: ignore[explicit-any]
    """Change the LLM used by the agent at runtime."""
    from_model = agent._model_config.model_id if agent._model_config is not None else None

    if isinstance(model, Model):
        agent._model = model
        agent._model_config = model.to_config()
    else:
        agent._model = None
        agent._model_config = model

    to_model = agent._model_config.model_id if agent._model_config is not None else None
    agent._provider = _resolve_provider(agent._model, agent._model_config)

    _emit_model_switched(agent, from_model, to_model, reason)


def _emit_model_switched(
    agent: Agent,
    from_model: str | None,
    to_model: str | None,
    reason: str,
) -> None:
    """Emit Hook.MODEL_SWITCHED if the agent has an events system."""
    if not hasattr(agent, "_emit_event"):
        return
    try:
        from syrin.enums import Hook
        from syrin.events import EventContext

        ctx = EventContext(from_model=from_model, to_model=to_model, reason=reason)
        agent._emit_event(Hook.MODEL_SWITCHED, ctx)
    except Exception:
        pass


def resolve_fallback_provider(agent: Agent) -> tuple[Provider, ModelConfig]:
    """Resolve fallback model to (provider, config). Cached on agent."""
    if agent._fallback_provider is not None and agent._fallback_model_config is not None:
        return agent._fallback_provider, agent._fallback_model_config
    cb = agent._circuit_breaker
    if cb is None:
        raise ValueError("circuit_breaker is not set")
    fallback = cb.fallback
    if fallback is None:
        raise ValueError("circuit_breaker has no fallback")
    fallback_model = Model(model_id=fallback) if isinstance(fallback, str) else fallback
    prov = fallback_model.get_provider()
    cfg = fallback_model.to_config()
    agent._fallback_provider = prov
    agent._fallback_model_config = cfg
    return prov, cfg
