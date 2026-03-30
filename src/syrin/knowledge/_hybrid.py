"""CodeChunk dataclass, HybridSearchConfig, and CancellableIngestTask."""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class CodeChunk:
    """A chunk of source code with language and symbol metadata.

    Extends the basic chunk concept with code-specific fields useful for
    code search and navigation.

    Attributes:
        content: The source-code text of the chunk.
        language: Programming language (e.g. ``"python"``, ``"typescript"``).
        symbol_name: Name of the function, class, or module in this chunk.
        symbol_type: Type of symbol: ``"function"``, ``"class"``, ``"method"``, etc.
        source_file: Path or URL to the source file.
        start_line: 1-based start line of this chunk in the source file.
        end_line: 1-based end line of this chunk in the source file.
        docstring: Extracted docstring / JSDoc comment, if any.
    """

    content: str
    language: str
    symbol_name: str
    symbol_type: str
    source_file: str
    start_line: int
    end_line: int
    docstring: str = ""


@dataclasses.dataclass
class HybridSearchConfig:
    """Configuration for hybrid vector + BM25 search with optional reranking.

    Attributes:
        bm25_weight: Weight given to BM25 (keyword) scores.  Must be in
            ``[0.0, 1.0]``.  Default ``0.3``.
        vector_weight: Weight given to vector (semantic) scores.  Must be in
            ``[0.0, 1.0]``.  Defaults to ``1 - bm25_weight``.
        use_reranker: Whether to apply a cross-encoder reranker as a final
            step.  Default ``False``.
        reranker_model: Model ID for the cross-encoder reranker.  Only used
            when ``use_reranker=True``.  Default ``"cross-encoder/ms-marco-MiniLM-L-6-v2"``.
        top_k: Number of final results to return after reranking.  Default ``10``.

    Example::

        from syrin.knowledge import HybridSearchConfig

        cfg = HybridSearchConfig(bm25_weight=0.3, vector_weight=0.7, use_reranker=True)
    """

    bm25_weight: float = 0.3
    vector_weight: float = dataclasses.field(default=0.0)  # computed in __post_init__
    use_reranker: bool = False
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    top_k: int = 10

    def __post_init__(self) -> None:
        if self.vector_weight == 0.0 and self.bm25_weight != 0.0:
            # Auto-compute vector weight as complement
            object.__setattr__(self, "vector_weight", round(1.0 - self.bm25_weight, 10))
        total = round(self.bm25_weight + self.vector_weight, 10)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"bm25_weight ({self.bm25_weight}) + vector_weight ({self.vector_weight})"
                f" must sum to 1.0, got {total}"
            )


class CancellableIngestTask:
    """A handle for a running knowledge ingestion that can be cancelled.

    Pass this object to your ingestion coroutine and check
    :attr:`cancelled` at each iteration boundary to stop cleanly.

    Example::

        from syrin.knowledge import CancellableIngestTask

        task = CancellableIngestTask()

        async def ingest(docs, task):
            for doc in docs:
                if task.cancelled:
                    return
                await process(doc)

        asyncio.create_task(ingest(docs, task))
        ...
        task.cancel()   # stop at next boundary
    """

    def __init__(self) -> None:
        self._cancelled = False

    @property
    def cancelled(self) -> bool:
        """``True`` after :meth:`cancel` has been called."""
        return self._cancelled

    def cancel(self) -> None:
        """Request cancellation.  The ingestion coroutine will stop at its next checkpoint."""
        self._cancelled = True
