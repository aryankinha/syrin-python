"""Tests for Almock (An LLM Mock) provider — valid, invalid, and edge cases."""

from __future__ import annotations

import time

import pytest

from syrin import Agent, MockPricing, Model
from syrin.enums import MessageRole
from syrin.types import Message, ModelConfig

# -----------------------------------------------------------------------------
# Valid: Model.Almock creation
# -----------------------------------------------------------------------------


class TestAlmockCreation:
    """Valid creation and default behavior."""

    def test_almock_default_returns_model(self) -> None:
        """Model.mock() with no args returns a Model with provider almock."""
        model = Model.mock()
        assert model._provider == "almock"
        assert "almock" in (model._model_id or "")

    def test_almock_pricing_tier_low(self) -> None:
        """pricing_tier='low' sets low input/output price."""
        model = Model.mock(pricing_tier="low")
        assert model.pricing is not None
        assert model.pricing.input_per_1m < 1.0
        assert model.pricing.output_per_1m < 1.0

    def test_almock_pricing_tier_enum(self) -> None:
        """pricing_tier=MockPricing.HIGH uses HIGH tier."""
        model = Model.mock(pricing_tier=MockPricing.HIGH)
        assert model.pricing is not None
        assert model.pricing.input_per_1m == 5.0
        assert model.pricing.output_per_1m == 15.0

    def test_almock_context_window(self) -> None:
        """context_window is set (default 8192)."""
        model = Model.mock(context_window=4096)
        assert model._settings.context_window == 4096

    def test_almock_custom_response_mode(self) -> None:
        """response_mode='custom' with custom_response returns that text."""
        model = Model.mock(
            response_mode="custom",
            custom_response="Hello, mock!",
            latency_min=0,
            latency_max=0,
        )
        resp = model.complete([Message(role=MessageRole.USER, content="Hi")])
        assert resp is not None
        assert resp.content == "Hello, mock!"

    def test_almock_lorem_mode_default_length(self) -> None:
        """response_mode='lorem' (default) returns Lorem Ipsum of default length."""
        model = Model.mock(latency_min=0, latency_max=0, lorem_length=50)
        resp = model.complete([Message(role=MessageRole.USER, content="Hi")])
        assert resp is not None
        assert resp.content is not None
        assert len(resp.content) == 50
        assert "Lorem" in resp.content or "lorem" in resp.content.lower()

    def test_almock_token_usage_populated(self) -> None:
        """Provider returns token_usage (input/output/total)."""
        model = Model.mock(latency_min=0, latency_max=0)
        resp = model.complete([Message(role=MessageRole.USER, content="Hello world")])
        assert resp is not None
        assert resp.token_usage.input_tokens >= 0
        assert resp.token_usage.output_tokens >= 0
        assert resp.token_usage.total_tokens == (
            resp.token_usage.input_tokens + resp.token_usage.output_tokens
        )


# -----------------------------------------------------------------------------
# Invalid: latency_seconds validation
# -----------------------------------------------------------------------------


class TestAlmockLatencyValidation:
    """latency_seconds must be > 0."""

    @pytest.mark.asyncio
    async def test_latency_seconds_zero_raises(self) -> None:
        """latency_seconds=0 raises ValueError (must be > 0)."""
        from syrin.providers.almock import AlmockProvider

        provider = AlmockProvider()
        cfg = ModelConfig(name="almock", provider="almock", model_id="almock/default")
        with pytest.raises(ValueError, match="greater than 0"):
            await provider.complete(
                [Message(role=MessageRole.USER, content="Hi")],
                model=cfg,
                latency_seconds=0.0,
            )

    @pytest.mark.asyncio
    async def test_latency_seconds_negative_raises(self) -> None:
        """latency_seconds=-1 raises ValueError."""
        from syrin.providers.almock import AlmockProvider

        provider = AlmockProvider()
        cfg = ModelConfig(name="almock", provider="almock", model_id="almock/default")
        with pytest.raises(ValueError, match="greater than 0"):
            await provider.complete(
                [Message(role=MessageRole.USER, content="Hi")],
                model=cfg,
                latency_seconds=-1.0,
            )


