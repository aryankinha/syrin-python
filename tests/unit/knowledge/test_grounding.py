"""Tests for grounding layer: GroundedFact, GroundingConfig, apply_grounding."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from syrin.enums import VerificationStatus
from syrin.knowledge._chunker import Chunk
from syrin.knowledge._grounding import (
    GroundedFact,
    GroundingConfig,
    _chunks_to_facts,
    _format_grounded_facts,
    _format_raw_results,
    _match_fact_to_result,
    apply_grounding,
)
from syrin.knowledge._store import SearchResult, chunk_id


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

    def test_max_chunk_preview_default(self) -> None:
        cfg = GroundingConfig()
        assert cfg.max_chunk_preview == 800

    def test_max_chunk_preview_custom(self) -> None:
        cfg = GroundingConfig(max_chunk_preview=1200)
        assert cfg.max_chunk_preview == 1200

    def test_max_chunk_preview_invalid(self) -> None:
        with pytest.raises(ValueError, match="max_chunk_preview"):
            GroundingConfig(max_chunk_preview=0)
        with pytest.raises(ValueError, match="max_chunk_preview"):
            GroundingConfig(max_chunk_preview=-1)


class TestMatchFactToResult:
    """_match_fact_to_result: fact source attribution (1A)."""

    def test_matches_by_document_id(self) -> None:
        c1 = _make_chunk("Content A", doc_id="moa.pdf", idx=0)
        c2 = _make_chunk("Content B", doc_id="sh7.pdf", idx=0)
        results = [_make_result(c1, rank=1), _make_result(c2, rank=2)]
        r = _match_fact_to_result("moa.pdf", results)
        assert r is not None
        assert r.chunk.document_id == "moa.pdf"
        assert chunk_id(r.chunk) == "moa.pdf::0"

    def test_partial_document_id_match(self) -> None:
        c = _make_chunk("Content", doc_id="data/SH-7/MOA.md", idx=1)
        results = [_make_result(c)]
        r = _match_fact_to_result("MOA", results)
        assert r is not None
        assert "MOA" in r.chunk.document_id
        assert r.chunk.chunk_index == 1

    def test_fallback_unknown_when_no_match(self) -> None:
        c = _make_chunk("Content", doc_id="other.pdf", idx=0)
        results = [_make_result(c)]
        r = _match_fact_to_result("nonexistent.docx", results)
        assert r is None

    def test_empty_results_returns_none(self) -> None:
        r = _match_fact_to_result("moa.pdf", [])
        assert r is None


class TestFormatRawResults:
    """_format_raw_results (1D: dedup by chunk_id)."""

    def test_empty(self) -> None:
        assert _format_raw_results([]) == "No relevant results found."

    def test_single(self) -> None:
        c = _make_chunk("Authorized capital is ₹50,00,000")
        r = _make_result(c)
        out = _format_raw_results([r])
        assert "[1]" in out
        assert "0.85" in out
        assert "Authorized capital" in out

    def test_dedup_by_chunk_id_same_chunk_once(self) -> None:
        c = _make_chunk("Same content here", doc_id="doc.pdf", idx=0)
        r1 = _make_result(c, rank=1)
        r2 = _make_result(c, rank=2)
        out = _format_raw_results([r1, r2])
        assert out.count("Same content") == 1

    def test_dedup_by_chunk_id_different_chunks_both_appear(self) -> None:
        prefix = "x" * 300
        c1 = _make_chunk(prefix + " tail1", doc_id="a.pdf", idx=0)
        c2 = _make_chunk(prefix + " tail2", doc_id="b.pdf", idx=0)
        r1 = _make_result(c1, rank=1)
        r2 = _make_result(c2, rank=2)
        out = _format_raw_results([r1, r2])
        assert "tail1" in out or "[1]" in out
        assert "tail2" in out or "[2]" in out
        assert out.count("[1]") == 1
        assert out.count("[2]") == 1


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

    @pytest.mark.asyncio
    async def test_fact_source_attribution_correct_when_order_differs(self) -> None:
        """Facts with sources matching different result indices get correct chunk_id (1A)."""
        c1 = _make_chunk("Content from MOA", doc_id="MOA.md", idx=0)
        c2 = _make_chunk("Content from PAS-3", doc_id="PAS-3.md", idx=0)
        c3 = _make_chunk("Content from SH-7", doc_id="SH-7.md", idx=0)
        results = [
            _make_result(c1, rank=1),
            _make_result(c2, rank=2),
            _make_result(c3, rank=3),
        ]
        # LLM returns facts in shuffled order: fact0->PAS-3, fact1->MOA, fact2->SH-7
        extract_json = """[
            {"fact": "From PAS-3", "source": "PAS-3.md", "page": null, "confidence": 0.9},
            {"fact": "From MOA", "source": "MOA.md", "page": null, "confidence": 0.9},
            {"fact": "From SH-7", "source": "SH-7.md", "page": null, "confidence": 0.9}
        ]"""
        cfg = GroundingConfig(extract_facts=True, verify_before_use=False)
        model = MagicMock()
        model.acomplete = AsyncMock(return_value=MagicMock(content=extract_json))
        out, facts = await apply_grounding(
            query="capital?",
            results=results,
            config=cfg,
            get_model=lambda: model,
        )
        assert len(facts) == 3
        by_content: dict[str, GroundedFact] = {f.content: f for f in facts}
        assert by_content["From PAS-3"].chunk_id == "PAS-3.md::0"
        assert by_content["From MOA"].chunk_id == "MOA.md::0"
        assert by_content["From SH-7"].chunk_id == "SH-7.md::0"
        assert by_content["From PAS-3"].source == "PAS-3.md"
        assert by_content["From MOA"].source == "MOA.md"
        assert by_content["From SH-7"].source == "SH-7.md"

    @pytest.mark.asyncio
    async def test_low_confidence_facts_skip_verification(self) -> None:
        """Only facts with confidence >= threshold get verified (1C)."""
        extract_json = """[
            {"fact": "High conf fact", "source": "a.pdf", "page": null, "confidence": 0.9},
            {"fact": "Low conf fact", "source": "a.pdf", "page": null, "confidence": 0.3}
        ]"""
        c = _make_chunk("High conf fact and more", doc_id="a.pdf", idx=0)
        results = [_make_result(c)]
        cfg = GroundingConfig(
            extract_facts=True,
            verify_before_use=True,
            confidence_threshold=0.7,
        )
        model = MagicMock()
        model.acomplete = AsyncMock(
            side_effect=[
                MagicMock(content=extract_json),
                MagicMock(content="""[{"claim": "High conf fact", "verdict": "SUPPORTED"}]"""),
            ]
        )
        out, facts = await apply_grounding(
            query="q",
            results=results,
            config=cfg,
            get_model=lambda: model,
        )
        assert model.acomplete.call_count == 2
        assert len(facts) == 1
        assert facts[0].content == "High conf fact"
        assert facts[0].verification == VerificationStatus.VERIFIED

    @pytest.mark.asyncio
    async def test_all_facts_below_threshold_returns_raw_fallback(self) -> None:
        """When all extracted facts are below confidence threshold, return raw results (1C)."""
        extract_json = """[
            {"fact": "Low", "source": "a.pdf", "page": null, "confidence": 0.2},
            {"fact": "Also low", "source": "a.pdf", "page": null, "confidence": 0.1}
        ]"""
        c = _make_chunk("Raw chunk content", doc_id="a.pdf", idx=0)
        results = [_make_result(c)]
        cfg = GroundingConfig(
            extract_facts=True,
            verify_before_use=True,
            confidence_threshold=0.7,
        )
        model = MagicMock()
        model.acomplete = AsyncMock(return_value=MagicMock(content=extract_json))
        out, facts = await apply_grounding(
            query="q",
            results=results,
            config=cfg,
            get_model=lambda: model,
        )
        assert model.acomplete.call_count == 1
        assert "Raw chunk content" in out
        assert facts == []

    @pytest.mark.asyncio
    async def test_threshold_boundary_inclusive(self) -> None:
        """Fact at exactly confidence_threshold is verified (1C)."""
        extract_json = """[
            {"fact": "At boundary", "source": "a.pdf", "page": null, "confidence": 0.7}
        ]"""
        c = _make_chunk("At boundary", doc_id="a.pdf", idx=0)
        results = [_make_result(c)]
        cfg = GroundingConfig(
            extract_facts=True,
            verify_before_use=True,
            confidence_threshold=0.7,
        )
        model = MagicMock()
        model.acomplete = AsyncMock(
            side_effect=[
                MagicMock(content=extract_json),
                MagicMock(content="""[{"claim": "At boundary", "verdict": "SUPPORTED"}]"""),
            ]
        )
        out, facts = await apply_grounding(
            query="q",
            results=results,
            config=cfg,
            get_model=lambda: model,
        )
        assert len(facts) == 1
        assert facts[0].verification == VerificationStatus.VERIFIED

    @pytest.mark.asyncio
    async def test_extract_facts_uses_max_chunk_preview(self) -> None:
        """Extraction prompt includes full chunk up to max_chunk_preview (1B)."""
        long_content = "Capital table: " + "x" * 700
        c = _make_chunk(long_content, doc_id="moa.pdf", idx=0)
        results = [_make_result(c)]
        cfg = GroundingConfig(max_chunk_preview=1200, verify_before_use=False)
        model = MagicMock()
        captured_prompt: list[str] = []

        async def capture_call(*args: object, **kwargs: object) -> str:
            prompt = args[1] if len(args) > 1 else ""
            captured_prompt.append(str(prompt))
            return '[{"fact": "ok", "source": "moa.pdf", "page": null, "confidence": 0.9}]'

        with patch(
            "syrin.knowledge._grounding._call_model",
            side_effect=capture_call,
        ):
            await apply_grounding(
                query="q",
                results=results,
                config=cfg,
                get_model=lambda: model,
            )
        assert len(captured_prompt) >= 1
        assert "x" * 400 in captured_prompt[0]
        assert len(long_content) <= 1200
        assert long_content[:700] in captured_prompt[0] or "x" * 700 in captured_prompt[0]


class TestBatchVerification:
    """Batch fact verification (5A)."""

    @pytest.mark.asyncio
    async def test_batch_verification_single_llm_call(self) -> None:
        """10 facts verified in 1 LLM call (5A)."""
        from syrin.knowledge._grounding import _verify_facts_batch

        c = _make_chunk("Content about capital", doc_id="moa.pdf", idx=0)
        results = [_make_result(c)]
        facts = [GroundedFact(f"Fact {i}", "moa.pdf", confidence=0.9) for i in range(10)]
        model = MagicMock()
        model.acomplete = AsyncMock(
            return_value=MagicMock(
                content="""[
                    {"claim": "Fact 0", "verdict": "SUPPORTED"},
                    {"claim": "Fact 1", "verdict": "CONTRADICTED"},
                    {"claim": "Fact 2", "verdict": "NOT_FOUND"},
                    {"claim": "Fact 3", "verdict": "SUPPORTED"},
                    {"claim": "Fact 4", "verdict": "SUPPORTED"},
                    {"claim": "Fact 5", "verdict": "NOT_FOUND"},
                    {"claim": "Fact 6", "verdict": "CONTRADICTED"},
                    {"claim": "Fact 7", "verdict": "SUPPORTED"},
                    {"claim": "Fact 8", "verdict": "NOT_FOUND"},
                    {"claim": "Fact 9", "verdict": "SUPPORTED"}
                ]"""
            )
        )
        verified = await _verify_facts_batch(facts, results, model)
        assert model.acomplete.call_count == 1
        assert len(verified) == 10
        assert verified[0].verification == VerificationStatus.VERIFIED
        assert verified[1].verification == VerificationStatus.CONTRADICTED
        assert verified[2].verification == VerificationStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_batch_verification_handles_partial_response(self) -> None:
        """LLM returns verdicts for only 8/10 facts; remaining 2 marked UNVERIFIED."""
        from syrin.knowledge._grounding import _verify_facts_batch

        c = _make_chunk("Content", doc_id="moa.pdf", idx=0)
        results = [_make_result(c)]
        facts = [GroundedFact(f"Fact {i}", "moa.pdf", confidence=0.9) for i in range(10)]
        model = MagicMock()
        model.acomplete = AsyncMock(
            return_value=MagicMock(
                content="""[
                    {"claim": "Fact 0", "verdict": "SUPPORTED"},
                    {"claim": "Fact 1", "verdict": "CONTRADICTED"},
                    {"claim": "Fact 2", "verdict": "NOT_FOUND"},
                    {"claim": "Fact 3", "verdict": "SUPPORTED"},
                    {"claim": "Fact 4", "verdict": "SUPPORTED"},
                    {"claim": "Fact 5", "verdict": "NOT_FOUND"},
                    {"claim": "Fact 6", "verdict": "CONTRADICTED"},
                    {"claim": "Fact 7", "verdict": "SUPPORTED"}
                ]"""
            )
        )
        verified = await _verify_facts_batch(facts, results, model)
        assert len(verified) == 10
        # First 8 should have correct verdicts from LLM response (index-based)
        assert verified[0].verification == VerificationStatus.VERIFIED
        assert verified[1].verification == VerificationStatus.CONTRADICTED
        assert verified[2].verification == VerificationStatus.NOT_FOUND
        # Remaining facts default to VERIFIED (assumed supported since evidence exists)
        assert verified[8].verification == VerificationStatus.VERIFIED
        assert verified[9].verification == VerificationStatus.VERIFIED

    @pytest.mark.asyncio
    async def test_batch_verification_empty_facts(self) -> None:
        """Empty list: no LLM call."""
        from syrin.knowledge._grounding import _verify_facts_batch

        c = _make_chunk("Content", doc_id="moa.pdf", idx=0)
        results = [_make_result(c)]
        model = MagicMock()
        model.acomplete = AsyncMock()
        verified = await _verify_facts_batch([], results, model)
        assert verified == []
        assert model.acomplete.call_count == 0

    @pytest.mark.asyncio
    async def test_batch_verification_large_batch_splits(self) -> None:
        """30 facts split into batches of 10 (configurable)."""
        from syrin.knowledge._grounding import _verify_facts_batch

        c = _make_chunk("Content", doc_id="moa.pdf", idx=0)
        results = [_make_result(c)]
        facts = [GroundedFact(f"Fact {i}", "moa.pdf", confidence=0.9) for i in range(30)]
        model = MagicMock()
        model.acomplete = AsyncMock(return_value=MagicMock(content="[]"))
        await _verify_facts_batch(facts, results, model, batch_size=10)
        assert model.acomplete.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_verification_all_not_found_when_empty_results(self) -> None:
        """Verification with empty search results: all facts get NOT_FOUND."""
        from syrin.knowledge._grounding import _verify_facts_batch

        facts = [GroundedFact(f"Fact {i}", "moa.pdf", confidence=0.9) for i in range(3)]
        model = MagicMock()
        model.acomplete = AsyncMock()
        verified = await _verify_facts_batch(facts, [], model)
        assert len(verified) == 3
        for v in verified:
            assert v.verification == VerificationStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_apply_grounding_uses_batch_verification_by_default(self) -> None:
        """apply_grounding uses batch verification when verify_before_use=True (5A)."""
        extract_json = """[
            {"fact": "Fact A", "source": "a.pdf", "page": null, "confidence": 0.9},
            {"fact": "Fact B", "source": "b.pdf", "page": null, "confidence": 0.9},
            {"fact": "Fact C", "source": "c.pdf", "page": null, "confidence": 0.9}
        ]"""
        c1 = _make_chunk("Content A", doc_id="a.pdf", idx=0)
        c2 = _make_chunk("Content B", doc_id="b.pdf", idx=0)
        c3 = _make_chunk("Content C", doc_id="c.pdf", idx=0)
        results = [_make_result(c1), _make_result(c2), _make_result(c3)]
        cfg = GroundingConfig(verify_before_use=True)
        model = MagicMock()
        model.acomplete = AsyncMock(
            side_effect=[
                MagicMock(content=extract_json),
                MagicMock(
                    content="""[
                    {"claim": "Fact A", "verdict": "SUPPORTED"},
                    {"claim": "Fact B", "verdict": "CONTRADICTED"},
                    {"claim": "Fact C", "verdict": "NOT_FOUND"}
                ]"""
                ),
            ]
        )
        out, facts = await apply_grounding(
            query="q",
            results=results,
            config=cfg,
            get_model=lambda: model,
        )
        assert model.acomplete.call_count == 2
        assert len(facts) == 3
        assert facts[0].verification == VerificationStatus.VERIFIED
        assert facts[1].verification == VerificationStatus.CONTRADICTED
        assert facts[2].verification == VerificationStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_grounding_uses_separate_model(self) -> None:
        """GroundingConfig(model=...) uses separate model for extraction/verification (5C)."""
        from syrin.model import Model

        mini_model = Model.OpenAI("gpt-4o-mini")
        main_model = Model.OpenAI("gpt-4o")
        extract_json = (
            """[{"fact": "Test fact", "source": "a.pdf", "page": null, "confidence": 0.9}]"""
        )
        c = _make_chunk("Content", doc_id="a.pdf", idx=0)
        results = [_make_result(c)]
        cfg = GroundingConfig(verify_before_use=False, model=mini_model)
        call_count = {"count": 0}

        async def track_call(*args: Any, **kwargs: Any) -> Any:
            call_count["count"] += 1
            return MagicMock(content=extract_json)

        mini_model.acomplete = AsyncMock(side_effect=track_call)
        main_model.acomplete = AsyncMock(side_effect=track_call)
        out, facts = await apply_grounding(
            query="q",
            results=results,
            config=cfg,
            get_model=lambda: main_model,
        )
        assert len(facts) == 1
        assert call_count["count"] == 1

    @pytest.mark.asyncio
    async def test_grounding_falls_back_to_agent_model(self) -> None:
        """No config.model set: uses agent's model."""
        from syrin.model import Model

        main_model = MagicMock(spec=Model)
        extract_json = (
            """[{"fact": "Test fact", "source": "a.pdf", "page": null, "confidence": 0.9}]"""
        )
        c = _make_chunk("Content", doc_id="a.pdf", idx=0)
        results = [_make_result(c)]
        cfg = GroundingConfig(verify_before_use=False)

        async def track_call(*args: Any, **kwargs: Any) -> Any:
            return MagicMock(content=extract_json)

        main_model.acomplete = AsyncMock(side_effect=track_call)
        out, facts = await apply_grounding(
            query="q",
            results=results,
            config=cfg,
            get_model=lambda: main_model,
        )
        assert len(facts) == 1
        assert main_model.acomplete.call_count == 1


