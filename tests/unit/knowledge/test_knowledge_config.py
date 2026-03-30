"""Knowledge configuration: flat chunk, grounding, and agentic field API.

Verifies:
- ChunkConfig/GroundingConfig/AgenticRAGConfig removed from public API
- Knowledge accepts flat chunk_*, grounding_*, agentic_* fields
- Internal config objects built correctly from flat fields
"""

from __future__ import annotations

import pytest
from tests.unit.knowledge.test_knowledge_orchestrator import _make_fake_embedding as _fake_embedding

from syrin.enums import KnowledgeBackend
from syrin.knowledge import Knowledge
from syrin.knowledge._chunker import ChunkStrategy


class TestChunkFlatFields:
    """Knowledge accepts flat chunk_* fields."""

    def test_chunk_size_default(self) -> None:
        k = Knowledge(
            sources=[Knowledge.Text("hello")],
            embedding=_fake_embedding()(),
            backend=KnowledgeBackend.MEMORY,
        )
        assert k._chunk_config.chunk_size == 512

    def test_chunk_size_custom(self) -> None:
        k = Knowledge(
            sources=[Knowledge.Text("hello")],
            embedding=_fake_embedding()(),
            backend=KnowledgeBackend.MEMORY,
            chunk_size=256,
        )
        assert k._chunk_config.chunk_size == 256

    def test_chunk_overlap_default(self) -> None:
        k = Knowledge(
            sources=[Knowledge.Text("hello")],
            embedding=_fake_embedding()(),
            backend=KnowledgeBackend.MEMORY,
        )
        assert k._chunk_config.chunk_overlap == 0

    def test_chunk_overlap_custom(self) -> None:
        k = Knowledge(
            sources=[Knowledge.Text("hello")],
            embedding=_fake_embedding()(),
            backend=KnowledgeBackend.MEMORY,
            chunk_size=512,
            chunk_overlap=64,
        )
        assert k._chunk_config.chunk_overlap == 64

    def test_chunk_strategy_default(self) -> None:
        k = Knowledge(
            sources=[Knowledge.Text("hello")],
            embedding=_fake_embedding()(),
            backend=KnowledgeBackend.MEMORY,
        )
        assert k._chunk_config.strategy == ChunkStrategy.AUTO

    def test_chunk_strategy_custom(self) -> None:
        k = Knowledge(
            sources=[Knowledge.Text("hello")],
            embedding=_fake_embedding()(),
            backend=KnowledgeBackend.MEMORY,
            chunk_strategy=ChunkStrategy.MARKDOWN,
        )
        assert k._chunk_config.strategy == ChunkStrategy.MARKDOWN

    def test_chunk_config_param_removed(self) -> None:
        """chunk_config kwarg is no longer accepted."""
        from syrin.knowledge._chunker import ChunkConfig

        with pytest.raises(TypeError):
            Knowledge(  # type: ignore[call-arg]
                sources=[Knowledge.Text("hello")],
                embedding=_fake_embedding()(),
                backend=KnowledgeBackend.MEMORY,
                chunk_config=ChunkConfig(),
            )


class TestGroundingFlatFields:
    """Knowledge accepts flat grounding_* fields."""

    def test_grounding_disabled_by_default(self) -> None:
        k = Knowledge(
            sources=[Knowledge.Text("hello")],
            embedding=_fake_embedding()(),
            backend=KnowledgeBackend.MEMORY,
        )
        assert k._grounding_config is None

    def test_grounding_enabled_flag(self) -> None:
        k = Knowledge(
            sources=[Knowledge.Text("hello")],
            embedding=_fake_embedding()(),
            backend=KnowledgeBackend.MEMORY,
            grounding_enabled=True,
        )
        assert k._grounding_config is not None
        assert k._grounding_config.enabled is True

    def test_grounding_confidence(self) -> None:
        k = Knowledge(
            sources=[Knowledge.Text("hello")],
            embedding=_fake_embedding()(),
            backend=KnowledgeBackend.MEMORY,
            grounding_enabled=True,
            grounding_confidence=0.85,
        )
        assert k._grounding_config is not None
        assert k._grounding_config.confidence_threshold == 0.85

    def test_grounding_extract_facts(self) -> None:
        k = Knowledge(
            sources=[Knowledge.Text("hello")],
            embedding=_fake_embedding()(),
            backend=KnowledgeBackend.MEMORY,
            grounding_enabled=True,
            grounding_extract_facts=False,
        )
        assert k._grounding_config is not None
        assert k._grounding_config.extract_facts is False

    def test_grounding_cite_sources(self) -> None:
        k = Knowledge(
            sources=[Knowledge.Text("hello")],
            embedding=_fake_embedding()(),
            backend=KnowledgeBackend.MEMORY,
            grounding_enabled=True,
            grounding_cite_sources=False,
        )
        assert k._grounding_config is not None
        assert k._grounding_config.cite_sources is False

    def test_grounding_verify(self) -> None:
        k = Knowledge(
            sources=[Knowledge.Text("hello")],
            embedding=_fake_embedding()(),
            backend=KnowledgeBackend.MEMORY,
            grounding_enabled=True,
            grounding_verify=False,
        )
        assert k._grounding_config is not None
        assert k._grounding_config.verify_before_use is False

    def test_grounding_max_facts(self) -> None:
        k = Knowledge(
            sources=[Knowledge.Text("hello")],
            embedding=_fake_embedding()(),
            backend=KnowledgeBackend.MEMORY,
            grounding_enabled=True,
            grounding_max_facts=5,
        )
        assert k._grounding_config is not None
        assert k._grounding_config.max_facts == 5

    def test_grounding_param_removed(self) -> None:
        """grounding= kwarg (old GroundingConfig) is no longer accepted."""
        from syrin.knowledge._grounding import GroundingConfig

        with pytest.raises(TypeError):
            Knowledge(  # type: ignore[call-arg]
                sources=[Knowledge.Text("hello")],
                embedding=_fake_embedding()(),
                backend=KnowledgeBackend.MEMORY,
                grounding=GroundingConfig(),
            )


