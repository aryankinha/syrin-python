"""Public knowledge-chunkers package facade.

This package exposes built-in chunking strategies for the knowledge pipeline.
Import from ``syrin.knowledge.chunkers`` for concrete chunker classes or the
``get_chunker`` helper that resolves a chunker from configuration.
"""

from syrin.knowledge.chunkers._core import (
    AutoChunker,
    CodeChunker,
    MarkdownChunker,
    MarkdownHeaderChunker,
    PageChunker,
    PythonASTChunker,
    RecursiveChunker,
    SemanticChunker,
    SentenceChunker,
    TokenChunker,
    get_chunker,
)

__all__ = [
    "AutoChunker",
    "CodeChunker",
    "MarkdownChunker",
    "MarkdownHeaderChunker",
    "PageChunker",
    "PythonASTChunker",
    "RecursiveChunker",
    "SemanticChunker",
    "SentenceChunker",
    "TokenChunker",
    "get_chunker",
]
