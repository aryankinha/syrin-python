"""Public memory-backends package facade.

This package exposes built-in memory backend implementations and the backend
factory used by memory configuration. Import from ``syrin.memory.backends`` for
backend classes, registry data, or ``get_backend``.
"""

from syrin.memory.backends._core import (
    BACKENDS,
    ChromaBackend,
    InMemoryBackend,
    PostgresBackend,
    QdrantBackend,
    RedisBackend,
    SQLiteBackend,
    get_backend,
)

__all__ = [
    "InMemoryBackend",
    "SQLiteBackend",
    "QdrantBackend",
    "ChromaBackend",
    "RedisBackend",
    "PostgresBackend",
    "get_backend",
    "BACKENDS",
]
