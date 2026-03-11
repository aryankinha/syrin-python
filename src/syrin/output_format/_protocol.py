"""OutputFormatter protocol for file generation."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class OutputFormatter(Protocol):
    """Protocol for output formatters that convert text content to file bytes.

    Implementations: TextFormatter, MarkdownFormatter, HTMLFormatter,
    PDFFormatter, DOCXFormatter.
    """

    def format(self, content: str, *, metadata: dict[str, object] | None = None) -> bytes:
        """Convert text content to formatted file bytes.

        Args:
            content: Raw text content to format.
            metadata: Optional metadata (title, styles, etc.).

        Returns:
            File bytes (e.g. UTF-8 for text, binary for PDF/DOCX).
        """
        ...

    def extension(self) -> str:
        """File extension without leading dot (e.g. 'txt', 'pdf')."""
        ...
