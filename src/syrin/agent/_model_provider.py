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


def switch_model(agent: Agent, model: Model | Any) -> None:  # type: ignore[explicit-any]
    """Change the LLM used by the agent at runtime."""
    if isinstance(model, Model):
        agent._model = model
        agent._model_config = model.to_config()
    else:
        agent._model = None
        agent._model_config = model
    agent._provider = _resolve_provider(agent._model, agent._model_config)


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
