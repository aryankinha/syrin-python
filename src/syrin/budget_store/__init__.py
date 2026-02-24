"""Budget persistence: store and load budget tracker state."""

from __future__ import annotations

import contextlib
import json
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from syrin.budget import BudgetTracker

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[assignment]

try:
    import msvcrt
except ImportError:
    msvcrt = None  # type: ignore[assignment]


def _lock_file(f: Any) -> None:
    """Acquire exclusive lock on file (fcntl on Unix, msvcrt on Windows)."""
    if sys.platform == "win32" and msvcrt is not None:
        try:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
        except (OSError, AttributeError):
            pass
    elif fcntl is not None:
        with contextlib.suppress(OSError, AttributeError):
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)


def _unlock_file(f: Any) -> None:
    """Release exclusive lock on file."""
    if sys.platform == "win32" and msvcrt is not None:
        try:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        except (OSError, AttributeError):
            pass
    elif fcntl is not None:
        with contextlib.suppress(OSError, AttributeError):
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


class BudgetStore(ABC):
    """Abstract interface for persisting budget tracker state."""

    @abstractmethod
    def load(self, key: str) -> BudgetTracker | None:
        """Load tracker state for key. Returns None if not found."""
        ...

    @abstractmethod
    def save(self, key: str, tracker: BudgetTracker) -> None:
        """Save tracker state for key."""
        ...


class InMemoryBudgetStore(BudgetStore):
    """In-memory store; state is lost when process exits."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    def load(self, key: str) -> BudgetTracker | None:
        state = self._store.get(key)
        if state is None:
            return None
        tracker = BudgetTracker()
        tracker.load_state(state)
        return tracker

    def save(self, key: str, tracker: BudgetTracker) -> None:
        self._store[key] = tracker.get_state()


class FileBudgetStore(BudgetStore):
    """JSON file store for rate limits across restarts. One file per key or single file with keys."""

    def __init__(self, path: str | Path, *, single_file: bool = True) -> None:
        self._path = Path(path)
        self._single_file = single_file

    def _file_for(self, key: str) -> Path:
        if self._single_file:
            return self._path
        return self._path / f"{key}.json"

    def load(self, key: str) -> BudgetTracker | None:
        path = self._file_for(key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            if self._single_file:
                data = data.get(key) if isinstance(data, dict) else None
            if data is None:
                return None
            tracker = BudgetTracker()
            tracker.load_state(data)
            return tracker
        except (json.JSONDecodeError, OSError):
            return None

    def save(self, key: str, tracker: BudgetTracker) -> None:
        path = self._file_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        if self._single_file:
            all_data: dict[str, Any] = {}
            with path.open("a") as _:
                pass
            with path.open("r+") as f:
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
                finally:
                    _unlock_file(f)
        else:
            path.write_text(json.dumps(tracker.get_state(), indent=2))
