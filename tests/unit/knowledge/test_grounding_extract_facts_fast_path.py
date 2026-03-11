"""Tests for grounding extract_facts=False fast path (no LLM call)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from syrin.knowledge._chunker import Chunk
from syrin.knowledge._grounding import GroundingConfig, apply_grounding
from syrin.knowledge._store import SearchResult


def _make_chunk(content: str, doc_id: str = "test.md") -> Chunk:
    return Chunk(
        content=content,
        metadata={},
        document_id=doc_id,
        chunk_index=0,
        token_count=max(1, len(content) // 4),
    )


def _make_result(chunk: Chunk, score: float = 0.85, rank: int = 1) -> SearchResult:
    return SearchResult(chunk=chunk, score=score, rank=rank)


class TestGroundingExtractFactsFalse:
    """When extract_facts=False, skip LLM and return raw chunks immediately."""

    @pytest.mark.asyncio
    async def test_extract_facts_false_returns_raw_no_model_call(self) -> None:
        """No model is called when extract_facts=False."""
        cfg = GroundingConfig(extract_facts=False)
        c = _make_chunk("Authorized capital Rs. 3,00,000", doc_id="PAS-3.md")
        r = _make_result(c)
        out, facts = await apply_grounding(
            query="capital",
            results=[r],
            config=cfg,
            get_model=lambda: None,
        )
        assert "Authorized capital" in out or "3" in out
        assert facts == []
        # No model needed - get_model can return None

    @pytest.mark.asyncio
    async def test_extract_facts_false_uses_format_raw_results(self) -> None:
        """Output format matches _format_raw_results (rank, score, content)."""
        cfg = GroundingConfig(extract_facts=False)
        c = _make_chunk("Nexus Brightlearn Solutions", doc_id="SH-7.md")
        r = _make_result(c, score=0.91, rank=1)
        out, _ = await apply_grounding(
            query="company name",
            results=[r],
            config=cfg,
            get_model=lambda: MagicMock(),
        )
        assert "[1]" in out
        assert "0.91" in out
        assert "Nexus Brightlearn" in out
