"""Output configuration and file generation for agent responses.

OutputConfig controls how agent output is structured, rendered, and exported.
Use output_config on Agent to enable file generation (PDF, DOCX, Markdown, etc.)
and optional template-based slot filling.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, overload

from syrin.output_format._citation import (
    Citation,
    CitationStyle,
    apply_citation_style,
)
from syrin.output_format._citation import (
    CitationConfig as _CitationConfig,
)
from syrin.output_format._protocol import OutputFormatter

if TYPE_CHECKING:
    from syrin.template import Template

__all__ = [
    "Citation",
    "CitationStyle",
    "OutputFormat",
    "OutputConfig",
    "OutputFormatter",
    "apply_citation_to_content",
    "get_formatter",
    "save_as_pdf",
    "save_as_docx",
    "save_as",
]


class OutputFormat(StrEnum):
    """Output file format for agent responses.

    Attributes:
        TEXT: Plain text (.txt).
        MARKDOWN: Markdown (.md).
        HTML: HTML document.
        PDF: PDF document (requires syrin[pdf-output]).
        DOCX: Word document (requires syrin[docx]).
    """

    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    DOCX = "docx"


@dataclass
class OutputConfig:
    """Output configuration: format, template, title, citation styling, and file generation.

    Use with Agent: ``output_config=OutputConfig(format=OutputFormat.MARKDOWN, title="Report")``.
    Citation markers in content are parsed and styled automatically when ``citation_style`` is set.

    Attributes:
        format: Output format (TEXT, MARKDOWN, HTML, PDF, DOCX).
        template: Optional template for slot-based generation. When set,
            agent output is rendered through the template. Requires
            ``output=Output(SomeModel)`` to provide structured data for slots.
        title: Document title (for PDF/DOCX/MD headers).
        citation_style: How citations appear — INLINE, FOOTNOTE, APPENDIX, NONE.
            ``None`` (default) disables citation processing entirely.
        citation_include_page: Include page number when rendering citations. Default True.
        citation_include_confidence: Include confidence score when available. Default False.

    Example::

        OutputConfig(
            format=OutputFormat.PDF,
            title="Research Report",
            citation_style=CitationStyle.FOOTNOTE,
            citation_include_page=True,
        )
    """

    format: OutputFormat
    template: Template | None = None
    title: str | None = None
    citation_style: CitationStyle | None = None
    citation_include_page: bool = True
    citation_include_confidence: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.format, str) and not isinstance(self.format, OutputFormat):
            object.__setattr__(self, "format", OutputFormat(self.format))


def apply_citation_to_content(
    content: str,
    config: OutputConfig,
) -> tuple[str, list[Citation]]:
    """Apply citation parsing and styling when config.citation_style is set.

    Args:
        content: Raw content that may contain citation markers.
        config: Output configuration. Citation processing is active only when
            ``config.citation_style`` is not None.

    Returns:
        ``(transformed_content, list of Citation objects)``.
        If ``config.citation_style`` is None, returns ``(content, [])``.
    """
    if config.citation_style is None:
        return content, []
    internal_cfg = _CitationConfig(
        style=config.citation_style,
        include_page=config.citation_include_page,
        include_confidence=config.citation_include_confidence,
    )
    return apply_citation_style(content, internal_cfg)


def get_formatter(fmt: OutputFormat) -> OutputFormatter:
    """Return the OutputFormatter for the given format."""
    if fmt == OutputFormat.TEXT:
        from syrin.output_format._text import TextFormatter

        return TextFormatter()
    if fmt == OutputFormat.MARKDOWN:
        from syrin.output_format._markdown import MarkdownFormatter

        return MarkdownFormatter()
    if fmt == OutputFormat.HTML:
        from syrin.output_format._html import HTMLFormatter

        return HTMLFormatter()
    if fmt == OutputFormat.PDF:
        from syrin.output_format._pdf import PDFFormatter

        return PDFFormatter()
    if fmt == OutputFormat.DOCX:
        from syrin.output_format._docx import DOCXFormatter

        return DOCXFormatter()
    raise ValueError(f"Unknown output format: {fmt}")


def _metadata_from_title(title: str | None) -> dict[str, object]:
    """Build metadata dict from optional title."""
    if title:
        return {"title": title}
    return {}


@overload
def save_as_pdf(content: str, path: str | Path, *, title: str | None = None) -> Path: ...
@overload
def save_as_pdf(content: str, path: None = None, *, title: str | None = None) -> bytes: ...


def save_as_pdf(
    content: str,
    path: str | Path | None = None,
    *,
    title: str | None = None,
) -> Path | bytes:
    """Save content as PDF file.

    Args:
        content: Text content (will be converted to HTML then PDF).
        path: File path to write. If None, returns raw bytes.
        title: Document title for header.

    Returns:
        Path to written file, or raw bytes if path is None.

    Raises:
        ImportError: If WeasyPrint is not installed. Use pip install syrin[pdf-output].
    """
    formatter = get_formatter(OutputFormat.PDF)
    metadata = _metadata_from_title(title)
    data = formatter.format(content, metadata=metadata)
    if path is None:
        return data
    p = Path(path)
    p.write_bytes(data)
    return p


@overload
def save_as_docx(content: str, path: str | Path, *, title: str | None = None) -> Path: ...
@overload
def save_as_docx(content: str, path: None = None, *, title: str | None = None) -> bytes: ...


def save_as_docx(
    content: str,
    path: str | Path | None = None,
    *,
    title: str | None = None,
) -> Path | bytes:
    """Save content as Word document.

    Args:
        content: Text content.
        path: File path to write. If None, returns raw bytes.
        title: Document title/heading.

    Returns:
        Path to written file, or raw bytes if path is None.

    Raises:
        ImportError: If python-docx is not installed. Use pip install syrin[docx].
    """
    formatter = get_formatter(OutputFormat.DOCX)
    metadata = _metadata_from_title(title)
    data = formatter.format(content, metadata=metadata)
    if path is None:
        return data
    p = Path(path)
    p.write_bytes(data)
    return p


def save_as(
    content: str,
    fmt: OutputFormat,
    path: str | Path | None = None,
    *,
    title: str | None = None,
) -> Path | bytes:
    """Save content in the given format.

    Args:
        content: Text content.
        fmt: Output format.
        path: File path. If None, returns raw bytes.
        title: Document title (for PDF/DOCX/MD).

    Returns:
        Path to written file, or raw bytes if path is None.
    """
    formatter = get_formatter(fmt)
    metadata = _metadata_from_title(title)
    data = formatter.format(content, metadata=metadata)
    if path is None:
        return data
    p = Path(path)
    p.write_bytes(data)
    return p


def format_to_file(
    content: str,
    fmt: OutputFormat,
    *,
    title: str | None = None,
) -> tuple[Path, bytes]:
    """Format content and write to a temporary file. For use by agent response.

    Returns:
        (path_to_temp_file, raw_bytes)
    """
    formatter = get_formatter(fmt)
    metadata = _metadata_from_title(title)
    data = formatter.format(content, metadata=metadata)
    suffix = "." + formatter.extension()
    with tempfile.NamedTemporaryFile(mode="wb", suffix=suffix, delete=False) as f:
        f.write(data)
        tmp_path = Path(f.name)
    return tmp_path, data
