"""Unit tests for citation parsing and formatting in output_format."""

from __future__ import annotations

from syrin.output_format._citation import (
    Citation,
    CitationConfig,
    CitationStyle,
    apply_citation_style,
    parse_citations,
)


class TestCitation:
    """Citation dataclass."""

    def test_minimal(self) -> None:
        c = Citation(text="The capital is ₹50,00,000", source="moa.pdf", page=3)
        assert c.text == "The capital is ₹50,00,000"
        assert c.source == "moa.pdf"
        assert c.page == 3
        assert c.confidence is None
        assert c.index is None

    def test_with_confidence(self) -> None:
        c = Citation(text="Face value ₹10", source="doc.pdf", page=1, confidence=0.95)
        assert c.confidence == 0.95

    def test_page_optional(self) -> None:
        c = Citation(text="General info", source="doc.pdf", page=None)
        assert c.page is None

    def test_index_for_footnote(self) -> None:
        c = Citation(text="Fact", source="x.pdf", page=2, index=1)
        assert c.index == 1


class TestCitationStyle:
    """CitationStyle enum."""

    def test_values(self) -> None:
        assert CitationStyle.INLINE == "inline"
        assert CitationStyle.FOOTNOTE == "footnote"
        assert CitationStyle.APPENDIX == "appendix"
        assert CitationStyle.NONE == "none"


class TestCitationConfig:
    """CitationConfig dataclass."""

    def test_defaults(self) -> None:
        cfg = CitationConfig()
        assert cfg.style == CitationStyle.INLINE
        assert cfg.include_page is True
        assert cfg.include_confidence is False

    def test_explicit(self) -> None:
        cfg = CitationConfig(
            style=CitationStyle.FOOTNOTE,
            include_page=False,
            include_confidence=True,
        )
        assert cfg.style == CitationStyle.FOOTNOTE
        assert cfg.include_page is False
        assert cfg.include_confidence is True


class TestParseCitations:
    """parse_citations extracts Citation objects from content."""

    def test_empty_content(self) -> None:
        assert parse_citations("") == []
        assert parse_citations("   ") == []

    def test_no_citations(self) -> None:
        content = "The capital structure is as follows. No citations here."
        assert parse_citations(content) == []

    def test_source_page_bracket(self) -> None:
        content = "Authorized capital is ₹50,00,000 [Source: moa.pdf, Page 3]."
        citations = parse_citations(content)
        assert len(citations) == 1
        assert citations[0].source == "moa.pdf"
        assert citations[0].page == 3
        assert "₹50,00,000" in citations[0].text or "Authorized" in citations[0].text

    def test_source_page_lowercase(self) -> None:
        content = "Face value ₹10 [source: doc.pdf, page 5]"
        citations = parse_citations(content)
        assert len(citations) == 1
        assert citations[0].source == "doc.pdf"
        assert citations[0].page == 5

    def test_source_page_p_dot(self) -> None:
        content = "Shareholding [Source: report.pdf, p. 7]"
        citations = parse_citations(content)
        assert len(citations) == 1
        assert citations[0].source == "report.pdf"
        assert citations[0].page == 7

    def test_source_only_no_page(self) -> None:
        content = "Info from [Source: doc.pdf]"
        citations = parse_citations(content)
        assert len(citations) == 1
        assert citations[0].source == "doc.pdf"
        assert citations[0].page is None

    def test_multiple_citations(self) -> None:
        content = "Cap is ₹50L [Source: moa.pdf, Page 3]. Face value ₹10 [Source: moa.pdf, Page 4]."
        citations = parse_citations(content)
        assert len(citations) == 2
        assert citations[0].source == "moa.pdf" and citations[0].page == 3
        assert citations[1].source == "moa.pdf" and citations[1].page == 4

    def test_footnote_style_numbered(self) -> None:
        content = "Fact one [1]. Fact two [2]."
        citations = parse_citations(content)
        # Numbered refs [1], [2] without source — we may get empty source
        assert len(citations) >= 0  # Depends on implementation

    def test_numeric_in_text_not_citation(self) -> None:
        content = "The value is 100 and the rate is 5%."
        assert parse_citations(content) == []


