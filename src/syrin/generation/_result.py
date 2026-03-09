"""Result type for image/video generation. Kept in a separate module to avoid circular imports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GenerationResult:
    """Result of image or video generation.

    Attributes:
        success: True if generation succeeded.
        url: Data URL (e.g. data:image/png;base64,...) or HTTP URL when available.
        content_type: MIME type (e.g. image/png, video/mp4).
        content_bytes: Raw bytes when url is a data URL or when no URL was returned.
        error: Error message when success is False.
        metadata: Provider-specific extras. Built-in providers set cost_usd and model_name
            for budget tracking when the agent has a budget.
    """

    success: bool
    url: str = ""
    content_type: str = ""
    content_bytes: bytes | None = None
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
