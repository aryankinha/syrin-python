"""TriggerEvent dataclass and WatchProtocol Protocol."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class TriggerEvent:
    """Event fired by a watch protocol when a trigger arrives.

    Passed to ``agent.trigger()`` and all watch callbacks.

    Attributes:
        input: Message or payload to pass to ``agent.run()``.
        source: Protocol name (``"webhook"``, ``"cron"``, ``"queue"``).
        metadata: Raw payload, headers, timestamp, or other protocol-specific data.
        trigger_id: Unique identifier for this trigger instance.
    """

    input: str
    source: str
    metadata: dict[str, object] = field(default_factory=dict)
    trigger_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@runtime_checkable
class WatchProtocol(Protocol):
    """Protocol for watch trigger sources.

    Implement this to add any trigger source (webhooks, crons, queues, etc.).

    Example::

        class MyProtocol:
            async def start(self, handler: Callable[[TriggerEvent], Awaitable[None]]) -> None:
                while True:
                    event = await wait_for_event()
                    await handler(event)

            async def stop(self) -> None:
                ...
    """

    async def start(
        self,
        handler: Callable[[TriggerEvent], Awaitable[None]],
    ) -> None:
        """Start watching. Call handler on every trigger.

        Args:
            handler: Async function to call with each TriggerEvent.
        """
        ...

    async def stop(self) -> None:
        """Stop watching and clean up resources."""
        ...
