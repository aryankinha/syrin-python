"""LiteLLM provider (fallback for any model)."""

from __future__ import annotations

import json

from syrin.enums import MessageRole
from syrin.exceptions import ProviderError
from syrin.tool import ToolSpec
from syrin.types import (
    Message,
    ModelConfig,
    ProviderResponse,
    TokenUsage,
    ToolCall,
)

from .base import Provider


def _message_to_litellm(msg: Message) -> dict[str, object]:
    if msg.role == MessageRole.TOOL:
        return {
            "role": "tool",
            "content": msg.content,
            "tool_call_id": msg.tool_call_id,
        }
    out: dict[str, object] = {"role": msg.role.value, "content": msg.content or ""}
    if msg.role == MessageRole.ASSISTANT and msg.tool_calls:
        out["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
            }
            for tc in msg.tool_calls
        ]
    return out


def _tools_to_litellm(tools: list[ToolSpec]) -> list[dict[str, object]]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.parameters_schema or {"type": "object", "properties": {}},
            },
        }
        for t in tools
    ]


class LiteLLMProvider(Provider):
    """Provider using LiteLLM for unified completion (supports many backends)."""

    async def complete(  # type: ignore[override]
        self,
        messages: list[Message],
        model: ModelConfig,
        tools: list[ToolSpec] | None = None,
        *,
        max_tokens: int = 1024,
        **kwargs: object,
    ) -> ProviderResponse:
        try:
            import litellm
        except ImportError as e:
            raise ProviderError(
                "LiteLLM provider requires the litellm package. "
                "Install with: uv pip install syrin[litellm]"
            ) from e

        api_messages = [_message_to_litellm(m) for m in messages]

        # Handle Google/Gemini models - add gemini/ prefix for litellm
        model_id = model.model_id
        if model.model_id.startswith("gemini-"):
            model_id = f"gemini/{model.model_id}"

        request_kwargs: dict[str, object] = {
            "model": model_id,
            "messages": api_messages,
            "max_tokens": max_tokens,
        }
        if model.api_key:
            request_kwargs["api_key"] = model.api_key
        if model.base_url:
            request_kwargs["api_base"] = model.base_url

        # Handle Google/Gemini models - force Google AI Studio provider
        if model_id.startswith("gemini/"):
            request_kwargs["custom_llm_provider"] = "gemini"

        request_kwargs.update(kwargs)
        if tools:
            request_kwargs["tools"] = _tools_to_litellm(tools)
            request_kwargs["tool_choice"] = request_kwargs.get("tool_choice", "auto")

        response = await litellm.acompletion(**request_kwargs)
        choice = response.choices[0] if response.choices else None
        if not choice:
            usage = getattr(response, "usage", None)
            return ProviderResponse(
                content="",
                tool_calls=[],
                token_usage=TokenUsage(
                    input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                    output_tokens=getattr(usage, "completion_tokens", 0) or 0,
                    total_tokens=getattr(usage, "total_tokens", 0) or 0,
                ),
                raw_response=response,
            )
        message = choice.message
        content = (getattr(message, "content", None) or "") or ""
        tool_calls_list: list[ToolCall] = []
        for tc in getattr(message, "tool_calls", []) or []:
            args = getattr(tc, "arguments", None) or "{}"
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            func = getattr(tc, "function", None)
            tool_calls_list.append(
                ToolCall(
                    id=getattr(tc, "id", "") or "",
                    name=getattr(func, "name", "") if func else "",
                    arguments=args,
                )
            )
        # When the model returns tool_calls with no text, /stream only did one completion and
        # did not run the tool loop, so the user would see nothing. Coerce to a short message.
        if (not content or not content.strip()) and tool_calls_list:
            if not tools or len(tools) == 0:
                names = ", ".join(tc.name for tc in tool_calls_list[:3])
                content = (
                    "Tools are currently disabled. The model attempted to use tool(s): "
                    f"{names}. Re-enable tools in the agent config to use them."
                )
            else:
                content = (
                    "The model chose to use a tool; this stream endpoint does not run tools. "
                    "Use POST /chat for full tool execution and a final reply."
                )

        usage = getattr(response, "usage", None)
        return ProviderResponse(
            content=content,
            tool_calls=tool_calls_list,
            token_usage=TokenUsage(
                input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                output_tokens=getattr(usage, "completion_tokens", 0) or 0,
                total_tokens=getattr(usage, "total_tokens", 0) or 0,
            ),
            raw_response=response,
        )
