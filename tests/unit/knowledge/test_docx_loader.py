"""Tests for DOCXLoader."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from syrin.knowledge._document import Document


def _make_minimal_docx(path: str) -> None:
    """Create a minimal valid DOCX using python-docx."""
    try:
        from docx import Document as DocxDocument

        doc = DocxDocument()
        doc.add_paragraph("Hello DOCX content")
        doc.save(path)
    except ImportError:
        pytest.skip("python-docx required for DOCX fixture")


class TestDOCXLoaderErrors:
    """Tests for DOCXLoader error handling."""

    def test_file_not_found_raises(self) -> None:
        """DOCXLoader raises FileNotFoundError when file does not exist."""
        from syrin.knowledge.loaders import DOCXLoader

        loader = DOCXLoader("/nonexistent/file.docx")
        with pytest.raises(FileNotFoundError, match="does not exist"):
            loader.load()

    def test_python_docx_not_installed_raises(self) -> None:
        """DOCXLoader raises ImportError when python-docx not installed."""
        from syrin.knowledge.loaders import DOCXLoader

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            path = f.name
        try:
            _make_minimal_docx(path)
            with (
                patch("syrin.knowledge.loaders._docx._try_docling", return_value=None),
                patch("syrin.knowledge.loaders._docx._check_docx") as mock_check,
            ):
                mock_check.side_effect = ImportError(
                    "python-docx required. Install with: pip install syrin[docx]"
                )
                loader = DOCXLoader(path)
                with pytest.raises(ImportError, match="syrin\\[docx\\]"):
                    loader.load()
        finally:
            Path(path).unlink(missing_ok=True)


class TestDOCXLoaderWithMock:
    """Tests for DOCXLoader using mocked python-docx."""

    @pytest.fixture
    def temp_docx(self) -> str:
        """Create a minimal valid DOCX file."""
        fd, path = tempfile.mkstemp(suffix=".docx")
        Path(path).unlink(missing_ok=True)
        _make_minimal_docx(path)
        yield path
        Path(path).unlink(missing_ok=True)

    def test_load_produces_documents(self, temp_docx: str) -> None:
        """DOCXLoader produces Document list."""
        from syrin.knowledge.loaders import DOCXLoader

        loader = DOCXLoader(temp_docx, use_docling=False)
        docs = loader.load()

        assert len(docs) >= 1
        assert all(isinstance(d, Document) for d in docs)
        assert docs[0].source == temp_docx
        assert docs[0].source_type == "docx"
        assert "Hello DOCX" in docs[0].content or len(docs[0].content) > 0

    def test_accepts_path_object(self, temp_docx: str) -> None:
        """DOCXLoader accepts Path object."""
        from syrin.knowledge.loaders import DOCXLoader

        loader = DOCXLoader(Path(temp_docx), use_docling=False)
        docs = loader.load()

        assert docs[0].source == temp_docx

    @pytest.mark.asyncio
    async def test_aload_returns_same_as_load(self, temp_docx: str) -> None:
        """aload() returns same as load()."""
        from syrin.knowledge.loaders import DOCXLoader

        loader = DOCXLoader(temp_docx, use_docling=False)
        sync_docs = loader.load()
        async_docs = await loader.aload()

        assert len(sync_docs) == len(async_docs)
        assert sync_docs[0].content == async_docs[0].content
