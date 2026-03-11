"""Tests for grounding layer: GroundedFact, GroundingConfig, apply_grounding."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from syrin.enums import VerificationStatus
from syrin.knowledge._chunker import Chunk
from syrin.knowledge._grounding import (
    GroundedFact,
    GroundingConfig,
    _chunks_to_facts,
    _format_grounded_facts,
    _format_raw_results,
    apply_grounding,
)
from syrin.knowledge._store import SearchResult


def _make_chunk(
    content: str, doc_id: str = "test.pdf", idx: int = 0, page: int | None = None
) -> Chunk:
    meta: dict[str, str | int | float | bool | None | list[str]] = {}
    if page is not None:
        meta["page"] = page
    return Chunk(
        content=content,
        metadata=meta,
        document_id=doc_id,
        chunk_index=idx,
        token_count=max(1, len(content) // 4),
    )


def _make_result(chunk: Chunk, score: float = 0.85, rank: int = 1) -> SearchResult:
    return SearchResult(chunk=chunk, score=score, rank=rank)


class TestGroundedFact:
    """GroundedFact dataclass."""

    def test_create_minimal(self) -> None:
        f = GroundedFact(content="Capital is ₹50L", source="moa.pdf")
        assert f.content == "Capital is ₹50L"
        assert f.source == "moa.pdf"
        assert f.page is None
        assert f.confidence == 0.0
        assert f.verification == VerificationStatus.UNVERIFIED
        assert f.chunk_id is None
        assert f.metadata == {}

    def test_create_full(self) -> None:
        f = GroundedFact(
            content="Face value ₹10",
            source="moa.pdf",
            page=3,
            confidence=0.95,
            verification=VerificationStatus.VERIFIED,
            chunk_id="moa.pdf::2",
            metadata={"section": "capital"},
        )
        assert f.page == 3
        assert f.confidence == 0.95
        assert f.verification == VerificationStatus.VERIFIED
        assert f.chunk_id == "moa.pdf::2"
        assert f.metadata["section"] == "capital"


class TestGroundingConfig:
    """GroundingConfig validation."""

    def test_defaults(self) -> None:
        cfg = GroundingConfig()
        assert cfg.enabled is True
        assert cfg.extract_facts is True
        assert cfg.cite_sources is True
        assert cfg.verify_before_use is True
        assert cfg.confidence_threshold == 0.7
        assert cfg.max_facts == 15

    def test_confidence_threshold_invalid(self) -> None:
        with pytest.raises(ValueError, match="confidence_threshold"):
            GroundingConfig(confidence_threshold=-0.1)
        with pytest.raises(ValueError, match="confidence_threshold"):
            GroundingConfig(confidence_threshold=1.5)

    def test_max_facts_invalid(self) -> None:
        with pytest.raises(ValueError, match="max_facts"):
            GroundingConfig(max_facts=0)


class TestFormatRawResults:
    """_format_raw_results."""

    def test_empty(self) -> None:
        assert _format_raw_results([]) == "No relevant results found."

    def test_single(self) -> None:
        c = _make_chunk("Authorized capital is ₹50,00,000")
        r = _make_result(c)
        out = _format_raw_results([r])
        assert "[1]" in out
        assert "0.85" in out
        assert "Authorized capital" in out


class TestChunksToFacts:
    """_chunks_to_facts fallback."""

    def test_empty(self) -> None:
        assert _chunks_to_facts([]) == []

    def test_single_chunk(self) -> None:
        c = _make_chunk("Capital is ₹50L", doc_id="moa.pdf", page=3)
        r = _make_result(c)
        facts = _chunks_to_facts([r])
        assert len(facts) == 1
        assert facts[0].content == "Capital is ₹50L"
        assert facts[0].source == "moa.pdf"
        assert facts[0].page == 3
        assert facts[0].chunk_id == "moa.pdf::0"


class TestFormatGroundedFacts:
    """_format_grounded_facts."""

    def test_empty(self) -> None:
        cfg = GroundingConfig()
        out = _format_grounded_facts([], cfg)
        assert "No grounded facts" in out

    def test_filters_by_confidence(self) -> None:
        cfg = GroundingConfig(confidence_threshold=0.8)
        facts = [
            GroundedFact(
                "High conf", "a.pdf", confidence=0.9, verification=VerificationStatus.VERIFIED
            ),
            GroundedFact(
                "Low conf", "b.pdf", confidence=0.5, verification=VerificationStatus.VERIFIED
            ),
        ]
        out = _format_grounded_facts(facts, cfg)
        assert "High conf" in out
        assert "Low conf" not in out

    def test_cites_sources(self) -> None:
        cfg = GroundingConfig(cite_sources=True)
        facts = [
            GroundedFact(
                "Fact", "doc.pdf", page=5, confidence=0.9, verification=VerificationStatus.VERIFIED
            ),
        ]
        out = _format_grounded_facts(facts, cfg)
        assert "Source: doc.pdf" in out
        assert "Page 5" in out


class TestApplyGrounding:
    """apply_grounding integration."""

    @pytest.mark.asyncio
    async def test_empty_results(self) -> None:
        cfg = GroundingConfig()
        model = MagicMock()
        out, facts = await apply_grounding(
            query="capital?",
            results=[],
            config=cfg,
            get_model=lambda: model,
        )
        assert "No relevant results" in out
        assert facts == []

    @pytest.mark.asyncio
    async def test_fallback_on_extraction_failure(self) -> None:
        """When extraction returns invalid JSON, falls back to chunk-as-fact."""
        cfg = GroundingConfig(extract_facts=True, verify_before_use=False)
        model = MagicMock()
        model.acomplete = AsyncMock(return_value=MagicMock(content="not valid json {"))
        c = _make_chunk("Authorized capital is ₹50,00,000", doc_id="moa.pdf")
        r = _make_result(c)
        out, facts = await apply_grounding(
            query="capital?",
            results=[r],
            config=cfg,
            get_model=lambda: model,
        )
        assert "Authorized capital" in out or "50" in out
        assert len(facts) >= 1
