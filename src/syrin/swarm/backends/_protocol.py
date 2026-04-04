"""MemoryBusBackend Protocol — extensible backend interface."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from syrin.memory.config import MemoryEntry


@runtime_checkable
class MemoryBusBackend(Protocol):
    """Protocol for MemoryBus storage backends.

    Implement this protocol to add a custom backend (e.g. PocketBase, Redis).
    All methods are async for compatibility with both blocking I/O and native
    async storage systems.

    Example:
        class MyBackend:
            async def store(self, entry, agent_id, ttl): ...
            async def query(self, query, agent_id): ...
            async def clear_expired(self): ...
            async def all_entries(self): ...

        bus = MemoryBus(backend=MyBackend())
    """

    async def store(
        self,
        entry: MemoryEntry,
        agent_id: str,
        ttl: float | None,
    ) -> None:
        """Store a memory entry.

        Args:
            entry: The :class:`~syrin.memory.config.MemoryEntry` to persist.
            agent_id: ID of the publishing agent.
            ttl: Seconds until entry expires, or ``None`` for no expiry.
        """
        ...

    async def query(self, query: str, agent_id: str) -> list[MemoryEntry]:
        """Query entries matching the given search string.

        Args:
            query: Substring to match against entry content.  An empty string
                matches all entries.
            agent_id: ID of the reading agent (for future ACL use).

        Returns:
            List of matching :class:`~syrin.memory.config.MemoryEntry` objects.
        """
        ...

    async def clear_expired(self) -> list[str]:
        """Remove entries that have passed their TTL.

        Returns:
            List of entry IDs that were removed.
        """
        ...

    async def all_entries(
        self,
    ) -> list[tuple[MemoryEntry, str, float | None]]:
        """Return all stored entries with routing metadata.

        Returns:
            List of ``(entry, agent_id, expire_at)`` tuples where
            ``expire_at`` is an absolute UNIX timestamp or ``None``.
        """
        ...


__all__ = ["MemoryBusBackend"]
