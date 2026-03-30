"""Budget persistence: store and load budget tracker state.

``BudgetStore`` is a concrete class that wraps a swappable backend. Use it
for per-user or per-session budget persistence across agent restarts.

Example::

    # In-memory (default, ephemeral)
    store = BudgetStore(key="user:123")

    # File-based persistence
    store = BudgetStore(key="user:123", backend="file", path="/var/budgets.json")

    # Custom backend (implements BudgetBackend Protocol)
    store = BudgetStore(key="org:acme", backend=MyDatabaseBackend())

    agent = Agent(model=..., budget=Budget(max_cost=1.0), budget_store=store)
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import sys
from pathlib import Path
from typing import Protocol, runtime_checkable

from syrin.budget import BudgetTracker

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[assignment]

try:
    import msvcrt
except ImportError:
    msvcrt = None  # type: ignore[assignment]


def _lock_file(f: io.BufferedIOBase | io.TextIOBase) -> None:
    """Acquire exclusive lock on file (fcntl on Unix, msvcrt on Windows)."""
    if sys.platform == "win32" and msvcrt is not None:
        try:
            f.seek(0)
            size = os.path.getsize(f.name) if hasattr(f, "name") and f.name else 1
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, max(1, size))
        except (OSError, AttributeError):
            pass
    elif fcntl is not None:
        with contextlib.suppress(OSError, AttributeError):
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)


def _unlock_file(f: io.BufferedIOBase | io.TextIOBase) -> None:
    """Release exclusive lock on file."""
    if sys.platform == "win32" and msvcrt is not None:
        try:
            f.seek(0)
            size = os.path.getsize(f.name) if hasattr(f, "name") and f.name else 1
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, max(1, size))
        except (OSError, AttributeError):
            pass
    elif fcntl is not None:
        with contextlib.suppress(OSError, AttributeError):
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def _validate_key(key: str) -> None:
    """Reject keys with path traversal characters or empty keys."""
    if not key or not re.match(r"^[a-zA-Z0-9_.:@-]+$", key):
        raise ValueError(f"Invalid budget store key (illegal characters): {key!r}")


@runtime_checkable
class BudgetBackend(Protocol):
    """Protocol for custom budget persistence backends.

    Implement this to plug in any storage system (Redis, DynamoDB, Postgres, etc.)
    and pass as ``BudgetStore(key=..., backend=MyBackend())``.

    Methods:
        load: Return BudgetTracker for key, or None if not found.
        save: Persist tracker under key.
    """

    def load(self, key: str) -> BudgetTracker | None:
        """Load budget tracker for the given key."""
        ...

    def save(self, key: str, tracker: BudgetTracker) -> None:
        """Persist budget tracker under the given key."""
        ...


class _MemoryBudgetBackend:
    """In-memory backend. State is lost when process exits. Default backend."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, object]] = {}

    def load(self, key: str) -> BudgetTracker | None:
        state = self._store.get(key)
        if state is None:
            return None
        tracker = BudgetTracker()
        tracker.load_state(state)
        return tracker

    def save(self, key: str, tracker: BudgetTracker) -> None:
        self._store[key] = tracker.get_state()


class _FileBudgetBackend:
    """JSON file backend. Persists budget across restarts. Uses file locking."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self, key: str) -> BudgetTracker | None:
        if not self._path.exists():
            return None
        try:
            data = json.loads(self._path.read_text())
            entry = data.get(key) if isinstance(data, dict) else None
            if entry is None:
                return None
            tracker = BudgetTracker()
            tracker.load_state(entry)
            return tracker
        except (json.JSONDecodeError, OSError):
            return None

    def save(self, key: str, tracker: BudgetTracker) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        all_data: dict[str, object] = {}
        with self._path.open("a"):
            pass
        with self._path.open("r+") as f:
            _lock_file(f)
            try:
                raw = f.read()
                if raw:
                    try:
                        all_data = json.loads(raw)
                        if not isinstance(all_data, dict):
                            all_data = {}
                    except json.JSONDecodeError:
                        all_data = {}
                all_data[key] = tracker.get_state()
                f.seek(0)
                f.truncate()
                f.write(json.dumps(all_data, indent=2))
                f.flush()
                with contextlib.suppress(OSError):
                    os.fsync(f.fileno())
            finally:
                _unlock_file(f)


# Shared in-memory store — one dict per process, keyed by BudgetStore.key.
# Separate BudgetStore instances with the same key share state (like FileBudgetStore
# instances pointing to the same file share state).
_SHARED_MEMORY_STORE: dict[str, dict[str, object]] = {}


class BudgetStore:
    """Concrete budget persistence class with swappable backend.

    Replaces the old ``FileBudgetStore`` / ``InMemoryBudgetStore`` split.
    One class, ``backend=`` selects the storage.

    Args:
        key: Persistence key — identifies the budget (e.g. "user:123", "session:abc").
            Isolates budgets per user, session, or any dimension you choose.
        backend: Storage backend. One of:
            - ``"memory"`` (default) — in-memory, ephemeral.
            - ``"file"`` — JSON file. Requires ``path=``.
            - A custom object implementing the ``BudgetBackend`` Protocol.
        path: File path (required when ``backend="file"``).

    Example::

        # In-memory (ephemeral, default)
        store = BudgetStore(key="user:123")

        # File persistence
        store = BudgetStore(key="user:123", backend="file", path="/var/budgets.json")

        # Custom backend
        store = BudgetStore(key="org:acme", backend=MyRedisBackend())

        agent = Agent(model=..., budget=Budget(max_cost=1.0), budget_store=store)
    """

    def __init__(
        self,
        key: str,
        *,
        backend: str | BudgetBackend = "memory",
        path: str | Path | None = None,
    ) -> None:
        self._key = key
        if isinstance(backend, str):
            if backend == "memory":
                self._backend: BudgetBackend = _MemoryBudgetBackend()
            elif backend == "file":
                if path is None:
                    raise ValueError("BudgetStore(backend='file') requires path= to be set.")
                self._backend = _FileBudgetBackend(Path(path))
            else:
                raise ValueError(
                    f"Unknown backend string: {backend!r}. "
                    "Use 'memory', 'file', or pass a custom BudgetBackend object."
                )
        else:
            self._backend = backend

    @property
    def key(self) -> str:
        """The persistence key for this store."""
        return self._key

    def load(self) -> BudgetTracker | None:
        """Load budget tracker for this store's key.

        Returns:
            BudgetTracker if found, None otherwise.
        """
        return self._backend.load(self._key)

    def save(self, tracker: BudgetTracker) -> None:
        """Persist tracker under this store's key.

        Args:
            tracker: The BudgetTracker to persist.
        """
        _validate_key(self._key)
        self._backend.save(self._key, tracker)


__all__ = ["BudgetStore", "BudgetBackend"]
