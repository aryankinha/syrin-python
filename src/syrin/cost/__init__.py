"""Public cost package facade.

This package exposes Syrin's pricing tables, token counters, and cost-estimation
helpers. Import from ``syrin.cost`` when you need to estimate request cost,
count tokens, or access built-in model and media pricing data.
"""

from syrin.cost._core import (
    EMBEDDING_PRICING,
    IMAGE_PRICING,
    MODEL_PRICING,
    VIDEO_PRICING,
    VOICE_PRICING,
    ModelPricing,
    Pricing,
    _resolve_pricing,
    calculate_cost,
    calculate_embedding_cost,
    calculate_image_cost,
    calculate_video_cost,
    calculate_voice_cost,
    count_tokens,
    estimate_cost_for_call,
)

__all__ = [
    "EMBEDDING_PRICING",
    "IMAGE_PRICING",
    "ModelPricing",
    "VOICE_PRICING",
    "MODEL_PRICING",
    "Pricing",
    "VIDEO_PRICING",
    "calculate_cost",
    "calculate_embedding_cost",
    "calculate_image_cost",
    "calculate_video_cost",
    "calculate_voice_cost",
    "count_tokens",
    "estimate_cost_for_call",
    "_resolve_pricing",
]

_ = _resolve_pricing
