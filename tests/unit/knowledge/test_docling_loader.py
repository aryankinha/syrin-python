"""Tests for DoclingLoader."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from syrin.knowledge._document import Document


class TestDoclingLoaderErrors:
    """Tests for DoclingLoader error handling."""

    def test_file_not_found_raises(self) -> None:
        """DoclingLoader raises FileNotFoundError when file does not exist."""
        from syrin.knowledge.loaders import DoclingLoader

        with patch("syrin.knowledge.loaders._docling._check_docling") as mock_check:
            mock_check.return_value = None
            loader = DoclingLoader("/nonexistent/file.pdf")
            with pytest.raises(FileNotFoundError, match="does not exist"):
                loader.load()

    def test_docling_not_installed_raises(self) -> None:
        """DoclingLoader raises ImportError with helpful message when docling not installed."""
        from syrin.knowledge.loaders import DoclingLoader

        with patch("syrin.knowledge.loaders._docling._check_docling") as check:
            check.side_effect = ImportError(
                "docling is required for DoclingLoader. Install with: pip install syrin[docling]"
            )
            loader = DoclingLoader("/any/path.pdf")
            with pytest.raises(ImportError, match="syrin\\[docling\\]"):
                loader.load()


class TestDoclingLoaderWithMock:
    """Tests for DoclingLoader using mocked docling."""

    @pytest.fixture
    def mock_docling(self) -> MagicMock:
        """Create mock ConversionResult with document, tables, and markdown."""
        doc = MagicMock()
        doc.export_to_markdown.return_value = "# Page 1\n\nSome text content.\n"
        doc.tables = []

        conv_res = MagicMock()
        conv_res.document = doc
        return conv_res

    @pytest.fixture
    def temp_pdf_path(self) -> str:
        """Create a temporary empty PDF-like file (docling validates format)."""
        fd, path = tempfile.mkstemp(suffix=".pdf")
        Path(path).write_bytes(b"%PDF-1.4 dummy")  # minimal PDF header
        yield path
        Path(path).unlink(missing_ok=True)

    def test_load_produces_documents(self, temp_pdf_path: str, mock_docling: MagicMock) -> None:
        """DoclingLoader produces Document list from converted output."""
        from syrin.knowledge.loaders import DoclingLoader

        with patch("docling.document_converter.DocumentConverter") as mock_converter:
            mock_converter.return_value.convert.return_value = mock_docling

            loader = DoclingLoader(temp_pdf_path)
            docs = loader.load()

        assert len(docs) >= 1
        assert all(isinstance(d, Document) for d in docs)
        assert docs[0].content
        assert docs[0].source == temp_pdf_path
        assert docs[0].source_type == "pdf"

    def test_tables_become_separate_documents(
        self, temp_pdf_path: str, mock_docling: MagicMock
    ) -> None:
        """Tables are extracted as separate Documents with structured metadata."""
        from syrin.knowledge.loaders import DoclingLoader

        table = MagicMock()
        table_df = MagicMock()
        table_df.to_csv.return_value = "Cat,Shares\nPromoter,1250000"
        table_df.to_markdown.return_value = "| Cat | Shares |\n|---|-----|\n| Promoter | 1250000 |"
        table.export_to_dataframe.return_value = table_df
        table.export_to_html.return_value = "<table><tr><td>Promoter</td></tr></table>"
        mock_docling.document.tables = [table]

        with patch("docling.document_converter.DocumentConverter") as mock_converter:
            mock_converter.return_value.convert.return_value = mock_docling

            loader = DoclingLoader(temp_pdf_path)
            docs = loader.load()

        table_docs = [d for d in docs if "table" in d.source_type]
        assert len(table_docs) == 1
        assert table_docs[0].metadata.get("table_index") == 0
        assert "table_csv" in table_docs[0].metadata
        assert "table_html" in table_docs[0].metadata
        assert "table_markdown" in table_docs[0].metadata

    def test_extract_tables_false_no_table_docs(
        self, temp_pdf_path: str, mock_docling: MagicMock
    ) -> None:
        """When extract_tables=False, no separate table Documents are created."""
        from syrin.knowledge.loaders import DoclingLoader

        table = MagicMock()
        table_df = MagicMock()
        table.export_to_dataframe.return_value = table_df
        mock_docling.document.tables = [table]

        with patch("docling.document_converter.DocumentConverter") as mock_converter:
            mock_converter.return_value.convert.return_value = mock_docling

            loader = DoclingLoader(temp_pdf_path, extract_tables=False)
            docs = loader.load()

        table_docs = [d for d in docs if "table" in d.source_type]
        assert len(table_docs) == 0

    def test_table_format_markdown_content(
        self, temp_pdf_path: str, mock_docling: MagicMock
    ) -> None:
        """table_format='markdown' uses markdown as Document content."""
        from syrin.knowledge.loaders import DoclingLoader

        table = MagicMock()
        table_df = MagicMock()
        table_df.to_markdown.return_value = "| A | B |"
        table_df.to_csv.return_value = "A,B"
        table.export_to_dataframe.return_value = table_df
        table.export_to_html.return_value = "<table></table>"
        mock_docling.document.tables = [table]

        with patch("docling.document_converter.DocumentConverter") as mock_converter:
            mock_converter.return_value.convert.return_value = mock_docling

            loader = DoclingLoader(temp_pdf_path, table_format="markdown")
            docs = loader.load()

        table_doc = next(d for d in docs if "table" in d.source_type)
        assert "| A | B |" in table_doc.content

    def test_table_format_csv_content(self, temp_pdf_path: str, mock_docling: MagicMock) -> None:
        """table_format='csv' uses CSV as Document content."""
        from syrin.knowledge.loaders import DoclingLoader

        table = MagicMock()
        table_df = MagicMock()
        table_df.to_csv.return_value = "A,B\n1,2"
        table_df.to_markdown.return_value = "| A | B |"
        table.export_to_dataframe.return_value = table_df
        table.export_to_html.return_value = "<table></table>"
        mock_docling.document.tables = [table]

        with patch("docling.document_converter.DocumentConverter") as mock_converter:
            mock_converter.return_value.convert.return_value = mock_docling

            loader = DoclingLoader(temp_pdf_path, table_format="csv")
            docs = loader.load()

        table_doc = next(d for d in docs if "table" in d.source_type)
        assert "A,B" in table_doc.content

    def test_accepts_path_object(self, temp_pdf_path: str, mock_docling: MagicMock) -> None:
        """DoclingLoader accepts Path object."""
        from syrin.knowledge.loaders import DoclingLoader

        with patch("docling.document_converter.DocumentConverter") as mock_converter:
            mock_converter.return_value.convert.return_value = mock_docling

            loader = DoclingLoader(Path(temp_pdf_path))
            docs = loader.load()

        assert docs[0].source == temp_pdf_path

    @pytest.mark.asyncio
    async def test_aload_returns_same_as_load(
        self, temp_pdf_path: str, mock_docling: MagicMock
    ) -> None:
        """aload() returns same documents as load()."""
        from syrin.knowledge.loaders import DoclingLoader

        with patch("docling.document_converter.DocumentConverter") as mock_converter:
            mock_converter.return_value.convert.return_value = mock_docling

            loader = DoclingLoader(temp_pdf_path)
            sync_docs = loader.load()
            async_docs = await loader.aload()

        assert len(sync_docs) == len(async_docs)
        assert sync_docs[0].content == async_docs[0].content
