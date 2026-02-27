"""CORS configuration for agent serving."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CORSConfig:
    """CORS configuration for HTTP serve.

    Maps to FastAPI/Starlette CORSMiddleware. Use with ServeConfig(cors=CORSConfig(...)).
    """

    origins: list[str] = field(default_factory=list)
    allow_credentials: bool = False
    allow_methods: list[str] = field(default_factory=lambda: ["*"])
    allow_headers: list[str] = field(default_factory=lambda: ["*"])
    expose_headers: list[str] = field(default_factory=list)
