"""Agent serving layer — HTTP, CLI, STDIO protocols."""

from syrin.serve.config import ServeConfig
from syrin.serve.discovery import (
    AgentCard,
    AgentCardAuth,
    AgentCardProvider,
    build_agent_card_json,
)
from syrin.serve.http import build_router
from syrin.serve.router import AgentRouter

__all__ = [
    "AgentCard",
    "AgentCardAuth",
    "AgentCardProvider",
    "AgentRouter",
    "build_agent_card_json",
    "build_router",
    "ServeConfig",
]
