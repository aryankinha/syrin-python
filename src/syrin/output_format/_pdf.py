"""PDF output formatter via WeasyPrint."""

from __future__ import annotations

from typing import cast

_PDF_EXTRA_HINT = "Install with: pip install syrin[pdf-output]"


def _get_weasyprint() -> type:
    """Lazy import WeasyPrint. Raises ImportError with hint if not installed."""
    try:
        from weasyprint import HTML as WeasyHTML

        return cast(type, WeasyHTML)
    except ImportError as e:
        raise ImportError(
            f"WeasyPrint is required for PDF output. {_PDF_EXTRA_HINT}. Original: {e}"
        ) from e


class PDFFormatter:
    """Formatter for PDF documents via WeasyPrint. Requires syrin[pdf-output]."""

    def format(self, content: str, *, metadata: dict[str, object] | None = None) -> bytes:
        """Convert content to PDF bytes. Content is wrapped in HTML first."""
        from syrin.output_format._html import HTMLFormatter

        html_fmt = HTMLFormatter()
        html_bytes = html_fmt.format(content, metadata=metadata)
        html_str = html_bytes.decode("utf-8")

        WeasyHTML = _get_weasyprint()
        doc = WeasyHTML(string=html_str)
        return cast(bytes, doc.write_pdf())

    def extension(self) -> str:
        return "pdf"