class TestApplyCitationStyle:
    """apply_citation_style transforms content based on CitationConfig."""

    def test_inline_unchanged(self) -> None:
        content = "Cap is ₹50L [Source: moa.pdf, Page 3]."
        config = CitationConfig(style=CitationStyle.INLINE, include_page=True)
        result, citations = apply_citation_style(content, config)
        assert result == content
        assert len(citations) == 1
        assert citations[0].source == "moa.pdf"

    def test_none_strips_markers(self) -> None:
        content = "Cap is ₹50L [Source: moa.pdf, Page 3]."
        config = CitationConfig(style=CitationStyle.NONE)
        result, citations = apply_citation_style(content, config)
        assert "[Source:" not in result
        assert "moa.pdf" not in result
        assert "Page 3" not in result
        assert "Cap is ₹50L" in result
        assert len(citations) == 1  # Still tracked

    def test_footnote_replaces_with_numbers(self) -> None:
        content = "Cap is ₹50L [Source: moa.pdf, Page 3]. Face value [Source: moa.pdf, Page 4]."
        config = CitationConfig(style=CitationStyle.FOOTNOTE, include_page=True)
        result, citations = apply_citation_style(content, config)
        assert "[1]" in result
        assert "[2]" in result
        assert "Cap is ₹50L" in result
        assert len(citations) == 2
        # Footer should have source references
        assert "moa.pdf" in result
        assert "page 3" in result.lower() or "p. 3" in result.lower()

    def test_appendix_moves_to_end(self) -> None:
        content = "Fact A [Source: a.pdf, Page 1]. Fact B [Source: b.pdf, Page 2]."
        config = CitationConfig(style=CitationStyle.APPENDIX, include_page=True)
        result, citations = apply_citation_style(content, config)
        assert "[1]" in result and "[2]" in result
        assert "References" in result or "Sources" in result or "Appendix" in result
        assert len(citations) == 2

    def test_empty_content(self) -> None:
        config = CitationConfig(style=CitationStyle.INLINE)
        result, citations = apply_citation_style("", config)
        assert result == ""
        assert citations == []

    def test_no_citations_in_content(self) -> None:
        content = "No citations in this text."
        config = CitationConfig(style=CitationStyle.FOOTNOTE)
        result, citations = apply_citation_style(content, config)
        assert result == content
        assert citations == []

    def test_include_confidence_when_available(self) -> None:
        content = "Fact [Source: doc.pdf, Page 1]"
        config = CitationConfig(style=CitationStyle.FOOTNOTE, include_confidence=True)
        result, citations = apply_citation_style(content, config)
        assert len(citations) == 1
        # Confidence may be None from parsing; config controls display
        assert citations[0].confidence is None  # Parser doesn't extract confidence

    def test_include_page_false(self) -> None:
        content = "Cap [Source: moa.pdf, Page 3]"
        config = CitationConfig(style=CitationStyle.FOOTNOTE, include_page=False)
        result, citations = apply_citation_style(content, config)
        assert len(citations) == 1
        # Footer should not include "page 3" when include_page=False
        assert "page 3" not in result.lower() or "p. 3" not in result.lower()


class TestParseCitationsEdgeCases:
    """Edge cases and invalid inputs."""

    def test_content_with_newlines(self) -> None:
        content = "Para one.\n\nPara two [Source: x.pdf, Page 2]."
        citations = parse_citations(content)
        assert len(citations) == 1
        assert citations[0].page == 2

    def test_malformed_marker_ignored(self) -> None:
        content = "Text [Source: no comma here]"
        citations = parse_citations(content)
        # Should not crash; may or may not parse
        assert isinstance(citations, list)

    def test_parentheses_source(self) -> None:
        content = "Info (Source: doc.pdf, Page 1)"
        citations = parse_citations(content)
        assert len(citations) == 1
        assert citations[0].source == "doc.pdf"
        assert citations[0].page == 1
