"""MarkdownHeaderChunker — splits Markdown at header boundaries."""

from __future__ import annotations

import re

from syrin.knowledge._chunker import Chunk, ChunkConfig
from syrin.knowledge._document import Document

_HEADER_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def _count_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class MarkdownHeaderChunker:
    """Chunk Markdown documents at header (``#``) boundaries.

    Splits on any heading level (``#`` through ``######``), keeping the
    heading text with its following content as a single chunk.  Never splits
    in the middle of a paragraph.

    Args:
        config: :class:`~syrin.knowledge._chunker.ChunkConfig`.
        min_header_level: Minimum heading level to split on (1–6).
            Default ``1`` (all headings trigger a split).

    Example::

        from syrin.knowledge.chunkers import MarkdownHeaderChunker
        from syrin.knowledge._chunker import ChunkConfig

        chunker = MarkdownHeaderChunker(config=ChunkConfig())
        chunks = chunker.chunk([doc])
    """

    def __init__(self, config: ChunkConfig, *, min_header_level: int = 1) -> None:
        self._config = config
        self._min_header_level = min_header_level

    def chunk(self, documents: list[Document]) -> list[Chunk]:
        """Chunk Markdown documents at header boundaries.

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
        source = doc.source
        text = doc.content

        # Find all header positions
        splits: list[int] = [0]
        for m in _HEADER_RE.finditer(text):
            level = len(m.group(1))
            if level >= self._min_header_level:
                pos = m.start()
                if pos > 0:
                    splits.append(pos)

        splits = sorted(set(splits))
        splits.append(len(text))

        chunks: list[Chunk] = []
        for i, start in enumerate(splits[:-1]):
            end = splits[i + 1]
            section = text[start:end].strip()
            if not section:
                continue
            header_m = _HEADER_RE.match(section)
            header = header_m.group(2) if header_m else ""
            chunks.append(
                Chunk(
                    content=section,
                    metadata={
                        "source": source,
                        "chunk_strategy": "markdown_header",
                        "header": header,
                    },
                    document_id=source,
                    chunk_index=len(chunks),
                    token_count=_count_tokens(section),
                )
            )

        return chunks or [
            Chunk(
                content=text,
                metadata={"source": source, "chunk_strategy": "markdown_header"},
                document_id=source,
                chunk_index=0,
                token_count=_count_tokens(text),
            )
        ]
