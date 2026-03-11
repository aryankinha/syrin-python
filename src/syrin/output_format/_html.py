"""HTML output formatter."""

from __future__ import annotations

import html


def _escape_html(text: str) -> str:
    """Escape HTML entities in text."""
    return html.escape(text)


class HTMLFormatter:
    """Formatter for HTML documents. Wraps content in minimal styled document."""

    def format(self, content: str, *, metadata: dict[str, object] | None = None) -> bytes:
        """Wrap content in HTML document with basic styling."""
        title = ""
        if metadata and "title" in metadata:
            t = metadata["title"]
            if isinstance(t, str) and t:
                title = _escape_html(t)

        doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title or "Document"}</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; line-height: 1.6; max-width: 65ch; margin: 0 auto; padding: 2rem; }}
        table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
        th, td {{ border: 1px solid #ddd; padding: 0.5rem 0.75rem; text-align: left; }}
        th {{ background: #f5f5f5; }}
        pre {{ background: #f5f5f5; padding: 1rem; overflow-x: auto; }}
        code {{ font-family: ui-monospace, monospace; }}
    </style>
</head>
<body>
<main>
{_paragraphs_to_html(content)}
</main>
</body>
</html>"""
        return doc.encode("utf-8")

    def extension(self) -> str:
        return "html"


def _paragraphs_to_html(content: str) -> str:
    """Convert plain text/markdown-like content to HTML paragraphs and tables."""
    lines = content.split("\n")
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Detect markdown table (starts with |)
        if line.strip().startswith("|") and "|" in line:
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].split("|")[1:-1]]
                rows.append(cells)
                i += 1
            if rows:
                result.append(_table_to_html(rows))
            continue
        # Regular paragraph
        if line.strip():
            escaped = _escape_html(line)
            result.append(f"<p>{escaped}</p>")
        else:
            result.append("<br>")
        i += 1
    return "\n".join(result)


def _table_to_html(rows: list[list[str]]) -> str:
    """Convert rows to HTML table. First row as header if separator row follows."""
    if not rows:
        return ""
    # Check for markdown separator row (|---|---|)
    is_header = len(rows) >= 2 and all(cell.replace("-", "").strip() == "" for cell in rows[1])
    parts: list[str] = ["<table>"]
    start = 0
    if is_header and len(rows) >= 2:
        parts.append("<thead><tr>")
        for cell in rows[0]:
            parts.append(f"<th>{_escape_html(cell)}</th>")
        parts.append("</tr></thead><tbody>")
        start = 2
    else:
        parts.append("<tbody>")
    for row in rows[start:]:
        parts.append("<tr>")
        for cell in row:
            parts.append(f"<td>{_escape_html(cell)}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table>")
    return "".join(parts)
