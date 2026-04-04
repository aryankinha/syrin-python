"""RedisBusBackend — optional Redis/Valkey MemoryBus backend."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from syrin.memory.config import MemoryEntry

if TYPE_CHECKING:
    pass

_KEY_PREFIX = "syrin:membus:"
_INDEX_KEY = "syrin:membus:__index__"


class RedisBusBackend:
    """Redis/Valkey-backed MemoryBus backend for distributed swarms.

    Requires the ``redis`` package (``pip install redis[asyncio]``).

    All entries are stored as JSON strings under ``syrin:membus:<entry_id>`` keys
    with optional Redis-native TTL expiry.

    Args:
        url: Redis connection URL (e.g. ``"redis://localhost:6379"``).

    Install with:
        ``pip install syrin[valkey]`` or ``pip install redis[asyncio]``

    Example:
        backend = RedisBusBackend(url="redis://localhost:6379")
        bus = MemoryBus(backend=backend)
    """

    def __init__(self, url: str = "redis://localhost:6379") -> None:
        """Initialise RedisBusBackend.

        Args:
            url: Redis connection URL.
        """
        try:
            import redis.asyncio as aioredis  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ImportError(
                "RedisBusBackend requires 'redis[asyncio]'. Install with: pip install syrin[redis]"
            ) from exc

        self._redis = aioredis.from_url(url, decode_responses=True)
        self._url = url

    async def store(
        self,
        entry: MemoryEntry,
        agent_id: str,
        ttl: float | None,
    ) -> None:
        """Store *entry* in Redis.

        Args:
            entry: The :class:`~syrin.memory.config.MemoryEntry` to store.
            agent_id: Publishing agent identifier.
            ttl: Seconds until expiry, or ``None`` for no expiry.
        """
        import json

        key = f"{_KEY_PREFIX}{entry.id}"
        expire_at: float | None = (time.time() + ttl) if ttl is not None else None
        value = json.dumps(
            {
                "entry": entry.model_dump(mode="json"),
                "agent_id": agent_id,
                "expire_at": expire_at,
            }
        )
        if ttl is not None:
            await self._redis.setex(key, int(ttl) + 1, value)
        else:
            await self._redis.set(key, value)
        await self._redis.sadd(_INDEX_KEY, entry.id)

    async def query(self, query: str, agent_id: str) -> list[MemoryEntry]:
        """Return non-expired entries whose content contains *query*.

        Args:
            query: Substring filter.  Empty string matches all.
            agent_id: Reading agent identifier.

        Returns:
            Matching :class:`~syrin.memory.config.MemoryEntry` objects.
        """
        import json

        now = time.time()
        ids: set[str] = await self._redis.smembers(_INDEX_KEY)
        results: list[MemoryEntry] = []
        for entry_id in ids:
            raw = await self._redis.get(f"{_KEY_PREFIX}{entry_id}")
            if raw is None:
                continue
            data = json.loads(raw)
            expire_at: float | None = data.get("expire_at")
            if expire_at is not None and expire_at <= now:
                continue
            entry = MemoryEntry.model_validate(data["entry"])
            if query == "" or query in entry.content:
                results.append(entry)
        return results

    async def clear_expired(self) -> list[str]:
        """Remove entries whose TTL has elapsed (Redis-native TTL handles most cases).

        Returns:
            IDs of explicitly removed entries.
        """
        import json

        now = time.time()
        ids: set[str] = await self._redis.smembers(_INDEX_KEY)
        expired_ids: list[str] = []
        for entry_id in ids:
            key = f"{_KEY_PREFIX}{entry_id}"
            raw = await self._redis.get(key)
            if raw is None:
                # Already expired by Redis TTL
                await self._redis.srem(_INDEX_KEY, entry_id)
                expired_ids.append(entry_id)
                continue
            data = json.loads(raw)
            expire_at: float | None = data.get("expire_at")
            if expire_at is not None and expire_at <= now:
                await self._redis.delete(key)
                await self._redis.srem(_INDEX_KEY, entry_id)
                expired_ids.append(entry_id)
        return expired_ids

    async def all_entries(
        self,
    ) -> list[tuple[MemoryEntry, str, float | None]]:
        """Return all stored entries with routing metadata.

        Returns:
            List of ``(entry, agent_id, expire_at)`` tuples.
        """
        import json

        ids: set[str] = await self._redis.smembers(_INDEX_KEY)
        results: list[tuple[MemoryEntry, str, float | None]] = []
        for entry_id in ids:
            raw = await self._redis.get(f"{_KEY_PREFIX}{entry_id}")
            if raw is None:
                continue
            data = json.loads(raw)
            entry = MemoryEntry.model_validate(data["entry"])
            results.append((entry, data["agent_id"], data.get("expire_at")))
        return results


__all__ = ["RedisBusBackend"]
