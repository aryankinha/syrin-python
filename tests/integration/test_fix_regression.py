"""Regression tests for fixes from FAILED_TESTS_REPORT and Manual_test_report.

Covers: model fallback when primary fails, response transformer at agent level,
Response.raw_response, and related API additions.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from syrin import Agent, Model
from syrin.model import Middleware
from syrin.types import Message, ProviderResponse, TokenUsage


def _mock_response(content: str = "ok") -> ProviderResponse:
    return ProviderResponse(
        content=content,
        tool_calls=[],
        token_usage=TokenUsage(input_tokens=5, output_tokens=10, total_tokens=15),
    )


class TestModelFallbackWhenPrimaryFails:
    """Model.with_fallback(): when primary fails, fallback is used."""

    def test_agent_with_model_fallback_uses_fallback_on_primary_error(self) -> None:
        """When primary model raises, agent uses fallback model."""
        primary = Model("anthropic/claude-3-5-sonnet")
        fallback = Model.Almock(latency_seconds=0.01, lorem_length=30)
        model = primary.with_fallback(fallback)
        agent = Agent(model=model, system_prompt="Hi")

        # Primary would fail (no API key), but fallback (Almock) should succeed
        r = agent.run("Hello")
        assert r.content is not None
        assert len(r.content) > 0

    def test_model_acomplete_fallback_chain(self) -> None:
        """Model.acomplete() tries fallbacks when primary raises."""
        primary = Model(provider="anthropic", model_id="anthropic/claude-3-5-sonnet")
        fallback = Model.Almock(latency_seconds=0.01, lorem_length=20)
        model = primary.with_fallback(fallback)

        import asyncio

        messages = [Message(role="user", content="Hi")]
        resp = asyncio.run(model.acomplete(messages))
        assert resp.content is not None
        assert len(resp.content) > 0


class TestResponseTransformerAtAgentLevel:
    """Model.with_middleware(): response transformer applied in agent.run()."""

    def test_agent_applies_response_transformer(self) -> None:
        """When model has response transformer, agent.run() returns transformed content."""
        transformed_content: list[str] = []

        class AppendTransformer(Middleware):
            def transform_request(self, messages, **kwargs):
                return messages, kwargs

            def transform_response(self, response: ProviderResponse) -> ProviderResponse:
                transformed_content.append(response.content or "")
                response.content = (response.content or "") + " [transformed]"
                return response

        model = Model.Almock(latency_seconds=0.01, lorem_length=20).with_middleware(
            AppendTransformer()
        )
        agent = Agent(model=model, system_prompt="Hi")

        r = agent.run("Hello")
        assert r.content is not None
        assert r.content.endswith(" [transformed]")
        assert len(transformed_content) == 1


class TestResponseRawResponse:
    """Response.raw_response attribute exists and is passed through."""

    def test_response_has_raw_response_attribute(self) -> None:
        """Response accepts and stores raw_response."""
        from syrin.response import Response

        r = Response(content="Hi", raw_response={"raw": "api_response"})
        assert hasattr(r, "raw_response")
        assert r.raw_response == {"raw": "api_response"}

    def test_agent_response_includes_raw_response_from_loop(self) -> None:
        """Agent response includes raw_response from loop when provider returns it."""
        model = Model.Almock(latency_seconds=0.01, lorem_length=20)
        agent = Agent(model=model, system_prompt="Hi")
        mock_resp = _mock_response(content="Hello")
        mock_resp.raw_response = {"almock": True}

        with patch.object(
            agent._provider,
            "complete",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            r = agent.run("Hi")
        assert hasattr(r, "raw_response")
        assert r.raw_response == {"almock": True}
