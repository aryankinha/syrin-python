"""OpenRouter provider — OpenAI-compatible API with header metadata parsing."""

from __future__ import annotations

import json
import threading
from typing import Any

_client_cache: dict[tuple[str, str], Any] = {}  # type: ignore[explicit-any]
_cache_lock = threading.Lock()

OPENROUTER_BASE = "https://openrouter.ai/api/v1"


def _get_openrouter_client(api_key: str | None, base_url: str | None) -> object:
    """Get or create cached AsyncOpenAI client for OpenRouter."""
    from openai import AsyncOpenAI

    url = base_url or OPENROUTER_BASE
    key = (api_key or "", url)
    with _cache_lock:
        if key not in _client_cache:
            _client_cache[key] = AsyncOpenAI(api_key=api_key, base_url=url)
        return _client_cache[key]


from syrin.exceptions import ProviderError
from syrin.tool import ToolSpec
from syrin.types import Message, ModelConfig, ProviderResponse, ToolCall

from .base import Provider
from .openai import (
    _message_to_openai,
    _parse_usage,
    _tools_to_openai,
)


def _extract_openrouter_metadata(response: object) -> dict[str, object]:
    """Extract OpenRouter metadata from response headers if available."""
    meta: dict[str, object] = {}
    raw = getattr(response, "_raw_response", None) or getattr(response, "headers", None)
    if raw is not None and hasattr(raw, "get"):
        cost_str = raw.get("x-openrouter-total-cost")
        if cost_str is not None:
            import contextlib

            with contextlib.suppress(ValueError, TypeError):
                meta["actual_cost"] = float(cost_str)
        model_used = raw.get("x-openrouter-model-used")
        if model_used is not None:
            meta["model_used"] = str(model_used)
        oid = raw.get("x-openrouter-id")
        if oid is not None:
            meta["openrouter_id"] = str(oid)
    return meta


class OpenRouterProvider(Provider):
    """Provider for OpenRouter — OpenAI-compatible with multi-model support.

    Uses the same API format as OpenAI. Parses x-openrouter-total-cost,
    x-openrouter-model-used, x-openrouter-id from response headers when available.
    """

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

            if importlib.util.find_spec("openai") is None:
                raise ImportError("openai package not found")
        except ImportError as e:
            raise ProviderError(
                "OpenRouter provider requires the openai package. "
                "Install with: uv pip install syrin[openai]"
            ) from e

        api_key = model.api_key
        if not api_key:
            raise ProviderError(
                "API key required for OpenRouter. Pass api_key when creating the Model: "
                "Model.OpenRouter('anthropic/claude-sonnet', api_key='sk-or-...')"
            )
        api_messages = [_message_to_openai(m) for m in messages]
        client = _get_openrouter_client(api_key, model.base_url)
        # OpenRouter expects full model ID (e.g. anthropic/claude-sonnet-4-5)
        model_id = model.model_id
        request_kwargs: dict[str, object] = {
            "model": model_id,
            "messages": api_messages,
            "max_tokens": max_tokens,
            **kwargs,
        }
        if model.output is not None:
            from syrin.model.structured import StructuredOutput

            structured = StructuredOutput(model.output)
            schema = structured.schema
            name = getattr(model.output, "__name__", "StructuredOutput")
            request_kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": name, "schema": schema, "strict": True},
            }
        if tools:
            request_kwargs["tools"] = _tools_to_openai(tools)
            request_kwargs["tool_choice"] = "auto"

        response = await client.chat.completions.create(**request_kwargs)  # type: ignore[attr-defined]
        meta = _extract_openrouter_metadata(response)
        choice = response.choices[0] if response.choices else None
        if not choice:
            return ProviderResponse(
                content="",
                tool_calls=[],
                token_usage=_parse_usage(response.usage),
                raw_response=response,
                metadata=meta,
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
        if (not content or not content.strip()) and tool_calls_list and not tools:
            names = ", ".join(tc.name for tc in tool_calls_list[:3])
            content = f"Tools disabled. Model attempted: {names}. Re-enable tools to use them."
        return ProviderResponse(
            content=content,
            tool_calls=tool_calls_list,
            token_usage=_parse_usage(response.usage),
            raw_response=response,
            metadata=meta,
        )
