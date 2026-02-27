"""Configuration for agent serving."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from syrin.enums import ServeProtocol

if TYPE_CHECKING:
    from syrin.serve.auth import AuthMiddleware
    from syrin.serve.cors import CORSConfig


@dataclass
class ServeConfig:
    """Configuration for agent.serve() and serving layer.

    Use when calling agent.serve(**config) or agent.serve(config=ServeConfig(...)).
    MCP routes are driven by syrin.MCP in tools — no enable_mcp flag.
    Discovery is auto-detected when agent has name; set enable_discovery=False to force off.
    """

    protocol: ServeProtocol = ServeProtocol.HTTP
    host: str = "0.0.0.0"
    port: int = 8000
    route_prefix: str = ""
    auth: AuthMiddleware | None = None
    cors: CORSConfig | None = None
    stream: bool = True
    include_metadata: bool = True
    debug: bool = False
    enable_playground: bool = False
    enable_discovery: bool | None = None
