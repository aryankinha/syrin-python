"""Unit tests for OutputFormat, OutputConfig, formatters, and save helpers."""

import tempfile
from pathlib import Path

import pytest

from syrin.output_format import (
    CitationStyle,
    OutputConfig,
    OutputFormat,
    OutputFormatter,
    apply_citation_to_content,
    get_formatter,
    save_as,
    save_as_docx,
    save_as_pdf,
)
from syrin.template import SlotConfig, Template


class TestOutputFormat:
    """OutputFormat enum."""

    def test_enum_values(self) -> None:
        assert OutputFormat.TEXT == "text"
        assert OutputFormat.MARKDOWN == "markdown"
        assert OutputFormat.HTML == "html"
        assert OutputFormat.PDF == "pdf"
        assert OutputFormat.DOCX == "docx"


class TestOutputConfig:
    """OutputConfig dataclass."""

    def test_bare_format(self) -> None:
        cfg = OutputConfig(format=OutputFormat.TEXT)
        assert cfg.format == OutputFormat.TEXT
        assert cfg.template is None
        assert cfg.title is None

    def test_with_template(self) -> None:
        tpl = Template("x", "{{a}}", slots={"a": SlotConfig("str")})
        cfg = OutputConfig(format=OutputFormat.MARKDOWN, template=tpl)
        assert cfg.template is tpl
        assert cfg.format == OutputFormat.MARKDOWN

    def test_with_title(self) -> None:
        cfg = OutputConfig(format=OutputFormat.PDF, title="Report")
        assert cfg.title == "Report"

    def test_str_format_accepted(self) -> None:
        cfg = OutputConfig(format="markdown")
        assert cfg.format == OutputFormat.MARKDOWN

    def test_with_citation(self) -> None:
        cfg = OutputConfig(
            format=OutputFormat.PDF,
            citation_style=CitationStyle.FOOTNOTE,
            citation_include_page=True,
        )
        assert cfg.citation_style == CitationStyle.FOOTNOTE
        assert cfg.citation_include_page is True

    def test_citation_none_by_default(self) -> None:
        cfg = OutputConfig(format=OutputFormat.TEXT)
        assert cfg.citation_style is None


class TestApplyCitationToContent:
    """apply_citation_to_content helper."""

    def test_no_citation_config_returns_unchanged(self) -> None:
        cfg = OutputConfig(format=OutputFormat.TEXT)
        content = "Text [Source: doc.pdf, Page 1]"
        result, citations = apply_citation_to_content(content, cfg)
        assert result == content
        assert citations == []

    def test_with_citation_config_parses_and_transforms(self) -> None:
        cfg = OutputConfig(
            format=OutputFormat.MARKDOWN,
            citation_style=CitationStyle.FOOTNOTE,
        )
        content = "Cap is ₹50L [Source: moa.pdf, Page 3]."
        result, citations = apply_citation_to_content(content, cfg)
        assert "[1]" in result
        assert "moa.pdf" in result
        assert len(citations) == 1
        assert citations[0].source == "moa.pdf"
        assert citations[0].page == 3


class TestOutputFormatterProtocol:
    """OutputFormatter implementations satisfy protocol."""

    def test_text_formatter(self) -> None:
        fmt = get_formatter(OutputFormat.TEXT)
        assert isinstance(fmt, OutputFormatter)
        data = fmt.format("hello", metadata=None)
        assert data == b"hello"
        assert fmt.extension() == "txt"

    def test_markdown_formatter(self) -> None:
        fmt = get_formatter(OutputFormat.MARKDOWN)
        assert isinstance(fmt, OutputFormatter)
        data = fmt.format("# Hi", metadata=None)
        assert data == b"# Hi"
        assert fmt.extension() == "md"
        data_with_title = fmt.format("body", metadata={"title": "Doc"})
        assert b"# Doc" in data_with_title

    def test_html_formatter(self) -> None:
        fmt = get_formatter(OutputFormat.HTML)
        assert isinstance(fmt, OutputFormatter)
        data = fmt.format("Hello", metadata=None)
        assert b"<!DOCTYPE html>" in data
        assert b"<html" in data
        assert b"Hello" in data
        assert fmt.extension() == "html"


class TestSaveAs:
    """save_as, save_as_pdf, save_as_docx helpers."""

    def test_save_as_text(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "out.txt"
            result = save_as("hello", OutputFormat.TEXT, p)
            assert result == p
            assert p.read_text(encoding="utf-8") == "hello"

    def test_save_as_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "out.md"
            result = save_as("# Title\n\nBody", OutputFormat.MARKDOWN, p, title="Report")
            assert result == p
            assert "Report" in p.read_text(encoding="utf-8")

    def test_save_as_returns_bytes_when_path_none(self) -> None:
        data = save_as("hello", OutputFormat.TEXT, None)
        assert isinstance(data, bytes)
        assert data == b"hello"

    def test_save_as_docx_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "out.docx"
            result = save_as_docx("Hello World", p, title="Doc")
            assert result == p
            assert p.exists()
            assert p.stat().st_size > 0

    def test_save_as_docx_returns_bytes_when_path_none(self) -> None:
        data = save_as_docx("Hello", None)
        assert isinstance(data, bytes)
        assert len(data) > 0


class TestSaveAsPdf:
    """save_as_pdf requires WeasyPrint."""

    def test_save_as_pdf_import_error_without_weasyprint(self) -> None:
        """When WeasyPrint not installed, save_as_pdf raises ImportError."""
        try:
            import weasyprint  # noqa: F401

            has_weasy = True
        except ImportError:
            has_weasy = False

        if not has_weasy:
            with pytest.raises(ImportError, match="WeasyPrint"):
                save_as_pdf("hi", Path("/tmp/out.pdf"))
        else:
            with tempfile.TemporaryDirectory() as d:
                p = Path(d) / "out.pdf"
                result = save_as_pdf("Hello", p)
                assert result == p
                assert p.exists()


class TestGetFormatterUnknown:
    """Unknown format raises."""

    def test_unknown_format_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown output format"):
            get_formatter("unknown")  # type: ignore[arg-type]