class TestAgenticFlatFields:
    """Knowledge accepts flat agentic_* fields."""

    def test_agentic_disabled_by_default(self) -> None:
        k = Knowledge(
            sources=[Knowledge.Text("hello")],
            embedding=_fake_embedding()(),
            backend=KnowledgeBackend.MEMORY,
        )
        assert k._agentic is False
        assert k._agentic_config is None

    def test_agentic_enabled(self) -> None:
        k = Knowledge(
            sources=[Knowledge.Text("hello")],
            embedding=_fake_embedding()(),
            backend=KnowledgeBackend.MEMORY,
            agentic=True,
        )
        assert k._agentic is True
        assert k._agentic_config is not None

    def test_agentic_max_iterations(self) -> None:
        k = Knowledge(
            sources=[Knowledge.Text("hello")],
            embedding=_fake_embedding()(),
            backend=KnowledgeBackend.MEMORY,
            agentic=True,
            agentic_max_iterations=5,
        )
        assert k._agentic_config is not None
        assert k._agentic_config.max_search_iterations == 5

    def test_agentic_decompose(self) -> None:
        k = Knowledge(
            sources=[Knowledge.Text("hello")],
            embedding=_fake_embedding()(),
            backend=KnowledgeBackend.MEMORY,
            agentic=True,
            agentic_decompose=False,
        )
        assert k._agentic_config is not None
        assert k._agentic_config.decompose_complex is False

    def test_agentic_grade_results(self) -> None:
        k = Knowledge(
            sources=[Knowledge.Text("hello")],
            embedding=_fake_embedding()(),
            backend=KnowledgeBackend.MEMORY,
            agentic=True,
            agentic_grade_results=False,
        )
        assert k._agentic_config is not None
        assert k._agentic_config.grade_results is False

    def test_agentic_relevance_threshold(self) -> None:
        k = Knowledge(
            sources=[Knowledge.Text("hello")],
            embedding=_fake_embedding()(),
            backend=KnowledgeBackend.MEMORY,
            agentic=True,
            agentic_relevance_threshold=0.8,
        )
        assert k._agentic_config is not None
        assert k._agentic_config.relevance_threshold == 0.8

    def test_agentic_web_fallback(self) -> None:
        k = Knowledge(
            sources=[Knowledge.Text("hello")],
            embedding=_fake_embedding()(),
            backend=KnowledgeBackend.MEMORY,
            agentic=True,
            agentic_web_fallback=True,
        )
        assert k._agentic_config is not None
        assert k._agentic_config.web_fallback is True

    def test_agentic_config_param_removed(self) -> None:
        """agentic_config= kwarg is no longer accepted."""
        from syrin.knowledge._agentic import AgenticRAGConfig

        with pytest.raises(TypeError):
            Knowledge(  # type: ignore[call-arg]
                sources=[Knowledge.Text("hello")],
                embedding=_fake_embedding()(),
                backend=KnowledgeBackend.MEMORY,
                agentic_config=AgenticRAGConfig(),
            )


class TestPublicAPIRemoval:
    """ChunkConfig, GroundingConfig, AgenticRAGConfig removed from public exports."""

    def test_chunk_config_not_in_syrin_root(self) -> None:
        import syrin

        assert not hasattr(syrin, "ChunkConfig")

    def test_grounding_config_not_in_syrin_root(self) -> None:
        import syrin

        assert not hasattr(syrin, "GroundingConfig")

    def test_agentic_rag_config_not_in_syrin_root(self) -> None:
        import syrin

        assert not hasattr(syrin, "AgenticRAGConfig")

    def test_chunk_config_not_in_knowledge_module(self) -> None:
        import syrin.knowledge as km

        assert not hasattr(km, "ChunkConfig")

    def test_grounding_config_not_in_knowledge_module(self) -> None:
        import syrin.knowledge as km

        assert not hasattr(km, "GroundingConfig")

    def test_agentic_rag_config_not_in_knowledge_module(self) -> None:
        import syrin.knowledge as km

        assert not hasattr(km, "AgenticRAGConfig")
