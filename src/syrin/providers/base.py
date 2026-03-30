"""Abstract provider interface for LLM completions."""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import warnings
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from typing import Any

from syrin.tool import ToolSpec
from syrin.types import Message, ModelConfig, ProviderResponse

_log = logging.getLogger(__name__)

warnings.filterwarnings("ignore", message=".*Event loop is closed.*")

# Shared thread pool for running async coroutines from a sync context
# when the calling thread already has a running event loop.
# One pool is reused to avoid per-call thread-creation overhead.
_THREAD_POOL = concurrent.futures.ThreadPoolExecutor(
    max_workers=8, thread_name_prefix="syrin-provider"
)


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
        """Run async coroutine from sync context.

        Uses asyncio.run() when no event loop is running (safe, fresh loop
        per call). When a running loop is detected — e.g., called from inside an
        async framework like FastAPI or Jupyter — falls back to a thread-pool
        worker with its own fresh loop so we never call run_until_complete() on
        an already-running loop.
        """
        try:
            asyncio.get_running_loop()
            running = True
        except RuntimeError:
            running = False

        def _run_in_fresh_loop() -> ProviderResponse | None:
            # always use a fresh event loop in a worker thread so we never
            # call run_until_complete() on an already-running loop AND we never
            # mutate the calling thread's global event loop state.
            new_loop = asyncio.new_event_loop()
            try:
                result: ProviderResponse | None = new_loop.run_until_complete(coro)  # type: ignore[arg-type]
                return result
            except asyncio.CancelledError:
                return None
            finally:
                new_loop.close()

        if running:
            # Running loop in calling thread — must offload to a worker thread.
            return _THREAD_POOL.submit(_run_in_fresh_loop).result()

        # No running loop — still use a thread so we never touch the global
        # event loop state (avoids breaking asyncio.get_event_loop() callers).
        return _THREAD_POOL.submit(_run_in_fresh_loop).result()

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
        """Synchronous wrapper for complete(). Safe to call from any context."""
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
