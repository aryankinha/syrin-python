"""Checkpoint system for agent state persistence."""

from __future__ import annotations

import logging
import os
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class CheckpointTrigger(StrEnum):
    """When checkpoints are automatically saved."""

    MANUAL = "manual"
    STEP = "step"
    TOOL = "tool"
    ERROR = "error"
    BUDGET = "budget"


class CheckpointState(BaseModel):
    """Snapshot of agent state for checkpointing."""

    agent_name: str
    checkpoint_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    messages: list[Any] = Field(default_factory=list)
    memory_data: dict[str, Any] = Field(default_factory=dict)
    budget_state: dict[str, Any] | None = None
    iteration: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


class CheckpointConfig(BaseModel):
    """Configuration for checkpoint behavior.

    Immutable after creation (config objects are immutable per architecture).
    Runtime state (checkpoint IDs, saved state) lives in Checkpointer/backends.

    Usage:
        agent = Agent(
            model=Model("gpt-4o"),
            checkpoint=Checkpoint(
                storage="sqlite",
                path="/tmp/agent_checkpoints.db",
                trigger="step",
                max_checkpoints=10,
            ),
        )
    """

    model_config = ConfigDict(frozen=True)

    enabled: bool = True
    storage: str = Field(default="memory", pattern="^(memory|sqlite|postgres|filesystem)$")
    path: str | None = None
    trigger: CheckpointTrigger = CheckpointTrigger.STEP
    max_checkpoints: int = Field(default=10, ge=1)
    compress: bool = False

    def __init__(self, **data: Any) -> None:
        """Initialize checkpoint config with validation."""
        if "trigger" in data and isinstance(data["trigger"], str):
            data["trigger"] = CheckpointTrigger(data["trigger"])
        super().__init__(**data)


class CheckpointBackendProtocol(ABC):
    """Protocol for checkpoint storage backends."""

    @abstractmethod
    def save(self, state: CheckpointState) -> None:
        """Save checkpoint state."""
        ...

    @abstractmethod
    def load(self, checkpoint_id: str) -> CheckpointState | None:
        """Load checkpoint state by ID."""
        ...

    @abstractmethod
    def list(self, agent_name: str) -> list[str]:
        """List checkpoint IDs for an agent."""
        ...

    @abstractmethod
    def delete(self, checkpoint_id: str) -> None:
        """Delete a checkpoint."""
        ...


class MemoryCheckpointBackend(CheckpointBackendProtocol):
    """In-memory checkpoint storage (testing, ephemeral)."""

    def __init__(self) -> None:
        self._checkpoints: dict[str, CheckpointState] = {}

    def save(self, state: CheckpointState) -> None:
        self._checkpoints[state.checkpoint_id] = state

    def load(self, checkpoint_id: str) -> CheckpointState | None:
        return self._checkpoints.get(checkpoint_id)

    def list(self, agent_name: str) -> list[str]:
        return [
            ck.checkpoint_id for ck in self._checkpoints.values() if ck.agent_name == agent_name
        ]

    def delete(self, checkpoint_id: str) -> None:
        self._checkpoints.pop(checkpoint_id, None)


