"""Public knowledge-stores package facade.

This package exposes knowledge-store registration and lookup helpers for the
retrieval system. Import from ``syrin.knowledge.stores`` for the default
in-memory store and custom-store registration helpers.
"""

from syrin.knowledge.stores._core import (
    InMemoryKnowledgeStore,
    get_knowledge_store,
    register_knowledge_store,
)

__all__ = ["InMemoryKnowledgeStore", "get_knowledge_store", "register_knowledge_store"]
