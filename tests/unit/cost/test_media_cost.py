"""Tests for image and video generation cost calculation.

TDD: tests for calculate_image_cost and calculate_video_cost.
"""

from __future__ import annotations

import pytest

from syrin.cost import (
    IMAGE_PRICING,
    VIDEO_PRICING,
    calculate_image_cost,
    calculate_video_cost,
)

# =============================================================================
# VALID CASES
# =============================================================================


def test_calculate_image_cost_known_model_single_image() -> None:
    """Known model, 1 image returns per-image cost."""
    cost = calculate_image_cost("dall-e-3", number_of_images=1)
    assert cost > 0
    assert cost == round(cost, 6)


def test_calculate_image_cost_multiple_images() -> None:
    """Multiple images scale linearly."""
    c1 = calculate_image_cost("imagen-4.0-generate-001", number_of_images=1)
    c3 = calculate_image_cost("imagen-4.0-generate-001", number_of_images=3)
    assert c3 == round(c3, 6)
    assert c3 == pytest.approx(c1 * 3, rel=1e-5)


def test_calculate_image_cost_model_with_provider_prefix() -> None:
    """Provider prefix in model_id is stripped for lookup."""
    cost = calculate_image_cost("openai/dall-e-3", number_of_images=1)
    assert cost > 0


def test_calculate_video_cost_known_model() -> None:
    """Known video model returns cost for default duration."""
    cost = calculate_video_cost("veo-2.0-generate-001")
    assert cost > 0
    assert cost == round(cost, 6)


def test_calculate_video_cost_custom_duration() -> None:
    """Video cost scales with duration in seconds."""
    c5 = calculate_video_cost("veo-2.0-generate-001", duration_seconds=5.0)
    c10 = calculate_video_cost("veo-2.0-generate-001", duration_seconds=10.0)
    assert c10 == pytest.approx(c5 * 2, rel=1e-5)


def test_image_pricing_has_entries() -> None:
    """IMAGE_PRICING contains expected models."""
    assert "dall-e-3" in IMAGE_PRICING
    assert "imagen-4.0-generate-001" in IMAGE_PRICING or any("imagen" in k for k in IMAGE_PRICING)


def test_video_pricing_has_entries() -> None:
    """VIDEO_PRICING contains expected models."""
    assert "veo-2.0-generate-001" in VIDEO_PRICING or any("veo" in k for k in VIDEO_PRICING)


# =============================================================================
# EDGE CASES - INVALID / BOUNDARY
# =============================================================================


def test_calculate_image_cost_unknown_model_returns_zero() -> None:
    """Unknown model returns 0.0 (no pricing)."""
    cost = calculate_image_cost("unknown-image-model-xyz", number_of_images=1)
    assert cost == 0.0


def test_calculate_image_cost_zero_images_returns_zero() -> None:
    """Zero images returns 0 cost."""
    cost = calculate_image_cost("dall-e-3", number_of_images=0)
    assert cost == 0.0


def test_calculate_image_cost_negative_images_returns_zero() -> None:
    """Negative number of images is treated as 0 (defensive)."""
    cost = calculate_image_cost("dall-e-3", number_of_images=-1)
    assert cost == 0.0


def test_calculate_video_cost_unknown_model_returns_zero() -> None:
    """Unknown video model returns 0.0."""
    cost = calculate_video_cost("unknown-video-model")
    assert cost == 0.0


def test_calculate_video_cost_zero_duration_returns_zero() -> None:
    """Zero duration returns 0 cost."""
    cost = calculate_video_cost("veo-2.0-generate-001", duration_seconds=0.0)
    assert cost == 0.0


def test_calculate_video_cost_negative_duration_returns_zero() -> None:
    """Negative duration is treated as 0 (defensive)."""
    cost = calculate_video_cost("veo-2.0-generate-001", duration_seconds=-1.0)
    assert cost == 0.0


def test_calculate_image_cost_empty_model_returns_zero() -> None:
    """Empty model_id returns 0."""
    cost = calculate_image_cost("", number_of_images=1)
    assert cost == 0.0


def test_calculate_video_cost_empty_model_returns_zero() -> None:
    """Empty model_id for video returns 0."""
    cost = calculate_video_cost("")
    assert cost == 0.0


# =============================================================================
# EDGE CASES - TRY TO BREAK
# =============================================================================


def test_calculate_image_cost_very_large_number_of_images() -> None:
    """Large number of images scales correctly."""
    cost = calculate_image_cost("dall-e-3", number_of_images=1000)
    assert cost > 0
    assert cost == round(cost, 6)


def test_calculate_video_cost_very_long_duration() -> None:
    """Long video duration scales correctly."""
    cost = calculate_video_cost("veo-2.0-generate-001", duration_seconds=300.0)
    assert cost > 0
