"""Docling-powered document loader for PDF, DOCX, PPTX, XLSX, HTML, images."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol, cast

from syrin.knowledge._document import Document, DocumentMetadata


class _TableDataFrameLike(Protocol):
    """Protocol for DataFrame-like object from table.export_to_dataframe()."""

    def to_csv(self, index: bool = True) -> str:
        """Return CSV string."""
        ...

    def to_markdown(self, index: bool = True) -> str:
        """Return Markdown table string."""
        ...


class _DoclingTableLike(Protocol):
    """Protocol for Docling table objects (structural typing for docling.TableItem)."""

    def export_to_dataframe(self, doc: object) -> _TableDataFrameLike:
        """Return table as DataFrame-like."""
        ...

    def export_to_html(self, doc: object) -> str:
        """Return table as HTML string."""
        ...


TableFormat = Literal["markdown", "csv", "html"]
_VALID_TABLE_FORMATS: frozenset[str] = frozenset({"markdown", "csv", "html"})


def _check_docling() -> None:
    """Ensure docling is installed. Raises ImportError with helpful message."""
    try:
        import docling  # noqa: F401
    except ImportError as err:
        raise ImportError(
            "docling is required for DoclingLoader. Install with: pip install syrin[docling]"
        ) from err


def _suffix_to_source_type(suffix: str) -> str:
    """Map file suffix to base source_type (pdf, docx, xlsx, etc.)."""
    ext = suffix.lower().lstrip(".")
    mapping = {
        "pdf": "pdf",
        "docx": "docx",
        "doc": "doc",
        "pptx": "pptx",
        "ppt": "ppt",
        "xlsx": "xlsx",
        "xls": "xls",
        "html": "html",
        "htm": "html",
        "png": "image",
        "jpg": "image",
        "jpeg": "image",
        "tiff": "image",
    }
    return mapping.get(ext, "document")


class DoclingLoader:
    """Universal document loader powered by IBM Docling.

    Supports PDF, DOCX, PPTX, XLSX, HTML, images with AI-powered
    layout analysis and table structure recognition.

    Tables are extracted as separate Documents with structured metadata
    including CSV, HTML, and Markdown representations.

    Requires: pip install syrin[docling]
    """

    def __init__(
        self,
        path: str | Path,
        *,
        extract_tables: bool = True,
        table_format: TableFormat | str = "markdown",
        ocr: bool = False,
    ) -> None:
        """Initialize DoclingLoader.

        Args:
            path: Path to the document file (PDF, DOCX, PPTX, XLSX, HTML, images).
            extract_tables: If True, extract tables as separate Documents with
                structured metadata (table_csv, table_html, table_markdown).
            table_format: Primary format for table Document content. One of
                "markdown", "csv", "html". Metadata always preserves all three.
            ocr: Enable OCR for scanned documents (adds processing time).
        """
        self._path = Path(path)
        self._extract_tables = extract_tables
        self._table_format = table_format if table_format in _VALID_TABLE_FORMATS else "markdown"
        self._ocr = ocr

    @property
    def path(self) -> Path:
        """Path to the document file."""
        return self._path

    def load(self) -> list[Document]:
        """Load the document and optionally extract tables as separate Documents.

        Returns:
            List of Documents. Main content first, then table Documents if
            extract_tables=True. Tables include table_csv, table_html,
            table_markdown in metadata.
        """
        _check_docling()

        if not self._path.exists():
            raise FileNotFoundError(f"Document file does not exist: {self._path}")

        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(str(self._path))

        base_type = _suffix_to_source_type(self._path.suffix)
        docs: list[Document] = []

        main_md = result.document.export_to_markdown()
        if main_md.strip():
            meta: DocumentMetadata = {}
            if hasattr(result.document, "pages") and result.document.pages:
                meta["total_pages"] = len(result.document.pages)
            docs.append(
                Document(
                    content=main_md,
                    source=str(self._path),
                    source_type=base_type,
                    metadata=meta,
                )
            )

        if self._extract_tables and result.document.tables:
            for idx, table in enumerate(result.document.tables):
                table_doc = self._table_to_document(
                    cast(_DoclingTableLike, table),
                    result.document,
                    base_type,
                    idx,
                )
                docs.append(table_doc)

        return docs

    def _table_to_document(
        self,
        table: _DoclingTableLike,
        document: object,
        base_type: str,
        index: int,
    ) -> Document:
        """Convert a Docling table to a Document with full metadata."""
        table_df = table.export_to_dataframe(doc=document)

        table_csv = table_df.to_csv(index=False)
        table_md = table_df.to_markdown(index=False)
        table_html = table.export_to_html(doc=document)

        format_map = {
            "markdown": table_md,
            "csv": table_csv,
            "html": table_html,
        }
        content = format_map.get(self._table_format, table_md)

        meta: DocumentMetadata = {
            "table_index": index,
            "table_csv": table_csv,
            "table_html": table_html,
            "table_markdown": table_md,
        }

        source_type = f"{base_type}_table"
        return Document(
            content=content,
            source=str(self._path),
            source_type=source_type,
            metadata=meta,
        )

    async def aload(self) -> list[Document]:
        """Load the document asynchronously.

        Returns:
            Same as load(). Docling conversion runs in executor (CPU-bound).
        """
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.load)


__all__ = ["DoclingLoader"]
