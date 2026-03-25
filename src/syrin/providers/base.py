"""Abstract provider interface for LLM completions."""

from __future__ import annotations

import asyncio
import logging
import warnings
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from typing import Any

from syrin.tool import ToolSpec
from syrin.types import Message, ModelConfig, ProviderResponse

_log = logging.getLogger(__name__)

warnings.filterwarnings("ignore", message=".*Event loop is closed.*")


def _get_event_loop() -> asyncio.AbstractEventLoop:
    """Get event loop for sync wrappers. Uses shared loop manager (no set_event_loop)."""
    from syrin._loop import get_loop

    return get_loop()


class Provider(ABC):
    """Abstract base for LLM providers. Implement complete(); stream() defaults to one chunk.

    Built-in providers: OpenAIProvider, AnthropicProvider, LiteLLMProvider, etc.
    To add a new LLM: subclass Provider, implement complete(), optionally override stream().

    Methods:
        complete: Async completion. Required. Returns ProviderResponse.
        complete_sync: Sync wrapper. Uses run_until_complete.
        stream: Async iterator of chunks. Default: yields single full response.
        stream_sync: Sync streaming. Default: yields single full response.
    """

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        model: ModelConfig,
        tools: list[ToolSpec] | None = None,
        **kwargs: object,
    ) -> ProviderResponse:
        """Run a completion. Required. Returns content, tool_calls, token_usage.

        Args:
            messages: Conversation messages (system, user, assistant, tool).
            model: ModelConfig with model_id, api_key, base_url.
            tools: Optional tool specs for function calling.
            **kwargs: Provider-specific (temperature, max_tokens, etc.).

        Returns:
            ProviderResponse with content, tool_calls, token_usage.
        """
        ...

    def _run_async(self, coro: object) -> ProviderResponse | None:
        """Run async coroutine using a persistent event loop."""
        loop = _get_event_loop()
        try:
            result: ProviderResponse | None = loop.run_until_complete(coro)  # type: ignore[arg-type]
            return result
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                from syrin.exceptions import SyrinError

                raise SyrinError(
                    "Event loop closed unexpectedly. This usually happens during shutdown. "
                    "If using syrin in an async framework, use await agent.arun() instead."
                ) from e
            raise
        except asyncio.CancelledError:
            return None

    @staticmethod
    def _handle_task_exception(task: asyncio.Task[Any]) -> None:  # type: ignore[explicit-any]
        """Suppress event loop closed errors in background tasks."""
        try:
            task.result()
        except RuntimeError as e:
            if "Event loop is closed" not in str(e):
                _log.debug("Background task error (non-fatal): %s", e)
        except asyncio.CancelledError:
            pass

    def complete_sync(
        self,
        messages: list[Message],
        model: ModelConfig,
        tools: list[ToolSpec] | None = None,
        **kwargs: object,
    ) -> ProviderResponse | None:
        """Synchronous wrapper. Uses run_until_complete(complete(...))."""
        return self._run_async(self.complete(messages=messages, model=model, tools=tools, **kwargs))

    async def stream(
        self,
        messages: list[Message],
        model: ModelConfig,
        tools: list[ToolSpec] | None = None,
        **kwargs: object,
    ) -> AsyncIterator[ProviderResponse]:
        """Stream response chunks. Default: yields one full response (from complete)."""
        response = await self.complete(messages, model, tools, **kwargs)
        yield response

    def stream_sync(
        self,
        messages: list[Message],
        model: ModelConfig,
        tools: list[ToolSpec] | None = None,
        **kwargs: object,
    ) -> Iterator[ProviderResponse]:
        """Synchronous streaming. Default: yields one full response."""
        response = self._run_async(self.complete(messages, model, tools, **kwargs))
        if response:
            yield response
