"""Cost calculation and token counting for budget tracking."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from syrin.types import TokenUsage

# USD per 1M tokens (input, output). Keys: model_id or prefix pattern (first match wins).
# Sources: Anthropic/OpenAI public pricing; update as needed.
# IMPORTANT: More specific models must come before general ones!
MODEL_PRICING: dict[str, tuple[float, float]] = {
    # OpenAI - specific models first (more specific to less specific)
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (5.0, 15.0),
    "gpt-4-turbo": (10.0, 30.0),
    "gpt-4": (30.0, 60.0),
    "gpt-3.5-turbo": (0.50, 1.50),
    "o1-preview": (15.0, 60.0),
    "o1-mini": (3.0, 12.0),
    # Anthropic - specific models first
    "claude-opus-4-6": (15.0, 75.0),
    "claude-opus-4-5": (15.0, 75.0),
    "claude-opus-4": (15.0, 75.0),
    "claude-sonnet-4-5": (3.0, 15.0),
    "claude-sonnet-4": (3.0, 15.0),
    "claude-3-7-sonnet": (3.0, 15.0),
    "claude-3-5-sonnet": (3.0, 15.0),
    "claude-3-5-haiku": (1.0, 5.0),
    "claude-haiku-4": (1.0, 5.0),
    "claude-3-opus": (15.0, 75.0),
    "claude-3-sonnet": (3.0, 15.0),
    "claude-3-haiku": (0.25, 1.25),
    # Google
    "gemini-2.0-flash": (0.0, 0.0),  # Check current pricing
    "gemini-1.5-pro": (1.25, 5.0),
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-3-flash-preview": (0.075, 0.30),  # gemini-3-flash pricing
}


class ModelPricing:
    """Custom pricing per 1M tokens (input, output) in USD."""

    def __init__(
        self,
        input_per_1m: float = 0.0,
        output_per_1m: float = 0.0,
    ) -> None:
        self.input_per_1m = input_per_1m
        self.output_per_1m = output_per_1m


Pricing = ModelPricing


def _resolve_pricing(model_id: str) -> tuple[float, float]:
    """Return (input_per_1m, output_per_1m) for model_id. Strips provider prefix."""
    normalized = model_id.split("/")[-1] if "/" in model_id else model_id
    for key, (inp, out) in MODEL_PRICING.items():
        if normalized.startswith(key):
            return (inp, out)
    return (0.0, 0.0)


def calculate_cost(
    model_id: str,
    token_usage: TokenUsage,
    pricing_override: Pricing | None = None,
    pricing_resolver: Callable[[str], tuple[float, float]] | None = None,
) -> float:
    """Compute cost in USD for the given token usage and model.

    Args:
        model_id: Model identifier (e.g. openai/gpt-4o-mini).
        token_usage: Input/output token counts.
        pricing_override: Per-call fixed pricing (ModelPricing); overridden by resolver.
        pricing_resolver: Optional callable(model_id) -> (input_per_1m, output_per_1m).
            When provided, used instead of pricing_override and MODEL_PRICING.
    """
    if pricing_resolver is not None:
        inp_p, out_p = pricing_resolver(model_id)
    elif pricing_override is not None:
        inp_p, out_p = pricing_override.input_per_1m, pricing_override.output_per_1m
    else:
        inp_p, out_p = _resolve_pricing(model_id)
    input_cost = (token_usage.input_tokens / 1_000_000) * inp_p
    output_cost = (token_usage.output_tokens / 1_000_000) * out_p
    return round(input_cost + output_cost, 6)


def count_tokens(text: str, model_id: str) -> int:
    """
    Estimate token count for text. Uses tiktoken for OpenAI-style models when available;
    otherwise uses ~4 chars per token.
    """
    if not text:
        return 0
    normalized = model_id.split("/")[-1] if "/" in model_id else model_id
    try:
        import tiktoken
    except ImportError:
        return _estimate_tokens(text)
    encoding_name = "cl100k_base"
    if "gpt-4" in normalized or "gpt-3.5" in normalized or "gpt-4o" in normalized:
        try:
            enc = tiktoken.encoding_for_model("gpt-4" if "gpt-4" in normalized else "gpt-3.5-turbo")
            return len(enc.encode(text))
        except Exception:
            enc = tiktoken.get_encoding(encoding_name)
            return len(enc.encode(text))
    try:
        enc = tiktoken.get_encoding(encoding_name)
        return len(enc.encode(text))
    except Exception:
        return _estimate_tokens(text)


def _estimate_tokens(text: str) -> int:
    """Fallback: ~4 characters per token for English."""
    return max(0, (len(text) + 3) // 4)


def estimate_cost_for_call(
    model_id: str,
    messages: list[Any],
    max_output_tokens: int | None = 1024,
    pricing_override: Pricing | None = None,
    pricing_resolver: Callable[[str], tuple[float, float]] | None = None,
) -> float:
    """Estimate cost in USD for a single LLM call (best-effort).

    Counts input tokens from message contents via count_tokens; uses max_output_tokens
    for output. Actual cost may differ. Use for pre-call budget checks.

    Args:
        model_id: Model identifier (e.g. openai/gpt-4o-mini).
        messages: List of message-like objects with .content (str).
        max_output_tokens: Assumed max completion tokens (default 1024).
        pricing_override: Optional ModelPricing.
        pricing_resolver: Optional callable(model_id) -> (input_per_1m, output_per_1m).
    """
    out_tokens = 1024 if max_output_tokens is None else max_output_tokens
    input_tokens = 0
    for m in messages:
        content = getattr(m, "content", None) or ""
        if isinstance(content, str):
            input_tokens += count_tokens(content, model_id)
    usage = TokenUsage(
        input_tokens=input_tokens,
        output_tokens=out_tokens,
        total_tokens=input_tokens + out_tokens,
    )
    return calculate_cost(
        model_id,
        usage,
        pricing_override=pricing_override,
        pricing_resolver=pricing_resolver,
    )


__all__ = [
    "ModelPricing",
    "Pricing",
    "MODEL_PRICING",
    "calculate_cost",
    "count_tokens",
    "estimate_cost_for_call",
]
