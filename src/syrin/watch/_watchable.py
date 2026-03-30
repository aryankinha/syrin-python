"""Watchable mixin — adds watch(), trigger(), and watch_handler() to any class."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from syrin.watch._trigger import TriggerEvent, WatchProtocol

if TYPE_CHECKING:
    from syrin.response import Response


class Watchable:
    """Mixin that adds event-driven trigger support to Agent, Pipeline, etc.

    Any class that inherits from ``Watchable`` gains:

    - ``watch()`` — register one or more ``WatchProtocol`` instances
    - ``trigger()`` — fire a one-shot trigger and await the result
    - ``watch_handler()`` — get the internal dispatch function for mounting in your own framework

    ``Agent``, ``Pipeline``, and ``DynamicPipeline`` all inherit ``Watchable``.

    Example::

        from syrin import Agent, Model
        from syrin.watch import CronProtocol

        agent = Agent(model=Model.OpenAI("gpt-4o-mini", api_key="..."))
        agent.watch(protocol=CronProtocol(schedule="0 * * * *", input="Run hourly report"))
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._watch_protocols: list[WatchProtocol] = []
        self._watch_concurrency: int = 1
        self._watch_timeout: float | None = None
        self._watch_on_trigger: Callable[[TriggerEvent], None] | None = None
        self._watch_on_result: Callable[[TriggerEvent, object], None] | None = None
        self._watch_on_error: Callable[[TriggerEvent, Exception], None] | None = None
        self._watch_semaphore: asyncio.Semaphore | None = None

    def watch(
        self,
        protocol: WatchProtocol | None = None,
        *,
        protocols: list[WatchProtocol] | None = None,
        concurrency: int = 1,
        timeout: float | None = None,
        on_trigger: Callable[[TriggerEvent], None] | None = None,
        on_result: Callable[[TriggerEvent, object], None] | None = None,
        on_error: Callable[[TriggerEvent, Exception], None] | None = None,
    ) -> None:
        """Register one or more watch protocols.

        ``protocol=`` and ``protocols=`` are mutually exclusive — passing both raises
        ``ValueError``.

        Args:
            protocol: Single ``WatchProtocol`` instance to register.
            protocols: List of ``WatchProtocol`` instances (mutually exclusive with ``protocol=``).
            concurrency: Max number of triggers processed simultaneously. Default: 1.
            timeout: Per-trigger timeout in seconds. ``None`` means no limit. Default: ``None``.
            on_trigger: Callback called before ``agent.run()`` for each trigger.
            on_result: Callback called after successful ``agent.run()``.
            on_error: Callback called when ``agent.run()`` raises.

        Raises:
            ValueError: If both ``protocol=`` and ``protocols=`` are provided.

        Example::

            agent.watch(
                protocol=WebhookProtocol(path="/trigger", port=8080),
                concurrency=5,
                timeout=60.0,
                on_error=lambda e, ex: logger.error(f"{e.trigger_id}: {ex}"),
            )
        """
        if protocol is not None and protocols is not None:
            raise ValueError(
                "watch() arguments 'protocol' and 'protocols' are mutually exclusive — "
                "pass one or the other, not both."
            )

        if protocol is not None:
            self._watch_protocols.append(protocol)
        elif protocols is not None:
            self._watch_protocols.extend(protocols)

        self._watch_concurrency = concurrency
        self._watch_timeout = timeout
        self._watch_on_trigger = on_trigger
        self._watch_on_result = on_result
        self._watch_on_error = on_error

    async def trigger(
        self,
        input: str,  # noqa: A002
        source: str = "manual",
        metadata: dict[str, object] | None = None,
    ) -> Response[str]:
        """Fire a one-shot trigger and return the response.

        Runs ``agent.run(input)`` and returns the ``Response``. Respects all agent
        config (budget, guardrails, memory, output type). No protocol needed — use
        this from your own routes, scripts, or test code.

        Args:
            input: Message to pass to ``agent.run()``.
            source: Label for the trigger source (e.g. ``"my-webhook"``). Default: ``"manual"``.
            metadata: Arbitrary metadata dict. Default: ``{}``.

        Returns:
            Response from ``agent.run()``.

        Example::

            result = await agent.trigger(input="Run the report", source="api")
            print(result.content)
        """
        event = TriggerEvent(
            input=input,
            source=source,
            metadata=metadata or {},
        )
        handler = self.watch_handler()
        return await handler(event)  # type: ignore[return-value]

    def watch_handler(
        self,
        concurrency: int | None = None,
        timeout: float | None = None,
        on_result: Callable[[TriggerEvent, object], None] | None = None,
        on_error: Callable[[TriggerEvent, Exception], None] | None = None,
    ) -> Callable[[TriggerEvent], Awaitable[object]]:
        """Return the internal dispatch function for mounting in your own framework.

        The returned callable accepts a ``TriggerEvent`` and runs ``agent.run()``
        with concurrency management, timeout enforcement, and optional callbacks.
        Use this when you own the HTTP layer and just want Syrin's dispatch logic.

        Args:
            concurrency: Override concurrency limit. Uses ``watch()`` setting if ``None``.
            timeout: Override per-trigger timeout. Uses ``watch()`` setting if ``None``.
            on_result: Override result callback.
            on_error: Override error callback.

        Returns:
            Async callable: ``(TriggerEvent) -> Awaitable[Response]``.

        Example::

            handler = agent.watch_handler(concurrency=10, timeout=30.0)

            @app.post("/webhook")
            async def webhook(request: Request):
                event = TriggerEvent(input=payload["message"], source="my-app")
                return await handler(event)
        """
        _concurrency = concurrency if concurrency is not None else self._watch_concurrency
        _timeout = timeout if timeout is not None else self._watch_timeout
        _on_result = on_result or self._watch_on_result
        _on_error = on_error or self._watch_on_error

        semaphore = asyncio.Semaphore(_concurrency)

        async def _dispatch(event: TriggerEvent) -> object:
            async with semaphore:
                try:
                    _emit_watch_trigger(self, event)
                    coro = self._arun_for_trigger(event.input)
                    if _timeout is not None:
                        result = await asyncio.wait_for(coro, timeout=_timeout)
                    else:
                        result = await coro
                    if _on_result is not None:
                        _on_result(event, result)
                    return result
                except Exception as exc:
                    _emit_watch_error(self, event, exc)
                    if _on_error is not None:
                        _on_error(event, exc)
                    raise

        return _dispatch

    async def _arun_for_trigger(self, input: str) -> object:  # noqa: A002
        """Run the watchable object with the trigger input.

        Subclasses (Agent, Pipeline) override this to call their ``arun()`` / ``aprocess()``.
        Default implementation looks for ``arun()`` then ``run()`` (blocking fallback).
        """
        if hasattr(self, "arun"):
            return await self.arun(input)
        if hasattr(self, "run"):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.run, input)
        raise NotImplementedError(
            f"{type(self).__name__} must implement arun() or run() to use watch/trigger."
        )


def _emit_watch_trigger(obj: object, event: TriggerEvent) -> None:
    if not hasattr(obj, "_emit_event"):
        return
    try:
        from syrin.enums import Hook
        from syrin.events import EventContext

        ctx = EventContext(
            trigger_id=event.trigger_id,
            source=event.source,
            input=event.input[:200],
        )
        obj._emit_event(Hook.WATCH_TRIGGER, ctx)
    except Exception:
        pass


def _emit_watch_error(obj: object, event: TriggerEvent, exc: Exception) -> None:
    if not hasattr(obj, "_emit_event"):
        return
    try:
        from syrin.enums import Hook
        from syrin.events import EventContext

        ctx = EventContext(
            trigger_id=event.trigger_id,
            source=event.source,
            error=str(exc),
        )
        obj._emit_event(Hook.WATCH_ERROR, ctx)
    except Exception:
        pass
