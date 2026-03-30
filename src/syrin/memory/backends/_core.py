"""Memory backends.

Available backends:
- MEMORY: In-memory storage (default, ephemeral)
- SQLITE: File-based SQLite storage (persistent)
- QDRANT: Vector database for semantic search
- CHROMA: Lightweight vector database
- REDIS: Fast in-memory cache
- POSTGRES: PostgreSQL for production

Each backend may have different optional dependencies:
- QDRANT: pip install qdrant-client
- CHROMA: pip install chromadb
- REDIS: pip install redis
- POSTGRES: pip install psycopg2-binary numpy
"""

from __future__ import annotations

from syrin.enums import MemoryBackend

from .chroma import ChromaBackend
from .memory import InMemoryBackend
from .postgres import PostgresBackend
from .qdrant import QdrantBackend
from .redis import RedisBackend
from .sqlite import SQLiteBackend

# Base type for all backends
BackendBase = InMemoryBackend

BACKENDS: dict[MemoryBackend, type[object]] = {
    MemoryBackend.MEMORY: InMemoryBackend,
    MemoryBackend.SQLITE: SQLiteBackend,
    MemoryBackend.QDRANT: QdrantBackend,
    MemoryBackend.CHROMA: ChromaBackend,
    MemoryBackend.REDIS: RedisBackend,
    MemoryBackend.POSTGRES: PostgresBackend,
}


def get_backend(backend: MemoryBackend, **kwargs: object) -> InMemoryBackend:
    """Get a memory backend instance.

    Args:
        backend: The backend type
        **kwargs: Additional arguments passed to the backend:

    Backend-specific options:
    - MEMORY: No additional options
    - SQLITE: path: str - Database file path (default: ~/.syrin/memory.db)
    - QDRANT: host, port, collection, vector_size
    - CHROMA: path, collection_name
    - REDIS: host, port, db, password, prefix, ttl
    - POSTGRES: host, port, database, user, password, table, vector_size

    Returns:
        A backend instance

    Example:
        >>> # In-memory (ephemeral)
        >>> backend = get_backend(MemoryBackend.MEMORY)
        >>>
        >>> # SQLite (persistent)
        >>> backend = get_backend(MemoryBackend.SQLITE, path="./memory.db")
        >>>
        >>> # QDRANT (semantic search)
        >>> backend = get_backend(MemoryBackend.QDRANT, host="localhost", port=6333)
    """
    backend_class = BACKENDS.get(backend)
    if backend_class is None:
        raise ValueError(f"Unknown memory backend: {backend}. Available: {list(BACKENDS.keys())}")
    return backend_class(**kwargs)  # type: ignore[return-value]


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
