"""Knowledge store backends for vector storage."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from syrin.enums import KnowledgeBackend

from ._memory import InMemoryKnowledgeStore

__all__ = [
    "InMemoryKnowledgeStore",
    "get_knowledge_store",
    "register_knowledge_store",
]

if TYPE_CHECKING:
    from syrin.knowledge._store import KnowledgeStore

# Registry: maps backend name to (module_path, class_name) for lazy imports,
# or directly to a class.
_STORE_REGISTRY: dict[str, type[Any] | tuple[str, str]] = {
    KnowledgeBackend.MEMORY: InMemoryKnowledgeStore,
    KnowledgeBackend.POSTGRES: ("syrin.knowledge.stores._postgres", "PostgresKnowledgeStore"),
    KnowledgeBackend.QDRANT: ("syrin.knowledge.stores._qdrant", "QdrantKnowledgeStore"),
    KnowledgeBackend.CHROMA: ("syrin.knowledge.stores._chroma", "ChromaKnowledgeStore"),
    KnowledgeBackend.SQLITE: ("syrin.knowledge.stores._sqlite", "SQLiteKnowledgeStore"),
}

# Required kwargs per backend
_REQUIRED_KWARGS: dict[str, list[str]] = {
    KnowledgeBackend.POSTGRES: ["connection_url"],
    KnowledgeBackend.SQLITE: ["path"],
}

# Kwargs to pass per backend (maps backend → set of accepted kwargs)
_BACKEND_KWARGS: dict[str, set[str]] = {
    KnowledgeBackend.MEMORY: {"embedding_dimensions"},
    KnowledgeBackend.POSTGRES: {"connection_url", "table_name", "embedding_dimensions"},
    KnowledgeBackend.QDRANT: {"embedding_dimensions", "collection", "path"},
    KnowledgeBackend.CHROMA: {"embedding_dimensions", "collection_name", "path"},
    KnowledgeBackend.SQLITE: {"path", "embedding_dimensions"},
}


def register_knowledge_store(name: str, cls: type[Any]) -> None:
    """Register a custom knowledge store backend.

    Args:
        name: Backend name (string or KnowledgeBackend value).
        cls: Store class (must implement KnowledgeStore protocol).

    Example:
        register_knowledge_store("my_store", MyCustomStore)
    """
    _STORE_REGISTRY[name] = cls


def _resolve_class(entry: type[Any] | tuple[str, str]) -> type[Any]:
    """Resolve a registry entry to a class (lazy import if needed)."""
    if isinstance(entry, tuple):
        import importlib

        module_path, class_name = entry
        module = importlib.import_module(module_path)
        return getattr(module, class_name)  # type: ignore[no-any-return]
    return entry


def get_knowledge_store(
    backend: KnowledgeBackend,
    *,
    embedding_dimensions: int = 1536,
    connection_url: str | None = None,
    path: str | None = None,
    table_name: str = "syrin_knowledge",
    collection: str = "syrin_knowledge",
) -> KnowledgeStore:
    """Create a KnowledgeStore for the given backend.

    Args:
        backend: Which backend to use.
        embedding_dimensions: Vector size (required for MEMORY, POSTGRES, etc.).
        connection_url: Postgres connection URL (for POSTGRES).
        path: File path for SQLite or embedded Qdrant.
        table_name: Postgres table name.
        collection: Qdrant/Chroma collection name.

    Returns:
        KnowledgeStore instance.

    Raises:
        ImportError: If optional deps for backend not installed.
        ValueError: If required kwargs missing for backend or unknown backend.
    """
    backend_key = str(backend)
    if backend_key not in _STORE_REGISTRY:
        raise ValueError(f"Unknown backend: {backend}")

    # Validate required kwargs
    for req in _REQUIRED_KWARGS.get(backend_key, []):
        val = locals().get(req)
        if not val:
            raise ValueError(f"{req} required for {backend.name} backend")

    cls = _resolve_class(_STORE_REGISTRY[backend_key])

    # Build kwargs for the specific backend
    all_kwargs: dict[str, Any] = {
        "embedding_dimensions": embedding_dimensions,
        "connection_url": connection_url,
        "path": path,
        "table_name": table_name,
        "collection": collection,
        "collection_name": collection,  # Chroma uses collection_name
    }
    accepted = _BACKEND_KWARGS.get(backend_key)
    if accepted is not None:
        filtered = {k: v for k, v in all_kwargs.items() if k in accepted and v is not None}
    else:
        # Custom backends: pass all non-None kwargs
        filtered = {k: v for k, v in all_kwargs.items() if v is not None}

    return cls(**filtered)  # type: ignore[no-any-return]
