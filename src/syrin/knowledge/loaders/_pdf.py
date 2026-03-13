"""PDF loader using docling."""

from __future__ import annotations

import logging
from pathlib import Path

from syrin.knowledge._document import Document, DocumentMetadata

_log = logging.getLogger(__name__)


class PDFLoader:
    """Load PDF files using docling.

    Extracts text from each page. Each page becomes a separate Document.
    Uses docling for better table and image extraction.

    Example:
        loader = PDFLoader("path/to/file.pdf")
        docs = loader.load()  # List of Documents, one per page
    """

    def __init__(self, path: str | Path) -> None:
        """Initialize PDFLoader.

        Args:
            path: Path to the PDF file.
        """
        self._path = Path(path)

    def _check_dependency(self) -> None:
        """Check if docling is installed."""
        import importlib.util

        if importlib.util.find_spec("docling") is None:
            raise ImportError(
                "docling is required for PDF loading. Install with: uv pip install syrin[pdf]"
            )

    @property
    def path(self) -> Path:
        """Path to the PDF file."""
        return self._path

    def load(self) -> list[Document]:
        """Load the PDF file, one page per Document.

        Returns:
            List of Documents, one per page.

        Raises:
            ImportError: If docling is not installed.
            FileNotFoundError: If the PDF file does not exist.
        """
        if not self._path.exists():
            raise FileNotFoundError(f"PDF file not found: {self._path}")

        # Import docling here to get proper error message
        try:
            from docling.document_converter import DocumentConverter
        except ImportError as err:
            raise ImportError(
                "docling is required for PDF loading. Install with: uv pip install syrin[pdf]"
            ) from err

        converter = DocumentConverter()
        result = converter.convert(str(self._path))
        docs: list[Document] = []

        for i, page in enumerate(result.document.pages):
            page_text = getattr(page, "text", "") or ""
            if page_text.strip():
                metadata: DocumentMetadata = {
                    "page": i + 1,
                    "total_pages": len(result.document.pages),
                    "has_pages": True,
                }
                docs.append(
                    Document(
                        content=page_text,
                        source=str(self._path),
                        source_type="pdf",
                        metadata=metadata,
                    )
                )
            else:
                _log.warning(
                    "Page %d of %s produced no text.",
                    i + 1,
                    self._path,
                )

        return docs

    async def aload(self) -> list[Document]:
        """Load the PDF file asynchronously.

        Returns:
            List of Documents, one per page.
        """
        return self.load()


__all__ = ["PDFLoader"]
