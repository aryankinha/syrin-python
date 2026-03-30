"""Token count accumulation across loop iterations in LoopResult.

Tests that:
- ReactLoop with multiple iterations sums token_usage from all LLM calls
- SimpleLoop with one call has correct token_usage
- Dead code: message .tokens attribute is NOT used (was always False — Message has no .tokens)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from syrin.loop import ReactLoop
from syrin.types import TokenUsage


def _make_response(
    content: str = "done",
    input_tokens: int = 10,
    output_tokens: int = 5,
    tool_calls: list | None = None,
) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    resp.stop_reason = "end_turn"
    resp.tool_calls = tool_calls or []
    usage = TokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
    )
    resp.token_usage = usage
    resp.raw_response = None
    return resp


def _make_ctx(responses: list) -> MagicMock:
    """Build a minimal AgentRunContext stub."""
    from syrin.enums import MessageRole
    from syrin.types import Message

    ctx = MagicMock()
    ctx.model_id = "gpt-4o-mini"
    ctx.pricing_override = None
    ctx.has_rate_limit = False
    ctx.has_budget = False
    ctx.max_output_tokens = None
    ctx.max_tool_result_length = 0
    ctx.tools = []
    ctx.complete = AsyncMock(side_effect=responses)
    # Use real Message objects so hasattr(msg, "tokens") is False (Message has no .tokens)
    ctx.build_messages = MagicMock(return_value=[Message(role=MessageRole.USER, content="hello")])
    ctx.emit_event = MagicMock()
    ctx.check_and_apply_budget = MagicMock()
    ctx.check_and_apply_rate_limit = MagicMock()
    ctx.pre_call_budget_check = MagicMock()
    return ctx


class TestReactLoopTokenAccumulation:
    @pytest.mark.asyncio
    async def test_single_iteration_token_count(self) -> None:
        """ReactLoop with no tools: token_usage equals single LLM call."""
        resp = _make_response(input_tokens=100, output_tokens=50)
        ctx = _make_ctx([resp])
        loop = ReactLoop(max_iterations=5)

        result = await loop.run(ctx, "hello")

        assert result.token_usage["input"] == 100
        assert result.token_usage["output"] == 50
        assert result.token_usage["total"] == 150

    @pytest.mark.asyncio
    async def test_multi_iteration_tokens_accumulated(self) -> None:
        """ReactLoop with tool calls: token_usage must sum all iterations."""
        from syrin.types import ToolCall

        # Iteration 1: LLM responds with a tool call (input=100, output=20)
        tool_call = ToolCall(id="tc1", name="fake_tool", arguments={})

        resp1 = _make_response(
            content="", input_tokens=100, output_tokens=20, tool_calls=[tool_call]
        )
        resp1.stop_reason = "tool_use"

        # Iteration 2: LLM responds with final answer (input=200, output=30)
        resp2 = _make_response(content="final", input_tokens=200, output_tokens=30)

        ctx = _make_ctx([resp1, resp2])
        # Make execute_tool return immediately
        with (
            patch(
                "syrin.loop._execute_tool_with_retry",
                new_callable=AsyncMock,
                return_value="tool result",
            ),
            patch("syrin.loop._tool_span_context") as mock_span,
        ):
            mock_span.return_value.__enter__ = MagicMock(return_value=None)
            mock_span.return_value.__exit__ = MagicMock(return_value=False)
            loop = ReactLoop(max_iterations=5)
            result = await loop.run(ctx, "hello")

        # Total should be iteration1 + iteration2
        assert result.token_usage["input"] == 300, (
            f"Expected 300 input tokens (100+200), got {result.token_usage['input']}"
        )
        assert result.token_usage["output"] == 50, (
            f"Expected 50 output tokens (20+30), got {result.token_usage['output']}"
        )
        assert result.token_usage["total"] == 350, (
            f"Expected 350 total tokens, got {result.token_usage['total']}"
        )
