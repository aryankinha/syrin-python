"""OpenAI chat completions provider."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any


@lru_cache(maxsize=32)
def _get_client(api_key: str, base_url: str) -> Any:
    """Get or create cached AsyncOpenAI client per (api_key, base_url)."""
    from openai import AsyncOpenAI

    return AsyncOpenAI(api_key=api_key or None, base_url=base_url or None)


def _get_client_for_config(api_key: str | None, base_url: str | None) -> Any:
    """Resolve client for possibly-None api_key/base_url. lru_cache requires hashable args."""
    return _get_client(api_key or "", base_url or "")


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


def _message_to_openai(msg: Message) -> dict[str, Any]:
    if msg.role == MessageRole.TOOL:
        return {
            "role": "tool",
            "tool_call_id": msg.tool_call_id or "",
            "content": msg.content,
        }
    out: dict[str, Any] = {"role": msg.role.value, "content": msg.content or ""}
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


def _tools_to_openai(tools: list[ToolSpec]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": {
                    "type": "object",
                    "properties": t.parameters_schema.get("properties", {}),
                    "required": t.parameters_schema.get("required", []),
                }
                if t.parameters_schema
                else {"type": "object", "properties": {}},
            },
        }
        for t in tools
    ]


def _parse_usage(usage: Any) -> TokenUsage:
    if usage is None:
        return TokenUsage()
    return TokenUsage(
        input_tokens=getattr(usage, "prompt_tokens", 0) or getattr(usage, "input_tokens", 0) or 0,
        output_tokens=getattr(usage, "completion_tokens", 0)
        or getattr(usage, "output_tokens", 0)
        or 0,
        total_tokens=getattr(usage, "total_tokens", 0) or 0,
    )


class OpenAIProvider(Provider):
    """Provider for OpenAI chat completions (and compatible APIs)."""

    async def complete(
        self,
        messages: list[Message],
        model: ModelConfig,
        tools: list[ToolSpec] | None = None,
        *,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> ProviderResponse:
        try:
            import importlib.util

            if importlib.util.find_spec("openai") is None:
                raise ImportError("openai package not found")
        except ImportError as e:
            raise ProviderError(
                "OpenAI provider requires the openai package. "
                "Install with: uv pip install syrin[openai]"
            ) from e

        api_key = model.api_key
        if not api_key:
            raise ProviderError(
                "API key required for OpenAI. Pass api_key when creating the Model: "
                "Model.OpenAI('gpt-4o', api_key='sk-...') or api_key=os.getenv('OPENAI_API_KEY')"
            )
        api_messages = [_message_to_openai(m) for m in messages]
        client = _get_client_for_config(api_key, model.base_url)
        request_kwargs: dict[str, Any] = {
            "model": model.model_id.split("/")[-1],  # Strip provider prefix
            "messages": api_messages,
            "max_tokens": max_tokens,
            **kwargs,
        }

        # Handle structured output
        if model.output is not None:
            from syrin.model.structured import StructuredOutput

            structured = StructuredOutput(model.output)
            schema = structured.schema
            # OpenAI requires specific format for structured output
            model_name = getattr(model.output, "__name__", "StructuredOutput")
            request_kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": model_name,
                    "schema": schema,
                    "strict": True,
                },
            }

        if tools:
            request_kwargs["tools"] = _tools_to_openai(tools)
            request_kwargs["tool_choice"] = request_kwargs.get("tool_choice", "auto")

        response = await client.chat.completions.create(**request_kwargs)
        choice = response.choices[0] if response.choices else None
        if not choice:
            return ProviderResponse(
                content="",
                tool_calls=[],
                token_usage=_parse_usage(response.usage),
                raw_response=response,
            )
        message = choice.message
        content = (message.content or "") or ""
        tool_calls_list: list[ToolCall] = []
        for tc in getattr(message, "tool_calls", []) or []:
            func = getattr(tc, "function", None)
            args = getattr(func, "arguments", None) or "{}"
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            tool_calls_list.append(
                ToolCall(
                    id=getattr(tc, "id", "") or "",
                    name=getattr(func, "name", "") or "",
                    arguments=args,
                )
            )
        # When the model returns tool_calls with no text, /stream only did one completion.
        # Coerce to a short message.
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
        return ProviderResponse(
            content=content,
            tool_calls=tool_calls_list,
            token_usage=_parse_usage(response.usage),
            raw_response=response,
        )