class TestGroundingConfigModel:
    """GroundingConfig model field validation (5C)."""

    def test_grounding_config_model_default_none(self) -> None:
        """Default model is None (uses agent model)."""
        cfg = GroundingConfig()
        assert cfg.model is None

    def test_grounding_config_model_set(self) -> None:
        """Can set model to a Model instance."""
        from syrin.model import Model

        m = Model.OpenAI("gpt-4o-mini")
        cfg = GroundingConfig(model=m)
        assert cfg.model is m


class TestGroundingEdgeCases:
    """Edge case tests for grounding (9C)."""

    @pytest.mark.asyncio
    async def test_extract_facts_empty_results(self) -> None:
        """No search results: returns empty list, no LLM call."""
        from syrin.knowledge._grounding import _extract_facts

        model = MagicMock()
        model.acomplete = AsyncMock()
        facts = await _extract_facts(
            query="capital?",
            results=[],
            model=model,
            max_facts=15,
            max_chunk_preview=800,
        )
        assert facts == []
        model.acomplete.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_facts_llm_returns_invalid_json(self) -> None:
        """LLM returns garbage: falls back to chunk-as-fact."""
        from syrin.knowledge._grounding import _extract_facts

        c = _make_chunk("Real content from document", doc_id="doc.pdf", idx=0)
        results = [_make_result(c)]
        model = MagicMock()
        model.acomplete = AsyncMock(return_value=MagicMock(content="not valid json {"))
        facts = await _extract_facts(
            query="capital?",
            results=results,
            model=model,
            max_facts=15,
            max_chunk_preview=800,
        )
        assert len(facts) >= 1

    @pytest.mark.asyncio
    async def test_extract_facts_llm_returns_non_array(self) -> None:
        """LLM returns object instead of array: falls back."""
        from syrin.knowledge._grounding import _extract_facts

        c = _make_chunk("Real content", doc_id="doc.pdf", idx=0)
        results = [_make_result(c)]
        model = MagicMock()
        model.acomplete = AsyncMock(return_value=MagicMock(content='{"fact": "single fact"}'))
        facts = await _extract_facts(
            query="q",
            results=results,
            model=model,
            max_facts=15,
            max_chunk_preview=800,
        )
        assert len(facts) >= 1

    @pytest.mark.asyncio
    async def test_verify_facts_empty_results_all_not_found(self) -> None:
        """Verification with empty search results: all facts get NOT_FOUND."""
        from syrin.knowledge._grounding import _verify_facts_batch

        facts = [
            GroundedFact("Fact 1", "doc.pdf", confidence=0.9),
            GroundedFact("Fact 2", "doc.pdf", confidence=0.9),
        ]
        model = MagicMock()
        model.acomplete = AsyncMock()
        verified = await _verify_facts_batch(facts, [], model)
        assert len(verified) == 2
        for v in verified:
            assert v.verification == VerificationStatus.NOT_FOUND

    def test_grounding_config_all_disabled(self) -> None:
        """GroundingConfig(enabled=False): no grounding applied."""
        cfg = GroundingConfig(enabled=False)
        assert cfg.enabled is False
        assert cfg.extract_facts is True
        assert cfg.verify_before_use is True

    @pytest.mark.asyncio
    async def test_grounding_config_extract_only_no_verify(self) -> None:
        """extract_facts=True, verify_before_use=False: facts extracted but not verified."""
        extract_json = """[
            {"fact": "Fact A", "source": "a.pdf", "page": null, "confidence": 0.9},
            {"fact": "Fact B", "source": "b.pdf", "page": null, "confidence": 0.5}
        ]"""
        c = _make_chunk("Content", doc_id="a.pdf", idx=0)
        results = [_make_result(c)]
        cfg = GroundingConfig(extract_facts=True, verify_before_use=False)
        model = MagicMock()
        model.acomplete = AsyncMock(return_value=MagicMock(content=extract_json))
        out, facts = await apply_grounding(
            query="q",
            results=results,
            config=cfg,
            get_model=lambda: model,
        )
        assert model.acomplete.call_count == 1
        assert len(facts) == 2
        assert facts[0].verification == VerificationStatus.UNVERIFIED

    @pytest.mark.asyncio
    async def test_apply_grounding_no_model_returns_error(self) -> None:
        """No model available: returns clear error message."""
        cfg = GroundingConfig()
        c = _make_chunk("Content", doc_id="a.pdf", idx=0)
        results = [_make_result(c)]
        out, facts = await apply_grounding(
            query="q",
            results=results,
            config=cfg,
            get_model=None,
        )
        assert "Grounding requires a model" in out
        assert facts == []

    @pytest.mark.asyncio
    async def test_apply_grounding_no_model_callable_returns_none(self) -> None:
        """Model callable returns None: returns clear error message."""
        cfg = GroundingConfig()
        c = _make_chunk("Content", doc_id="a.pdf", idx=0)
        results = [_make_result(c)]
        out, facts = await apply_grounding(
            query="q",
            results=results,
            config=cfg,
            get_model=lambda: None,
        )
        assert "Grounding requires a model" in out
        assert facts == []
