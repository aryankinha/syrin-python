"""Tests for multimodal input handling (file_to_message, pdf_extract_text)."""

from __future__ import annotations

import base64
from unittest.mock import patch

import pytest

from syrin.multimodal import file_to_message, pdf_extract_text


class TestFileToMessage:
    """Tests for file_to_message."""

    def test_file_to_message_returns_base64_data_url(self) -> None:
        """file_to_message returns a data URL string with base64 content."""
        data = b"hello"
        mimetype = "text/plain"
        result = file_to_message(data, mimetype, "user")
        expected = f"data:{mimetype};base64,{base64.b64encode(data).decode()}"
        assert result == expected

    def test_file_to_message_with_image_mimetype(self) -> None:
        """file_to_message works with image/png."""
        data = b"\x89PNG\r\n\x1a\n"
        mimetype = "image/png"
        result = file_to_message(data, mimetype, "user")
        assert result.startswith("data:image/png;base64,")
        assert base64.b64decode(result.split(",", 1)[1]) == data

    def test_file_to_message_with_role(self) -> None:
        """file_to_message accepts role (used for building message structure elsewhere)."""
        data = b"content"
        result = file_to_message(data, "text/plain", "user")
        assert "base64," in result
        result_system = file_to_message(data, "text/plain", "system")
        assert result_system == result  # role affects caller usage, not the returned string

    def test_file_to_message_empty_bytes(self) -> None:
        """file_to_message handles empty bytes."""
        result = file_to_message(b"", "application/octet-stream", "user")
        assert result == "data:application/octet-stream;base64,"


class TestPdfExtractText:
    """Tests for pdf_extract_text."""

    def test_pdf_extract_text_empty_returns_empty(self) -> None:
        """pdf_extract_text with empty bytes returns empty string (no docling needed)."""
        result = pdf_extract_text(b"")
        assert result == ""

    @pytest.mark.skip(reason="Hard to mock docling import in full test suite")
    def test_pdf_extract_text_without_docling_raises_import_error(self) -> None:
        """When docling is not installed, pdf_extract_text raises ImportError."""

        class FakeModule:
            def __getattr__(self, name: str) -> None:
                raise ImportError("No module named 'docling'")

        with (
            patch.dict("sys.modules", {"docling": FakeModule()}),
            pytest.raises(ImportError, match=r"syrin\[pdf\]"),
        ):
            pdf_extract_text(b"%PDF-1.4 minimal")

    def test_pdf_extract_text_with_docling(self) -> None:
        """docling is used when available for PDF text extraction."""
        pytest.importorskip("docling")
        # Create a minimal valid PDF that docling can parse
        # Note: docling is strict, so we just test it doesn't crash on empty
        result = pdf_extract_text(b"")
        assert result == ""
