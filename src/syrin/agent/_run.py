"""Run orchestration and response building for Agent.

Single responsibility: run the loop (via AgentRunContext), handle guardrails,
checkpoints, and build Response from LoopResult. Agent delegates here from
response()/arun() so that agent/__init__.py stays focused on config and identity.
"""

from __future__ import annotations

from typing import Any, cast

from syrin.enums import GuardrailStage, StopReason
from syrin.loop import LoopResult
from syrin.response import Response
from syrin.types import TokenUsage


async def run_agent_loop_async(agent: Any, user_input: str) -> Response[str]:
    """Run the configured loop with full observability and build Response.

    Performs: input guardrails → loop.run(ctx, user_input) → checkpoint →
    output guardrails → build_output → populate report → return Response.
    """
    from syrin.observability import SemanticAttributes, SpanKind

    with agent._tracer.span(
        f"{agent._agent_name}.response",
        kind=SpanKind.AGENT,
        attributes={
            SemanticAttributes.AGENT_NAME: agent._agent_name,
            SemanticAttributes.AGENT_CLASS: agent.__class__.__name__,
            "input": user_input if not agent._debug else user_input[:1000],
            SemanticAttributes.LLM_MODEL: agent._model_config.model_id,
            SemanticAttributes.LLM_PROVIDER: agent._model_config.provider,
        },
    ) as agent_span:
        # Input guardrails check
        input_guardrail = agent._run_guardrails(user_input, GuardrailStage.INPUT)
        if not input_guardrail.passed:
            return cast(
                Response[str],
                agent._with_context_on_response(
                    _guardrail_response(
                        agent,
                        0.0,
                        0.0,
                        TokenUsage(input_tokens=0, output_tokens=0, total_tokens=0),
                        [],
                    ),
                ),
            )

        result = await agent._loop.run(agent.run_context, user_input)

        # Auto-checkpoint after step completion
        agent._maybe_checkpoint("step")

        tokens = _tokens_from_result(result)
        agent_span.set_attribute(SemanticAttributes.LLM_TOKENS_TOTAL, tokens.total_tokens)
        agent_span.set_attribute("cost.usd", result.cost_usd)

        if agent._budget is not None:
            agent_span.set_attribute("budget.remaining", agent._budget.remaining)
            agent_span.set_attribute("budget.spent", agent._budget._spent)

        tool_calls_list = _tool_calls_from_result(result)
        if result.tool_calls:
            agent._maybe_checkpoint("tool")

        # Output guardrails check (only if no tool calls)
        if not result.tool_calls:
            output_guardrail = agent._run_guardrails(result.content or "", GuardrailStage.OUTPUT)
            if not output_guardrail.passed:
                agent._last_iteration = result.iterations
                return cast(
                    Response[str],
                    agent._with_context_on_response(
                        _guardrail_response(
                            agent,
                            result.cost_usd,
                            result.latency_ms / 1000,
                            tokens,
                            tool_calls_list,
                        ),
                    ),
                )

        # Build structured output with validation
        structured = agent._build_output(
            result.content,
            validation_retries=agent._validation_retries,
            validation_context=agent._validation_context,
            validator=getattr(agent, "_output_validator", None),
        )

        # Populate report with final data
        agent._run_report.budget_remaining = agent._budget.remaining if agent._budget else None
        agent._run_report.budget_used = agent._budget._spent if agent._budget else 0.0
        agent._run_report.tokens.input_tokens = tokens.input_tokens
        agent._run_report.tokens.output_tokens = tokens.output_tokens
        agent._run_report.tokens.total_tokens = tokens.total_tokens
        agent._run_report.tokens.cost_usd = result.cost_usd

        agent._last_iteration = result.iterations

        return cast(
            Response[str],
            agent._with_context_on_response(
                _response_from_loop_result(agent, result, tokens, tool_calls_list, structured),
            ),
        )


def _tokens_from_result(result: LoopResult) -> TokenUsage:
    u = result.token_usage or {}
    return TokenUsage(
        input_tokens=u.get("input", 0),
        output_tokens=u.get("output", 0),
        total_tokens=u.get("total", 0),
    )


def _tool_calls_from_result(result: LoopResult) -> list[Any]:
    from syrin.types import ToolCall

    out: list[Any] = []
    for tc in result.tool_calls or []:
        out.append(
            ToolCall(
                id=tc.get("id", ""),
                name=tc.get("name", ""),
                arguments=tc.get("arguments", {}),
            )
        )
    return out


def _guardrail_response(
    agent: Any,
    cost_usd: float,
    duration_sec: float,
    tokens: TokenUsage,
    tool_calls: list[Any],
) -> Response[str]:
    from syrin.response import Response as ResponseClass

    return ResponseClass(
        content="",
        raw="",
        cost=cost_usd,
        tokens=tokens,
        model=agent._model_config.model_id,
        duration=duration_sec,
        trace=[],
        tool_calls=tool_calls,
        stop_reason=StopReason.GUARDRAIL,
        budget_remaining=agent._budget.remaining if agent._budget else None,
        budget_used=agent._budget._spent if agent._budget else 0.0,
        structured=None,
        report=agent._run_report,
    )


def _response_from_loop_result(
    agent: Any,
    result: LoopResult,
    tokens: TokenUsage,
    tool_calls_list: list[Any],
    structured: Any,
) -> Response[str]:
    from syrin.response import Response as ResponseClass

    stop_reason = (
        StopReason(result.stop_reason)
        if isinstance(result.stop_reason, str)
        else result.stop_reason
    )
    return ResponseClass(
        content=result.content,
        cost=result.cost_usd,
        tokens=tokens,
        model=agent._model_config.model_id,
        duration=result.latency_ms / 1000,
        tool_calls=tool_calls_list,
        stop_reason=stop_reason,
        budget_remaining=agent._budget.remaining if agent._budget else None,
        budget_used=agent._budget._spent if agent._budget else 0.0,
        iterations=result.iterations,
        structured=structured,
        report=agent._run_report,
    )
