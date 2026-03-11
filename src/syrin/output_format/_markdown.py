"""Markdown output formatter."""

from __future__ import annotations


class MarkdownFormatter:
    """Formatter for Markdown (.md) files. Adds optional title as first line."""

    def format(self, content: str, *, metadata: dict[str, object] | None = None) -> bytes:
        """Return content as Markdown with optional title header."""
        if not metadata or "title" not in metadata:
            return content.encode("utf-8")
        title = metadata.get("title")
        if not title or not isinstance(title, str):
            return content.encode("utf-8")
        header = f"# {title}\n\n"
        return (header + content).encode("utf-8")

    def extension(self) -> str:
        return "md"
