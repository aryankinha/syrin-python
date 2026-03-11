"""Citation parsing and formatting for output — extracts and styles source references.

Citations are parsed from content (e.g. [Source: doc.pdf, Page 3]) and can be
reformatted as inline, footnotes, or appendix. Used by OutputConfig when
output_config.citation is set.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "Citation",
    "CitationConfig",
    "CitationStyle",
    "apply_citation_style",
    "parse_citations",
]


class CitationStyle(StrEnum):
    """How citations appear in the output.

    Attributes:
        INLINE: Keep as-is — [Source: doc.pdf, Page 3] in text.
        FOOTNOTE: Replace with [1], [2] and list sources at bottom.
        APPENDIX: Replace with [1], [2] and group all sources at end.
        NONE: Strip markers from text but still track in response.citations.
    """

    INLINE = "inline"
    FOOTNOTE = "footnote"
    APPENDIX = "appendix"
    NONE = "none"


@dataclass
class Citation:
    """A single citation extracted from content.

    Attributes:
        text: The cited snippet or sentence (content before the marker).
        source: Source document identifier (file path, URL).
        page: Page number in source document, or None.
        confidence: Optional confidence score (0–1). None when not available.
        index: Optional footnote/appendix index (1-based).
    """

    text: str
    source: str
    page: int | None
    confidence: float | None = None
    index: int | None = None


@dataclass
class CitationConfig:
    """Configuration for citation parsing and styling.

    Use with OutputConfig: output_config=OutputConfig(
        format=OutputFormat.PDF,
        citation=CitationConfig(style=CitationStyle.FOOTNOTE),
    )

    Attributes:
        style: How citations appear — INLINE, FOOTNOTE, APPENDIX, NONE.
        include_page: Include page number when rendering citation.
        include_confidence: Include confidence score when available.
    """

    style: CitationStyle = CitationStyle.INLINE
    include_page: bool = True
    include_confidence: bool = False


# Patterns for extracting [Source: X, Page Y] or [Source: X]
_SOURCE_PAGE_BRACKET = re.compile(
    r"\[Source:\s*([^,\]]+)(?:,\s*(?:Page|page|p\.)\s*(\d+))?\]",
    re.IGNORECASE,
)
_SOURCE_PAGE_PAREN = re.compile(
    r"\(Source:\s*([^,)]+)(?:,\s*(?:Page|page|p\.)\s*(\d+))?\)",
    re.IGNORECASE,
)


def _extract_cited_text(content: str, start: int, end: int) -> str:
    """Extract the sentence/fragment before a citation marker."""
    before = content[:start]
    # Find last sentence boundary
    match = re.search(r"[.!?\n]\s*([^.!?\n]*)$", before)
    if match:
        return match.group(1).strip()
    return before.strip()[-100:] if len(before) > 100 else before.strip()


def parse_citations(content: str) -> list[Citation]:
    """Extract citations from content.

    Recognizes [Source: doc.pdf, Page N], (Source: doc.pdf, Page N),
    [Source: doc.pdf, p. N], and [Source: doc.pdf] (no page).

    Args:
        content: Text that may contain citation markers.

    Returns:
        List of Citation objects in order of appearance.
    """
    if not content or not content.strip():
        return []

    found: list[tuple[int, Citation]] = []
    seen_starts: set[int] = set()

    for pattern in (_SOURCE_PAGE_BRACKET, _SOURCE_PAGE_PAREN):
        for match in pattern.finditer(content):
            start = match.start()
            if start in seen_starts:
                continue
            source = match.group(1).strip()
            page_str = match.group(2)
            page = int(page_str) if page_str else None
            text = _extract_cited_text(content, start, match.end())
            found.append((start, Citation(text=text, source=source, page=page)))
            seen_starts.add(start)

    found.sort(key=lambda x: x[0])
    return [
        Citation(
            text=c.text,
            source=c.source,
            page=c.page,
            confidence=c.confidence,
            index=i,
        )
        for i, (_, c) in enumerate(found, start=1)
    ]


def _format_citation_ref(c: Citation, config: CitationConfig) -> str:
    """Format a single citation for footer/appendix."""
    parts = [c.source]
    if config.include_page and c.page is not None:
        parts.append(f"page {c.page}")
    if config.include_confidence and c.confidence is not None:
        parts.append(f"confidence {c.confidence:.2f}")
    return ", ".join(parts)


def apply_citation_style(
    content: str,
    config: CitationConfig,
) -> tuple[str, list[Citation]]:
    """Parse citations and apply style transformation.

    Args:
        content: Raw content with citation markers.
        config: Citation configuration.

    Returns:
        (transformed_content, list of Citation objects)
    """
    citations = parse_citations(content)
    if not citations:
        return content, []

    if config.style == CitationStyle.INLINE:
        return content, citations

    if config.style == CitationStyle.NONE:
        result = _SOURCE_PAGE_BRACKET.sub("", content)
        result = _SOURCE_PAGE_PAREN.sub("", result)
        result = re.sub(r"\s{2,}", " ", result).strip()
        return result, citations

    # FOOTNOTE or APPENDIX: replace markers with [1], [2], etc. in document order
    matches: list[tuple[int, int, str]] = []  # (start, end, full_match)
    for pattern in (_SOURCE_PAGE_BRACKET, _SOURCE_PAGE_PAREN):
        for m in pattern.finditer(content):
            matches.append((m.start(), m.end(), m.group(0)))
    matches.sort(key=lambda x: x[0])

    # Build result by replacing in reverse order (so positions stay valid)
    result = content
    for i in range(len(matches) - 1, -1, -1):
        start, end, _ = matches[i]
        idx = i + 1
        result = result[:start] + f"[{idx}]" + result[end:]

    footer_lines = [
        f"[{i}] {_format_citation_ref(c, config)}" for i, c in enumerate(citations, start=1)
    ]

    if footer_lines:
        header = (
            "\n\n## References\n\n"
            if config.style == CitationStyle.APPENDIX
            else "\n\n---\n\n**References**\n\n"
        )
        result = result.rstrip() + header + "\n".join(footer_lines)

    return result, citations
