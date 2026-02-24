"""Tests for cost calculator (cost.py)."""

from __future__ import annotations

import pytest

from syrin.cost import (
    MODEL_PRICING,
    Pricing,
    calculate_cost,
    count_tokens,
)
from syrin.types import TokenUsage


def test_calculate_cost_known_model() -> None:
    usage = TokenUsage(input_tokens=1_000_000, output_tokens=500_000)
    cost = calculate_cost("anthropic/claude-3-7-sonnet-latest", usage)
    assert cost > 0
    # 1M input @ 3, 0.5M output @ 15 -> 3 + 7.5 = 10.5
    assert 10 <= cost <= 11


def test_calculate_cost_with_override() -> None:
    usage = TokenUsage(input_tokens=1_000_000, output_tokens=0)
    cost = calculate_cost("unknown/model", usage, pricing_override=Pricing(1.0, 2.0))
    assert cost == 1.0


def test_calculate_cost_with_pricing_resolver() -> None:
    """When pricing_resolver is provided, it is used instead of built-in or override."""
    usage = TokenUsage(input_tokens=1_000_000, output_tokens=500_000)

    def resolver(model_id: str) -> tuple[float, float]:
        assert model_id == "custom/model"
        return (2.0, 4.0)

    cost = calculate_cost("custom/model", usage, pricing_resolver=resolver)
    assert cost == 4.0  # 1M*2 + 0.5M*4 = 2 + 2


def test_calculate_cost_pricing_resolver_takes_precedence_over_override() -> None:
    """pricing_resolver overrides pricing_override when both are given."""
    usage = TokenUsage(input_tokens=1_000_000, output_tokens=0)

    def resolver(_: str) -> tuple[float, float]:
        return (10.0, 20.0)

    cost = calculate_cost(
        "any/model",
        usage,
        pricing_override=Pricing(1.0, 2.0),
        pricing_resolver=resolver,
    )
    assert cost == 10.0


def test_calculate_cost_pricing_resolver_none_uses_builtin() -> None:
    """When pricing_resolver is None, built-in MODEL_PRICING is used."""
    usage = TokenUsage(input_tokens=1_000_000, output_tokens=0)
    cost = calculate_cost("gpt-4o-mini", usage, pricing_resolver=None)
    assert cost == 0.15


def test_calculate_cost_pricing_resolver_raises_propagates() -> None:
    """When pricing_resolver raises, the exception propagates."""

    def resolver(_: str) -> tuple[float, float]:
        raise ValueError("custom resolver error")

    with pytest.raises(ValueError, match="custom resolver error"):
        calculate_cost(
            "any/model",
            TokenUsage(input_tokens=100, output_tokens=100),
            pricing_resolver=resolver,
        )


def test_calculate_cost_unknown_model_zero() -> None:
    usage = TokenUsage(input_tokens=1000, output_tokens=500)
    cost = calculate_cost("unknown/foo", usage)
    assert cost == 0.0


def test_pricing() -> None:
    p = Pricing(input_per_1m=0.5, output_per_1m=1.5)
    assert p.input_per_1m == 0.5
    assert p.output_per_1m == 1.5


def test_count_tokens_empty() -> None:
    assert count_tokens("", "gpt-4") == 0


def test_count_tokens_estimate_fallback() -> None:
    n = count_tokens("hello world", "unknown/model")
    assert n >= 1


def test_model_pricing_has_entries() -> None:
    assert len(MODEL_PRICING) >= 5
    assert "claude-3-7-sonnet" in MODEL_PRICING or any("claude" in k for k in MODEL_PRICING)


# =============================================================================
# COST EDGE CASES - TRY TO BREAK FUNCTIONALITY
# =============================================================================


def test_calculate_cost_zero_usage() -> None:
    """Zero tokens should return zero cost."""
    usage = TokenUsage(input_tokens=0, output_tokens=0, total_tokens=0)
    cost = calculate_cost("gpt-4o-mini", usage)
    assert cost == 0.0


def test_calculate_cost_very_small_usage() -> None:
    """Very small token usage should return small cost."""
    usage = TokenUsage(input_tokens=1, output_tokens=1, total_tokens=2)
    cost = calculate_cost("gpt-4o-mini", usage)
    assert cost > 0


def test_calculate_cost_very_large_usage() -> None:
    """Very large token usage should calculate correctly."""
    usage = TokenUsage(
        input_tokens=10_000_000,
        output_tokens=10_000_000,
        total_tokens=20_000_000,
    )
    cost = calculate_cost("gpt-4o-mini", usage)
    # 10M * 0.15 + 10M * 0.60 = 1.5 + 6.0 = 7.5
    assert cost == 7.5


def test_pricing_boundary_values() -> None:
    """Pricing with zero values."""
    p = Pricing(input_per_1m=0.0, output_per_1m=0.0)
    assert p.input_per_1m == 0.0
    assert p.output_per_1m == 0.0


def test_pricing_with_very_high_values() -> None:
    """Pricing with very high values."""
    p = Pricing(input_per_1m=1_000_000.0, output_per_1m=1_000_000.0)
    assert p.input_per_1m == 1_000_000.0


def test_count_tokens_very_long_string() -> None:
    """Very long strings should be tokenizable."""
    long_text = "hello " * 10000
    tokens = count_tokens(long_text, "gpt-4o")
    assert tokens > 10000


def test_count_tokens_unicode() -> None:
    """Unicode characters should be handled."""
    tokens = count_tokens("Hello 🌍 你好 🔥", "gpt-4o")
    assert tokens > 0


def test_count_tokens_special_characters() -> None:
    """Special characters should be handled."""
    tokens = count_tokens("!@#$%^&*()\n\t\r", "gpt-4o")
    assert tokens > 0


def test_model_pricing_prefix_matching() -> None:
    """Test pricing prefix matching works correctly."""
    usage = TokenUsage(input_tokens=1_000_000, output_tokens=0)
    # gpt-4o-mini is more specific than gpt-4o
    cost = calculate_cost("gpt-4o-mini", usage)
    assert cost == 0.15  # gpt-4o-mini pricing


def test_calculate_cost_with_pricing_override_unknown_model() -> None:
    """Pricing override should work for unknown models."""
    usage = TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000)
    cost = calculate_cost(
        "completely-unknown-model-12345",
        usage,
        pricing_override=Pricing(input_per_1m=10.0, output_per_1m=20.0),
    )
    assert cost == 30.0


def test_model_pricing_all_major_providers() -> None:
    """Verify pricing exists for major providers."""
    # Should have OpenAI
    assert any("gpt" in k for k in MODEL_PRICING)
    # Should have Anthropic
    assert any("claude" in k for k in MODEL_PRICING)
    # Should have Google
    assert any("gemini" in k for k in MODEL_PRICING)
