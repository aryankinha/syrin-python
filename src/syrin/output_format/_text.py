"""Plain text output formatter."""

from __future__ import annotations


class TextFormatter:
    """Formatter for plain .txt files. No extra dependencies."""

    def format(self, content: str, *, metadata: dict[str, object] | None = None) -> bytes:
        """Return content as UTF-8 bytes."""
        return content.encode("utf-8")

    def extension(self) -> str:
        return "txt"
