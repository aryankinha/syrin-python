"""QueueProtocol — message queue trigger with pluggable backend."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Protocol, runtime_checkable

from syrin.watch._trigger import TriggerEvent

_log = logging.getLogger(__name__)


@runtime_checkable
class QueueBackend(Protocol):
    """Protocol for pluggable queue backends (Redis, SQS, RabbitMQ, etc.).

    Implement this to add support for any message broker.

    Example::

        class SQSBackend:
            async def connect(self) -> None: ...
            async def disconnect(self) -> None: ...
            async def receive(self) -> AsyncIterator[tuple[str, object]]:
                async for message in poll_sqs():
                    yield message["Body"], message
            async def ack(self, message_id: object) -> None: ...
            async def nack(self, message_id: object) -> None: ...
    """

    async def connect(self) -> None:
        """Connect to the queue backend."""
        ...

    async def disconnect(self) -> None:
        """Disconnect from the queue backend."""
        ...

    async def receive(self) -> AsyncIterator[tuple[str, object]]:
        """Yield (message_text, message_handle) tuples.

        The message_handle is opaque — pass it back to ack()/nack().
        """
        ...
        yield ("", None)  # pragma: no cover

    async def ack(self, message_id: object) -> None:
        """Acknowledge successful processing."""
        ...

    async def nack(self, message_id: object) -> None:
        """Reject the message (put back on queue or dead-letter)."""
        ...


class QueueProtocol:
    """Message queue trigger source.

    Consumes messages from a queue backend and fires the agent for each one.
    Default backend is Redis (via ``redis-py`` with ``BLPOP``). Custom backends
    implement the ``QueueBackend`` protocol.

    Args:
        source: Connection URL (e.g. ``"redis://localhost:6379/0"``) or a custom
            ``QueueBackend`` instance.
        queue: Queue name (Redis list key, SQS queue name, etc.).
        concurrency: Max messages processed in parallel. Default: ``1``.
        ack_on_success: Acknowledge message after successful processing. Default: ``True``.
        nack_on_error: Reject message on error (send to dead-letter / retry queue). Default: ``True``.

    Example::

        from syrin.watch import QueueProtocol

        agent.watch(
            protocol=QueueProtocol(
                source="redis://localhost:6379/0",
                queue="agent_tasks",
                concurrency=3,
            )
        )
    """

    def __init__(
        self,
        source: str | QueueBackend = "",
        queue: str = "",
        concurrency: int = 1,
        ack_on_success: bool = True,
        nack_on_error: bool = True,
    ) -> None:
        self.source = source
        self.queue = queue
        self.concurrency = concurrency
        self.ack_on_success = ack_on_success
        self.nack_on_error = nack_on_error
        self._running = False
        self._backend: QueueBackend | None = None

    async def start(
        self,
        handler: Callable[[TriggerEvent], Awaitable[None]],
    ) -> None:
        """Start consuming from the queue. Blocks until ``stop()`` is called.

        Args:
            handler: Async function called for each message.
        """
        self._running = True
        backend = self._resolve_backend()
        self._backend = backend

        try:
            await backend.connect()
        except Exception as exc:
            _log.error(f"QueueProtocol failed to connect: {exc}")
            return

        semaphore = asyncio.Semaphore(self.concurrency)

        async def _process(text: str, handle: object) -> None:
            async with semaphore:
                event = TriggerEvent(
                    input=text,
                    source="queue",
                    metadata={"queue": self.queue},
                    trigger_id=str(uuid.uuid4()),
                )
                try:
                    await handler(event)
                    if self.ack_on_success:
                        await backend.ack(handle)
                except Exception as exc:
                    _log.error(f"QueueProtocol handler error: {exc}")
                    if self.nack_on_error:
                        await backend.nack(handle)

        tasks: set[asyncio.Task[None]] = set()
        try:
            async for text, handle in backend.receive():
                if not self._running:
                    break
                task = asyncio.ensure_future(_process(text, handle))
                tasks.add(task)
                task.add_done_callback(tasks.discard)
        except Exception as exc:
            _log.error(f"QueueProtocol receive error: {exc}")
        finally:
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            await backend.disconnect()

    async def stop(self) -> None:
        """Stop consuming from the queue."""
        self._running = False

    def _resolve_backend(self) -> QueueBackend:
        """Resolve the queue backend from source."""
        if isinstance(self.source, str):
            return _RedisBackend(self.source, self.queue)
        return self.source


class _RedisBackend:
    """Default Redis backend using BLPOP."""

    def __init__(self, url: str, queue: str) -> None:
        self._url = url
        self._queue = queue
        self._client: object = None

    async def connect(self) -> None:
        try:
            import redis.asyncio as aioredis

            self._client = aioredis.from_url(self._url)
        except ImportError as exc:
            raise ImportError(
                "redis is required for QueueProtocol with Redis. Install it with: pip install redis"
            ) from exc

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.aclose()  # type: ignore[attr-defined]

    async def receive(self) -> AsyncIterator[tuple[str, object]]:
        if self._client is None:
            return
        while True:
            result = await self._client.blpop(self._queue, timeout=1)  # type: ignore[attr-defined]
            if result is not None:
                _, raw = result
                text = raw.decode() if isinstance(raw, bytes) else str(raw)
                yield text, text

    async def ack(self, message_id: object) -> None:
        pass  # Redis BLPOP auto-removes on receipt

    async def nack(self, message_id: object) -> None:
        if self._client is not None and message_id is not None:
            await self._client.rpush(self._queue, message_id)  # type: ignore[attr-defined]