class SQLiteCheckpointBackend(CheckpointBackendProtocol):
    """SQLite-based checkpoint storage (persistent, file-based)."""

    def __init__(self, path: str | Path | None = None) -> None:
        if path is None:
            path = os.path.expanduser("~/.syrin/checkpoints.db")
        self._path = str(path)
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """Create tables if they don't exist."""
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        conn = sqlite3.connect(self._path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                checkpoint_id TEXT PRIMARY KEY,
                agent_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                state_json TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_name ON checkpoints(agent_name)
        """)
        conn.commit()
        conn.close()

    def save(self, state: CheckpointState) -> None:
        """Save checkpoint to SQLite."""
        conn = sqlite3.connect(self._path)
        state_json = state.model_dump_json()
        conn.execute(
            """
            INSERT OR REPLACE INTO checkpoints (checkpoint_id, agent_name, created_at, state_json)
            VALUES (?, ?, ?, ?)
            """,
            (state.checkpoint_id, state.agent_name, state.created_at.isoformat(), state_json),
        )
        conn.commit()
        conn.close()

    def load(self, checkpoint_id: str) -> CheckpointState | None:
        """Load checkpoint from SQLite."""
        conn = sqlite3.connect(self._path)
        cursor = conn.execute(
            "SELECT state_json FROM checkpoints WHERE checkpoint_id = ?",
            (checkpoint_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None
        return CheckpointState.model_validate_json(row[0])

    def list(self, agent_name: str) -> list[str]:
        """List checkpoint IDs for an agent."""
        conn = sqlite3.connect(self._path)
        cursor = conn.execute(
            "SELECT checkpoint_id FROM checkpoints WHERE agent_name = ? ORDER BY created_at",
            (agent_name,),
        )
        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        return results

    def delete(self, checkpoint_id: str) -> None:
        """Delete a checkpoint."""
        conn = sqlite3.connect(self._path)
        conn.execute("DELETE FROM checkpoints WHERE checkpoint_id = ?", (checkpoint_id,))
        conn.commit()
        conn.close()


class FilesystemCheckpointBackend(CheckpointBackendProtocol):
    """Filesystem-based checkpoint storage (JSON files)."""

    def __init__(self, path: str | Path | None = None) -> None:
        if path is None:
            path = os.path.expanduser("~/.syrin/checkpoints")
        self._path = Path(path)
        self._path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, checkpoint_id: str) -> Path:
        return self._path / f"{checkpoint_id}.json"

    def save(self, state: CheckpointState) -> None:
        file_path = self._get_file_path(state.checkpoint_id)
        file_path.write_text(state.model_dump_json())

    def load(self, checkpoint_id: str) -> CheckpointState | None:
        file_path = self._get_file_path(checkpoint_id)
        if not file_path.exists():
            return None
        return CheckpointState.model_validate_json(file_path.read_text())

    def list(self, agent_name: str) -> list[str]:
        results = []
        for file_path in self._path.glob("*.json"):
            try:
                state = CheckpointState.model_validate_json(file_path.read_text())
                if state.agent_name == agent_name:
                    results.append(state.checkpoint_id)
            except Exception:
                continue
        return sorted(results)

    def delete(self, checkpoint_id: str) -> None:
        file_path = self._get_file_path(checkpoint_id)
        if file_path.exists():
            file_path.unlink()


class Checkpointer:
    """Checkpoint manager for agent state.

    Provides a simple API to save, load, list, and delete checkpoints.

    Usage:
        checkpointer = Checkpointer()
        checkpoint_id = checkpointer.save("my_agent", {"iteration": 5, "messages": []})
        state = checkpointer.load(checkpoint_id)
        checkpoints = checkpointer.list_checkpoints("my_agent")
        checkpointer.delete(checkpoint_id)
    """

    def __init__(
        self,
        strategy: str = "incremental",
        backend: CheckpointBackendProtocol | None = None,
        max_checkpoints: int = 10,
    ) -> None:
        self._strategy = strategy
        self._backend = backend or MemoryCheckpointBackend()
        self._counters: dict[str, int] = {}
        self._max_checkpoints = max_checkpoints

    def _get_next_id(self, agent_name: str) -> str:
        """Get next checkpoint ID for an agent."""
        if agent_name not in self._counters:
            self._counters[agent_name] = 0
        self._counters[agent_name] += 1
        return f"{agent_name}_{self._counters[agent_name]}"

    def save(self, agent_name: str, state: dict[str, Any]) -> str:
        """Save checkpoint and return checkpoint ID.

        Args:
            agent_name: Name of the agent
            state: State dictionary to save

        Returns:
            The checkpoint ID that can be used to load the checkpoint
        """
        checkpoint_id = self._get_next_id(agent_name)
        checkpoint_state = CheckpointState(
            agent_name=agent_name,
            checkpoint_id=checkpoint_id,
            metadata=state,
            iteration=state.get("iteration", 0),
            messages=state.get("messages", []),
            memory_data=state.get("memory_data", {}),
            budget_state=state.get("budget_state"),
        )
        self._backend.save(checkpoint_state)
        return checkpoint_id

    def load(self, checkpoint_id: str) -> CheckpointState | None:
        """Load checkpoint by ID.

        Args:
            checkpoint_id: The checkpoint ID returned from save()

        Returns:
            CheckpointState if found, None otherwise
        """
        return self._backend.load(checkpoint_id)

    def list_checkpoints(self, agent_name: str) -> list[str]:
        """List checkpoints for an agent.

        Args:
            agent_name: Name of the agent

        Returns:
            List of checkpoint IDs, sorted by creation time
        """
        return self._backend.list(agent_name)

    def delete(self, checkpoint_id: str) -> None:
        """Delete a checkpoint.

        Args:
            checkpoint_id: The checkpoint ID to delete
        """
        self._backend.delete(checkpoint_id)

    def get_latest(self, agent_name: str) -> CheckpointState | None:
        """Get the most recent checkpoint for an agent.

        Args:
            agent_name: Name of the agent

        Returns:
            The latest CheckpointState or None if no checkpoints exist
        """
        checkpoints = self._backend.list(agent_name)
        if not checkpoints:
            return None
        return self._backend.load(checkpoints[-1])


BACKENDS: dict[str, type[CheckpointBackendProtocol]] = {
    "memory": MemoryCheckpointBackend,
    "sqlite": SQLiteCheckpointBackend,
    "filesystem": FilesystemCheckpointBackend,
}


def get_checkpoint_backend(backend: str, **kwargs: Any) -> CheckpointBackendProtocol:
    """Get a checkpoint backend instance.

    Args:
        backend: Backend name ('memory', 'sqlite', 'filesystem')
        **kwargs: Additional arguments passed to backend constructor

    Returns:
        CheckpointBackendProtocol instance

    Raises:
        ValueError: If backend name is unknown

    Usage:
        backend = get_checkpoint_backend("sqlite", path="/tmp/checkpoints.db")
    """
    backend_class = BACKENDS.get(backend)
    if backend_class is None:
        raise ValueError(
            f"Unknown checkpoint backend: {backend}. Available: {list(BACKENDS.keys())}"
        )
    return backend_class(**kwargs)


__all__ = [
    "CheckpointState",
    "CheckpointConfig",
    "CheckpointTrigger",
    "CheckpointBackendProtocol",
    "MemoryCheckpointBackend",
    "SQLiteCheckpointBackend",
    "FilesystemCheckpointBackend",
    "Checkpointer",
    "get_checkpoint_backend",
    "BACKENDS",
]
