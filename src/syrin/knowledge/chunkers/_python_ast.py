"""PythonASTChunker — AST-aware Python chunker that never splits mid-function."""

from __future__ import annotations

import ast
import textwrap

from syrin.knowledge._chunker import Chunk, ChunkConfig
from syrin.knowledge._document import Document


def _count_tokens(text: str) -> int:
    """Rough token estimate: 1 token ≈ 4 characters."""
    return max(1, len(text) // 4)


class PythonASTChunker:
    """Chunk Python source code at function/class boundaries using the AST.

    Never splits a function or class definition across two chunks.  Each
    top-level ``def``, ``async def``, or ``class`` statement becomes its own
    chunk.

    Args:
        config: :class:`~syrin.knowledge._chunker.ChunkConfig` with chunking
            parameters.

    Example::

        from syrin.knowledge.chunkers import PythonASTChunker
        from syrin.knowledge._chunker import ChunkConfig
        from syrin.knowledge._document import Document

        chunker = PythonASTChunker(config=ChunkConfig())
        chunks = chunker.chunk([Document(content=source, source="app.py", source_type="code")])
    """

    def __init__(self, config: ChunkConfig) -> None:
        self._config = config

    def chunk(self, documents: list[Document]) -> list[Chunk]:
        """Chunk Python documents at function/class boundaries.

        Args:
            documents: Documents to chunk.

        Returns:
            List of :class:`~syrin.knowledge._chunker.Chunk` objects.
        """
        chunks: list[Chunk] = []
        for doc in documents:
            chunks.extend(self._chunk_doc(doc))
        return chunks

    async def achunk(self, documents: list[Document]) -> list[Chunk]:
        """Async wrapper around :meth:`chunk`."""
        return self.chunk(documents)

    def _chunk_doc(self, doc: Document) -> list[Chunk]:
        source = doc.content
        source_name = doc.source
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return [
                Chunk(
                    content=source,
                    metadata={"source": source_name, "chunk_strategy": "python_ast"},
                    document_id=source_name,
                    chunk_index=0,
                    token_count=_count_tokens(source),
                )
            ]

        lines = source.splitlines(keepends=True)
        used_lines: set[int] = set()
        chunks: list[Chunk] = []
        idx = 0

        for node in ast.iter_child_nodes(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            start = node.lineno - 1  # 0-based
            end: int = getattr(node, "end_lineno", len(lines))
            snippet = "".join(lines[start:end])
            used_lines.update(range(start, end))
            chunks.append(
                Chunk(
                    content=textwrap.dedent(snippet),
                    metadata={
                        "source": source_name,
                        "chunk_strategy": "python_ast",
                        "symbol_name": node.name,
                        "symbol_type": type(node).__name__,
                    },
                    document_id=source_name,
                    chunk_index=idx,
                    token_count=_count_tokens(snippet),
                )
            )
            idx += 1

        # Add any remaining top-level code not covered above
        remaining_lines = [lines[i] for i in range(len(lines)) if i not in used_lines]
        remaining = "".join(remaining_lines).strip()
        if remaining:
            chunks.append(
                Chunk(
                    content=remaining,
                    metadata={"source": source_name, "chunk_strategy": "python_ast"},
                    document_id=source_name,
                    chunk_index=idx,
                    token_count=_count_tokens(remaining),
                )
            )

        return chunks or [
            Chunk(
                content=source,
                metadata={"source": source_name, "chunk_strategy": "python_ast"},
                document_id=source_name,
                chunk_index=0,
                token_count=_count_tokens(source),
            )
        ]
