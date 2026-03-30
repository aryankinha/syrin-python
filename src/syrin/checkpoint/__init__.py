"""Public checkpoint package facade.

This package exposes Syrin's checkpointing API for saving and restoring agent
state. Import from ``syrin.checkpoint`` when you need checkpoint configuration,
backends, or the checkpointer itself. The implementation lives in private
modules so the package root stays focused on the public contract.

Why use this package:
    - Configure when agent state should be persisted during execution.
    - Choose storage backends such as in-memory, SQLite, or filesystem.
    - Restore prior state for resume, recovery, testing, and inspection flows.

Typical usage:
    >>> from syrin.checkpoint import CheckpointConfig, CheckpointTrigger
    >>> cfg = CheckpointConfig(
    ...     storage="sqlite",
    ...     path="/tmp/agent_checkpoints.db",
    ...     trigger=CheckpointTrigger.STEP,
    ... )

Exported surface:
    - ``CheckpointConfig`` for checkpoint policy and storage settings
    - ``CheckpointTrigger`` for auto-save triggers
    - ``Checkpointer`` and backend types for storage and restore operations
    - ``CheckpointState`` for serialized checkpoint payloads
"""

from syrin.checkpoint._core import (
    BACKENDS,
    CheckpointBackendProtocol,
    CheckpointConfig,
    Checkpointer,
    CheckpointState,
    CheckpointTrigger,
    FilesystemCheckpointBackend,
    MemoryCheckpointBackend,
    SQLiteCheckpointBackend,
    get_checkpoint_backend,
)

__all__ = [
    "BACKENDS",
    "CheckpointBackendProtocol",
    "CheckpointConfig",
    "CheckpointState",
    "Checkpointer",
    "CheckpointTrigger",
    "FilesystemCheckpointBackend",
    "get_checkpoint_backend",
    "MemoryCheckpointBackend",
    "SQLiteCheckpointBackend",
]
