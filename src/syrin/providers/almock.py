"""Almock (An LLM Mock) provider — no API calls, configurable response and cost for testing."""

from __future__ import annotations

import asyncio
import random

from syrin.enums import AlmockPricing
from syrin.tool import ToolSpec
from syrin.types import (
    Message,
    ModelConfig,
    ProviderResponse,
    TokenUsage,
)

from .base import Provider

# USD per 1M tokens (input, output) per tier — for budget testing
ALMOCK_PRICING: dict[str, tuple[float, float]] = {
    AlmockPricing.LOW: (0.01, 0.02),
    AlmockPricing.MEDIUM: (0.50, 1.50),
    AlmockPricing.HIGH: (5.0, 15.0),
    AlmockPricing.ULTRA_HIGH: (30.0, 60.0),
}

DEFAULT_LOREM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
    "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris. "
)


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def _lorem_ipsum(length: int) -> str:
    """Return Lorem Ipsum text of at least `length` characters."""
    if length <= 0:
        return ""
    out: list[str] = []
    n = 0
    while n < length:
        out.append(DEFAULT_LOREM)
        n += len(DEFAULT_LOREM)
    s = "".join(out)
    return s[:length] if len(s) > length else s


class AlmockProvider(Provider):
    """Provider that returns mocked responses with configurable latency and content.

    No real API calls. Use for development and tests without API keys or cost.
    """

    async def complete(  # type: ignore[override]
        self,
        messages: list[Message],
        model: ModelConfig,
        tools: list[ToolSpec] | None = None,
        *,
        max_tokens: int = 1024,
        latency_min: float = 1.0,
        latency_max: float = 3.0,
        latency_seconds: float | None = None,
        response_mode: str = "lorem",
        custom_response: str | None = None,
        lorem_length: int = 100,
        **kwargs: object,
    ) -> ProviderResponse:
        """Return a mocked response after optional delay.

        Args:
            messages: Input messages (used to estimate input tokens).
            model: Model config (provider uses model_id for token/cost reporting).
            tools: Ignored for mock; no tool calls unless custom_response encodes them.
            max_tokens: Ignored; output length driven by response_mode/lorem_length/custom_response.
            latency_min: Min delay in seconds (used when latency_seconds not set).
            latency_max: Max delay in seconds (used when latency_seconds not set).
            latency_seconds: Fixed delay in seconds; must be > 0. Overrides latency_min/max.
            response_mode: "lorem" = Lorem Ipsum of lorem_length; "custom" = custom_response.
            custom_response: Used when response_mode == "custom".
            lorem_length: Length in characters when response_mode == "lorem".
        """
        # Validate latency: user-provided must be > 0
        if latency_seconds is not None:
            if latency_seconds <= 0:
                raise ValueError("latency_seconds must be greater than 0")
            delay = latency_seconds
        else:
            delay = random.uniform(
                max(0.0, latency_min),
                max(0.0, latency_max),
            )

        if delay > 0:
            await asyncio.sleep(delay)

        if response_mode == "custom" and custom_response is not None:
            content = custom_response
        else:
            # lorem or fallback
            length = lorem_length if lorem_length > 0 else 100
            content = _lorem_ipsum(length)

        def _to_str(c: str | list[dict[str, object]] | None) -> str:
            if c is None:
                return ""
            return c if isinstance(c, str) else str(c)

        input_tokens = sum(_estimate_tokens(_to_str(m.content)) for m in messages) or 1
        output_tokens = _estimate_tokens(content) or 1

        return ProviderResponse(
            content=content,
            tool_calls=[],
            token_usage=TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            ),
            stop_reason="end_turn",
            raw_response={"almock": True, "latency_seconds": delay},
        )
