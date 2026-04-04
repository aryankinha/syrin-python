"""Anthropic Claude provider."""

from __future__ import annotations

import json
import threading
from typing import Any

_client_cache: dict[tuple[str, str], Any] = {}  # type: ignore[explicit-any]
_cache_lock = threading.Lock()


def _get_client(api_key: str | None, base_url: str | None = None) -> object:
    """Get or create cached AsyncAnthropic client per (api_key, base_url)."""
    import anthropic

    key = (api_key or "", base_url or "")
    with _cache_lock:
        if key not in _client_cache:
            kwargs: dict[str, object] = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            _client_cache[key] = anthropic.AsyncAnthropic(**kwargs)
        return _client_cache[key]


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


def _message_to_anthropic(msg: Message) -> dict[str, object]:
    role = msg.role
    if role == MessageRole.SYSTEM:
        return {"role": "user", "content": f"[System: {msg.content}]"}
    if role == MessageRole.USER:
        return {"role": "user", "content": msg.content}
    if role == MessageRole.ASSISTANT:
        if msg.tool_calls:
            blocks: list[dict[str, object]] = []
            if msg.content:
                blocks.append({"type": "text", "text": msg.content})
            for tc in msg.tool_calls:
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    }
                )
            return {"role": "assistant", "content": blocks}
        return {"role": "assistant", "content": msg.content}
    if role == MessageRole.TOOL:
        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": msg.tool_call_id or "",
                    "content": msg.content,
                }
            ],
        }
    return {"role": "user", "content": msg.content}


def _tools_to_anthropic(tools: list[ToolSpec]) -> list[dict[str, object]]:
    return [
        {
            "name": t.name,
            "description": t.description or "",
            "input_schema": t.parameters_schema or {"type": "object", "properties": {}},
        }
        for t in tools
    ]


def _parse_usage(usage: object) -> TokenUsage:
    if usage is None:
        return TokenUsage()
    return TokenUsage(
        input_tokens=getattr(usage, "input_tokens", 0) or 0,
        output_tokens=getattr(usage, "output_tokens", 0) or 0,
        total_tokens=getattr(usage, "input_tokens", 0) + getattr(usage, "output_tokens", 0),
    )


def _content_to_text_and_tool_calls(content: object) -> tuple[str, list[ToolCall]]:
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    if not content:
        return "", []
    for block in content:  # type: ignore[attr-defined]
        if getattr(block, "type", None) == "text":
            text_parts.append(getattr(block, "text", "") or "")
        elif getattr(block, "type", None) == "tool_use":
            args = getattr(block, "input", None)
            if isinstance(args, str):
                try:
                    args = json.loads(args) if args else {}
                except json.JSONDecodeError:
                    args = {}
            elif not isinstance(args, dict):
                args = {}
            tool_calls.append(
                ToolCall(
                    id=getattr(block, "id", "") or "",
                    name=getattr(block, "name", "") or "",
                    arguments=args,
                )
            )
    return "\n".join(text_parts), tool_calls


class AnthropicProvider(Provider):
    """Provider for Anthropic Claude via the anthropic SDK."""

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
            import importlib.util

            if importlib.util.find_spec("anthropic") is None:
                raise ImportError("anthropic package not found")
        except ImportError as e:
            raise ProviderError(
                "Anthropic provider requires the anthropic package. "
                "Install with: uv pip install syrin[anthropic]"
            ) from e

        system_list: list[Message] = [m for m in messages if m.role == MessageRole.SYSTEM]
        rest = [m for m in messages if m.role != MessageRole.SYSTEM]
        system_prompt = (
            "\n".join(
                (m.content if isinstance(m.content, str) else str(m.content)) for m in system_list
            )
            if system_list
            else ""
        )
        api_messages = [_message_to_anthropic(m) for m in rest]

        api_key = model.api_key
        if not api_key:
            raise ProviderError(
                "API key required for Anthropic. Pass api_key when creating the Model: "
                "Model.Anthropic('claude-sonnet', api_key='sk-ant-...') or api_key=os.getenv('ANTHROPIC_API_KEY')"
            )
        client = _get_client(api_key, model.base_url)

        # Anthropic API expects model name without "anthropic/" prefix
        api_model = (
            model.model_id.removeprefix("anthropic/")
            if model.model_id.startswith("anthropic/")
            else model.model_id
        )
        request_kwargs: dict[str, object] = {
            "model": api_model,
            "max_tokens": max_tokens,
            "messages": api_messages,
            **kwargs,
        }
        if system_prompt:
            request_kwargs["system"] = system_prompt
        if tools:
            request_kwargs["tools"] = _tools_to_anthropic(tools)

        response = await client.messages.create(**request_kwargs)  # type: ignore[attr-defined]
        usage = _parse_usage(getattr(response, "usage", None))
        content = getattr(response, "content", [])
        text, tool_calls = _content_to_text_and_tool_calls(content)
        return ProviderResponse(
            content=text,
            tool_calls=tool_calls,
            token_usage=usage,
            raw_response=response,
        )
