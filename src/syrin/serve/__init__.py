"""Agent serving layer — HTTP, CLI, STDIO protocols."""

from syrin.serve.auth import BearerTokenAuth
from syrin.serve.config import ServeConfig
from syrin.serve.cors import CORSConfig
from syrin.serve.http import build_router
from syrin.serve.router import AgentRouter

__all__ = [
    "AgentRouter",
    "BearerTokenAuth",
    "build_router",
    "CORSConfig",
    "ServeConfig",
]
