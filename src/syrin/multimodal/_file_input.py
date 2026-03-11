"""Internal module: file-to-message and PDF text extraction."""

from __future__ import annotations

import base64


def file_to_message(data: bytes, mimetype: str, role: str = "user") -> str:
    """Convert file bytes to a base64 data URL suitable as Message content.

    Args:
        data: Raw file bytes.
        mimetype: MIME type (e.g. image/png, application/pdf).
        role: Message role (user/system/assistant). Used by callers when
            building messages; does not affect the returned string.

    Returns:
        Data URL string: data:{mimetype};base64,{base64_data}

    Example:
        >>> file_to_message(b"hello", "text/plain", "user")
        'data:text/plain;base64,aGVsbG8='
    """
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mimetype};base64,{b64}"


def pdf_extract_text(data: bytes) -> str:
    """Extract text from PDF bytes using pypdf.

    Requires the pypdf package (pip install syrin[pdf]).

    Args:
        data: Raw PDF file bytes.

    Returns:
        Extracted text as string. Empty string for empty input.

    Raises:
        ImportError: When pypdf is not installed. Install with pip install syrin[pdf].
    """
    if not data:
        return ""
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise ImportError("syrin[pdf] required for PDF extraction. pip install syrin[pdf]") from e

    from io import BytesIO

    reader = PdfReader(BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n".join(parts)
