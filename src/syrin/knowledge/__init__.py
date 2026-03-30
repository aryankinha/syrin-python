"""Public knowledge package facade.

This package exposes Syrin's knowledge and retrieval API for RAG-style workflows.
Import from ``syrin.knowledge`` when you need the high-level ``Knowledge``
orchestrator, chunk/document models, built-in loaders, or hybrid retrieval
support. Runtime implementation lives in private modules so the package root
remains a stable public surface.

Why use this package:
    - Build agent knowledge bases from files, directories, URLs, and text.
    - Configure chunking, embedding, storage, grounding, and agentic retrieval.
    - Reuse document, chunk, and loader primitives in custom ingestion flows.

Typical usage:
    >>> from syrin.knowledge import Knowledge
    >>> knowledge = Knowledge(
    ...     sources=[Knowledge.Text("Syrin supports retrieval workflows.")],
    ... )

Exported surface:
    - ``Knowledge`` for end-to-end retrieval orchestration
    - document, chunk, and grounding models used by the knowledge pipeline
    - built-in loaders and helper factories such as ``get_chunker``
"""

from syrin.knowledge._core import (
    CancellableIngestTask,
    Chunk,
    Chunker,
    ChunkMetadata,
    ChunkStrategy,
    CodeChunk,
    CSVLoader,
    DirectoryLoader,
    DoclingLoader,
    Document,
    DocumentLoader,
    DocumentMetadata,
    DOCXLoader,
    ExcelLoader,
    GitHubLoader,
    GoogleDriveLoader,
    GroundedFact,
    HybridSearchConfig,
    JSONLoader,
    Knowledge,
    MarkdownLoader,
    PDFLoader,
    PythonLoader,
    RawTextLoader,
    TextLoader,
    URLLoader,
    YAMLLoader,
    get_chunker,
)

__all__ = [
    "GroundedFact",
    "Chunk",
    "ChunkMetadata",
    "ChunkStrategy",
    "Chunker",
    "CodeChunk",
    "Document",
    "DocumentMetadata",
    "DocumentLoader",
    "DirectoryLoader",
    "DoclingLoader",
    "CSVLoader",
    "CancellableIngestTask",
    "DOCXLoader",
    "ExcelLoader",
    "get_chunker",
    "GitHubLoader",
    "GoogleDriveLoader",
    "HybridSearchConfig",
    "JSONLoader",
    "Knowledge",
    "MarkdownLoader",
    "PDFLoader",
    "PythonLoader",
    "RawTextLoader",
    "TextLoader",
    "URLLoader",
    "YAMLLoader",
]
