"""SecretCache — TTL-bounded in-memory cache for secrets."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class _CacheEntry:
    """Internal cache entry with value and expiry timestamp.

    Attributes:
        value: The cached secret string.
        expires_at: Unix timestamp (float) when this entry expires.
    """

    value: str
    expires_at: float


class SecretCache:
    """TTL-bounded secret cache.

    Stores secrets in memory with automatic expiry based on a time-to-live.
    Accessing an expired entry returns ``None`` and marks it as expired.

    Args:
        ttl_seconds: Time-to-live in seconds for cached entries.

    Example:
        >>> cache = SecretCache(ttl_seconds=60.0)
        >>> cache.set("api_key", "sk-secret")
        >>> assert cache.get("api_key") == "sk-secret"
    """

    def __init__(self, ttl_seconds: float) -> None:
        """Initialize SecretCache with a TTL.

        Args:
            ttl_seconds: How long entries live before expiring.
        """
        self._ttl = ttl_seconds
        self._store: dict[str, _CacheEntry] = {}

    def set(self, key: str, value: str) -> None:
        """Store a secret with the configured TTL.

        Args:
            key: Cache key.
            value: Secret value to cache.
        """
        self._store[key] = _CacheEntry(
            value=value,
            expires_at=time.monotonic() + self._ttl,
        )

    def get(self, key: str) -> str | None:
        """Retrieve a secret, returning None if absent or expired.

        Args:
            key: Cache key.

        Returns:
            The cached value, or None if key is missing or expired.
        """
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() >= entry.expires_at:
            return None
        return entry.value

    def is_expired(self, key: str) -> bool:
        """Check whether a cache entry has expired.

        Args:
            key: Cache key.

        Returns:
            True if the entry is expired or does not exist.
        """
        entry = self._store.get(key)
        if entry is None:
            return True
        return time.monotonic() >= entry.expires_at
