"""OutputConfig citation fields: CitationConfig removal and flat field API.

CitationConfig class removed. Fields absorbed as citation_style,
citation_include_page, citation_include_confidence on OutputConfig.
"""

from __future__ import annotations

import pytest

from syrin.output_format import (
    CitationStyle,
    OutputConfig,
    OutputFormat,
    apply_citation_to_content,
)


class TestOutputConfigCitationFlatFields:
    """OutputConfig exposes citation_style, citation_include_page, citation_include_confidence."""

    def test_default_citation_style_is_none(self) -> None:
        """OutputConfig default has no citation (citation_style=None)."""
        cfg = OutputConfig(format=OutputFormat.MARKDOWN)
        assert cfg.citation_style is None

    def test_citation_style_footnote_accepted(self) -> None:
        """citation_style=FOOTNOTE stored correctly."""
        cfg = OutputConfig(format=OutputFormat.MARKDOWN, citation_style=CitationStyle.FOOTNOTE)
        assert cfg.citation_style == CitationStyle.FOOTNOTE

    def test_citation_include_page_default_true(self) -> None:
        """citation_include_page defaults to True."""
        cfg = OutputConfig(format=OutputFormat.MARKDOWN)
        assert cfg.citation_include_page is True

    def test_citation_include_confidence_default_false(self) -> None:
        """citation_include_confidence defaults to False."""
        cfg = OutputConfig(format=OutputFormat.MARKDOWN)
        assert cfg.citation_include_confidence is False

    def test_all_citation_flat_fields_together(self) -> None:
        """All citation flat fields accepted simultaneously."""
        cfg = OutputConfig(
            format=OutputFormat.PDF,
            citation_style=CitationStyle.APPENDIX,
            citation_include_page=False,
            citation_include_confidence=True,
        )
        assert cfg.citation_style == CitationStyle.APPENDIX
        assert cfg.citation_include_page is False
        assert cfg.citation_include_confidence is True

    def test_citation_config_class_not_exported_from_syrin(self) -> None:
        """CitationConfig is no longer exported from syrin top-level."""
        import syrin

        assert not hasattr(syrin, "CitationConfig"), "CitationConfig must not be a public export"

    def test_output_config_citation_field_removed(self) -> None:
        """OutputConfig no longer has a 'citation' field."""
        cfg = OutputConfig(format=OutputFormat.MARKDOWN)
        assert not hasattr(cfg, "citation"), "OutputConfig.citation field must be removed"

    def test_citation_not_accepted_as_kwarg(self) -> None:
        """The old citation= kwarg is not accepted."""
        with pytest.raises(TypeError):
            OutputConfig(format=OutputFormat.MARKDOWN, citation=object())  # type: ignore[call-arg]


class TestApplyCitationToContentWithFlatFields:
    """apply_citation_to_content uses flat fields from OutputConfig."""

    def test_no_citation_style_passes_through(self) -> None:
        """No citation_style → content passes through unchanged."""
        cfg = OutputConfig(format=OutputFormat.MARKDOWN)
        content = "Hello [Source: doc.pdf, Page 3] world"
        result, citations = apply_citation_to_content(content, cfg)
        assert result == content
        assert citations == []

    def test_inline_style_returns_content_with_citations(self) -> None:
        """INLINE style returns content unchanged with parsed citations."""
        cfg = OutputConfig(format=OutputFormat.MARKDOWN, citation_style=CitationStyle.INLINE)
        content = "Hello [Source: doc.pdf, Page 3] world"
        result, citations = apply_citation_to_content(content, cfg)
        assert result == content
        assert len(citations) == 1
        assert citations[0].source == "doc.pdf"

    def test_none_style_strips_markers(self) -> None:
        """NONE style strips citation markers from content."""
        cfg = OutputConfig(format=OutputFormat.MARKDOWN, citation_style=CitationStyle.NONE)
        content = "Hello [Source: doc.pdf, Page 3] world"
        result, citations = apply_citation_to_content(content, cfg)
        assert "[Source:" not in result
        assert len(citations) > 0  # still tracks them

    def test_footnote_style_replaces_with_refs(self) -> None:
        """FOOTNOTE style replaces markers with [1], [2] and appends references."""
        cfg = OutputConfig(format=OutputFormat.MARKDOWN, citation_style=CitationStyle.FOOTNOTE)
        content = "Claim [Source: doc.pdf, Page 1] and fact [Source: other.pdf, Page 5]"
        result, citations = apply_citation_to_content(content, cfg)
        assert "[1]" in result
        assert "[2]" in result
        assert "References" in result
        assert len(citations) == 2

    def test_footnote_respects_citation_include_page_false(self) -> None:
        """FOOTNOTE with citation_include_page=False omits page from references."""
        cfg = OutputConfig(
            format=OutputFormat.MARKDOWN,
            citation_style=CitationStyle.FOOTNOTE,
            citation_include_page=False,
        )
        content = "Claim [Source: doc.pdf, Page 3]"
        result, _citations = apply_citation_to_content(content, cfg)
        assert "page 3" not in result.lower()

    def test_appendix_style_groups_at_end(self) -> None:
        """APPENDIX style groups references at end under ## References."""
        cfg = OutputConfig(format=OutputFormat.MARKDOWN, citation_style=CitationStyle.APPENDIX)
        content = "First [Source: a.pdf, Page 1] then [Source: b.pdf, Page 2]"
        result, _citations = apply_citation_to_content(content, cfg)
        assert "## References" in result

    def test_empty_content_no_citations(self) -> None:
        """Empty content returns no citations regardless of style."""
        cfg = OutputConfig(format=OutputFormat.MARKDOWN, citation_style=CitationStyle.FOOTNOTE)
        result, citations = apply_citation_to_content("", cfg)
        assert result == ""
        assert citations == []