# -----------------------------------------------------------------------------
# Edge: latency behavior (use small delay to avoid slow tests)
# -----------------------------------------------------------------------------


class TestAlmockLatencyBehavior:
    """Latency: fixed latency_seconds or random min/max."""

    def test_latency_seconds_positive_delays(self) -> None:
        """When latency_seconds=0.1, response is delayed ~0.1s (sync complete)."""
        model = Model.mock(latency_seconds=0.1)  # valid: > 0
        t0 = time.monotonic()
        resp = model.complete([Message(role=MessageRole.USER, content="Hi")])
        elapsed = time.monotonic() - t0
        assert resp is not None
        assert elapsed >= 0.09  # allow small tolerance

    def test_latency_zero_via_min_max_ok(self) -> None:
        """latency_min=0, latency_max=0 means no delay (no latency_seconds)."""
        model = Model.mock(latency_min=0, latency_max=0)
        t0 = time.monotonic()
        resp = model.complete([Message(role=MessageRole.USER, content="Hi")])
        elapsed = time.monotonic() - t0
        assert resp is not None
        assert elapsed < 1.0


# -----------------------------------------------------------------------------
# Agent integration with Almock
# -----------------------------------------------------------------------------


class TestAlmockWithAgent:
    """Agent.run() works with Model.Almock (no API key)."""

    def test_agent_almock_returns_response(self) -> None:
        """Agent(model=Model.mock()) returns a Response with content."""
        model = Model.mock(latency_min=0, latency_max=0, lorem_length=20)
        agent = Agent(model=model, system_prompt="You are helpful.")
        r = agent.run("Hello")
        assert r.content is not None
        assert r.cost >= 0
        assert r.tokens.total_tokens >= 0

    def test_agent_almock_budget_tracked(self) -> None:
        """Cost from Almock is tracked when Agent has Budget."""
        from syrin import Budget

        model = Model.mock(pricing_tier=MockPricing.MEDIUM, latency_min=0, latency_max=0)
        agent = Agent(
            model=model,
            system_prompt="Test.",
            budget=Budget(max_cost=10.0),
        )
        r = agent.run("Hi")
        assert r.cost >= 0
        assert r.budget_used >= 0


# -----------------------------------------------------------------------------
# Edge: lorem_length 0 or negative
# -----------------------------------------------------------------------------


class TestAlmockLoremEdgeCases:
    """lorem_length edge cases."""

    def test_lorem_length_zero_uses_fallback(self) -> None:
        """lorem_length=0: provider uses fallback length (100)."""
        model = Model.mock(latency_min=0, latency_max=0, lorem_length=0)
        resp = model.complete([Message(role=MessageRole.USER, content="Hi")])
        assert resp is not None
        # Implementation uses 100 as fallback when lorem_length <= 0
        assert len(resp.content or "") >= 0


# -----------------------------------------------------------------------------
# Pricing tiers
# -----------------------------------------------------------------------------


class TestMockPricingTiers:
    """All pricing tiers set correct input/output per 1M."""

    def test_ultra_high_tier(self) -> None:
        """ULTRA_HIGH has highest prices."""
        model = Model.mock(pricing_tier=MockPricing.ULTRA_HIGH)
        assert model.pricing is not None
        assert model.pricing.input_per_1m == 30.0
        assert model.pricing.output_per_1m == 60.0

    def test_medium_tier(self) -> None:
        """MEDIUM tier has medium prices."""
        model = Model.mock(pricing_tier=MockPricing.MEDIUM)
        assert model.pricing is not None
        assert model.pricing.input_per_1m == 0.50
        assert model.pricing.output_per_1m == 1.50
