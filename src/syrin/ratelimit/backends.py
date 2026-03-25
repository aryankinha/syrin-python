"""Rate limit persistence backends for multi-instance support.

Provides backends for storing rate limit state across multiple instances:
- MemoryBackend: In-memory (default, not persistent)
- SQLiteBackend: File-based persistent storage
- RedisBackend: Distributed storage for multi-instance deployments
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast


@dataclass
class RateLimitState:
    """Serialized rate limit state for persistence.

    Attributes:
        entries: List of rate limit entries (timestamp, tokens, etc.).
        last_updated: Last update timestamp.
    """

    entries: list[dict[str, object]] = field(default_factory=list)
    last_updated: float = field(default_factory=time.time)


class RateLimitBackend(ABC):
    """Abstract base class for rate limit backends.

    Implement save/load/delete/exists to persist rate limit state
    (in-memory, SQLite, Redis, etc.). Used by APIRateLimit backend.
    """

    @abstractmethod
    def save(self, key: str, state: RateLimitState) -> None:
        """Save rate limit state."""
        ...

    @abstractmethod
    def load(self, key: str) -> RateLimitState | None:
        """Load rate limit state."""
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete rate limit state."""
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if state exists."""
        ...


class MemoryRateLimitBackend(RateLimitBackend):
    """In-memory rate limit backend (not persistent)."""

    def __init__(self) -> None:
        self._storage: dict[str, RateLimitState] = {}

    def save(self, key: str, state: RateLimitState) -> None:
        self._storage[key] = state

    def load(self, key: str) -> RateLimitState | None:
        return self._storage.get(key)

    def delete(self, key: str) -> None:
        self._storage.pop(key, None)

    def exists(self, key: str) -> bool:
        return key in self._storage


class SQLiteRateLimitBackend(RateLimitBackend):
    """SQLite-based rate limit backend (persistent)."""

    def __init__(self, path: str | Path | None = None) -> None:
        path_obj = Path(path) if path else Path.home() / ".syrin" / "ratelimit.db"
        self._path = path_obj
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        import sqlite3

        with sqlite3.connect(str(self._path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rate_limits (
                    key TEXT PRIMARY KEY,
                    entries TEXT NOT NULL,
                    last_updated REAL NOT NULL
                )
            """
            )
            conn.commit()

    def save(self, key: str, state: RateLimitState) -> None:
        import json
        import sqlite3

        with sqlite3.connect(str(self._path)) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO rate_limits (key, entries, last_updated) VALUES (?, ?, ?)",
                (key, json.dumps(state.entries), state.last_updated),
            )
            conn.commit()

    def load(self, key: str) -> RateLimitState | None:
        import json
        import sqlite3

        with sqlite3.connect(str(self._path)) as conn:
            cursor = conn.execute(
                "SELECT entries, last_updated FROM rate_limits WHERE key = ?", (key,)
            )
            row = cursor.fetchone()
        if row:
            return RateLimitState(entries=json.loads(row[0]), last_updated=row[1])
        return None

    def delete(self, key: str) -> None:
        import sqlite3

        with sqlite3.connect(str(self._path)) as conn:
            conn.execute("DELETE FROM rate_limits WHERE key = ?", (key,))
            conn.commit()

    def exists(self, key: str) -> bool:
        import sqlite3

        with sqlite3.connect(str(self._path)) as conn:
            cursor = conn.execute("SELECT 1 FROM rate_limits WHERE key = ? LIMIT 1", (key,))
            exists = cursor.fetchone() is not None
        return exists


class RedisRateLimitBackend(RateLimitBackend):
    """Redis-based rate limit backend (distributed)."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
        key_prefix: str = "syrin:ratelimit:",
    ) -> None:
        try:
            import redis
        except ImportError:
            raise ImportError("redis package required: pip install redis") from None

        self._client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
        )
        self._key_prefix = key_prefix

    def _make_key(self, key: str) -> str:
        return f"{self._key_prefix}{key}"

    def save(self, key: str, state: RateLimitState) -> None:
        import json

        data = {"entries": state.entries, "last_updated": state.last_updated}
        self._client.set(self._make_key(key), json.dumps(data), ex=86400 * 7)  # 7 days TTL

    def load(self, key: str) -> RateLimitState | None:
        import json

        data = cast(str | None, self._client.get(self._make_key(key)))
        if data:
            parsed = json.loads(data)
            return RateLimitState(
                entries=parsed.get("entries", []), last_updated=parsed.get("last_updated", 0)
            )
        return None

    def delete(self, key: str) -> None:
        cast(int, self._client.delete(self._make_key(key)))

    def exists(self, key: str) -> bool:
        return cast(int, self._client.exists(self._make_key(key))) > 0


# Factory function
def get_rate_limit_backend(
    backend: str = "memory",
    **kwargs: object,
) -> RateLimitBackend:
    """Get a rate limit backend.

    Args:
        backend: Backend type ("memory", "sqlite", "redis")
        **kwargs: Backend-specific arguments

    Returns:
        RateLimitBackend instance

    Examples:
        >>> backend = get_rate_limit_backend("memory")
        >>> backend = get_rate_limit_backend("sqlite", path="/tmp/ratelimit.db")
        >>> backend = get_rate_limit_backend("redis", host="redis.example.com", port=6380)
    """
    if backend == "memory":
        return MemoryRateLimitBackend()
    elif backend == "sqlite":
        return SQLiteRateLimitBackend(path=kwargs.get("path"))  # type: ignore[arg-type]
    elif backend == "redis":
        return RedisRateLimitBackend(
            host=kwargs.get("host", "localhost"),  # type: ignore[arg-type]
            port=kwargs.get("port", 6379),  # type: ignore[arg-type]
            db=kwargs.get("db", 0),  # type: ignore[arg-type]
            password=kwargs.get("password"),  # type: ignore[arg-type]
            key_prefix=kwargs.get("key_prefix", "syrin:ratelimit:"),  # type: ignore[arg-type]
        )
    else:
        raise ValueError(f"Unknown backend: {backend}")


__all__ = [
    "RateLimitBackend",
    "RateLimitState",
    "MemoryRateLimitBackend",
    "SQLiteRateLimitBackend",
    "RedisRateLimitBackend",
    "get_rate_limit_backend",
]
