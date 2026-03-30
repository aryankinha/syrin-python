"""Public embedding package facade.

This package exposes embedding providers and the embedding namespace used by
knowledge and memory features. Import from ``syrin.embedding`` for provider
types and factory-style embedding constructors.
"""

from syrin.embedding._core import (
    Embedding,
    EmbeddingBackend,
    EmbeddingProvider,
    OllamaEmbedding,
    OpenAIEmbedding,
)

__all__ = [
    "Embedding",
    "EmbeddingBackend",
    "EmbeddingProvider",
    "OllamaEmbedding",
    "OpenAIEmbedding",
]
