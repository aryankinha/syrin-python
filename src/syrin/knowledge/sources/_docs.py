"""DocsSource — URL crawler with depth control and domain scoping."""

from __future__ import annotations

from syrin.knowledge._document import Document


class DocsSource:
    """Crawl a documentation site and load pages as documents.

    Follows links up to ``depth`` levels deep, restricted to ``domain_scope``
    when set to avoid crawling off-site.

    Args:
        url: Root URL to start crawling from.
        depth: Maximum link-follow depth.  Default ``2``.
        domain_scope: Only follow links within this domain.  If ``None``
            (default) the domain of ``url`` is used.
        max_pages: Maximum number of pages to fetch.  Default ``100``.

    Example::

        from syrin.knowledge.sources import DocsSource

        src = DocsSource(url="https://docs.syrin.dev", depth=3)
        docs = await src.aload()
    """

    def __init__(
        self,
        url: str,
        *,
        depth: int = 2,
        domain_scope: str | None = None,
        max_pages: int = 100,
    ) -> None:
        self.url = url
        self.depth = depth
        self.domain_scope = domain_scope
        self.max_pages = max_pages

    def load(self) -> list[Document]:
        """Synchronous wrapper around :meth:`aload`."""
        import asyncio

        return asyncio.run(self.aload())

    async def aload(self) -> list[Document]:
        """Crawl pages starting at :attr:`url` up to :attr:`depth` levels.

        Returns:
            List of :class:`~syrin.knowledge._document.Document` objects.
        """
        from urllib.parse import urlparse

        try:
            import httpx
        except ImportError as exc:
            raise ImportError("DocsSource requires httpx: pip install httpx") from exc

        root_parsed = urlparse(self.url)
        scope = self.domain_scope or root_parsed.netloc

        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(self.url, 0)]
        docs: list[Document] = []

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            while queue and len(docs) < self.max_pages:
                current_url, current_depth = queue.pop(0)
                if current_url in visited:
                    continue
                visited.add(current_url)

                try:
                    resp = await client.get(current_url)
                    resp.raise_for_status()
                    content_type = resp.headers.get("content-type", "")
                    if "text" not in content_type and "html" not in content_type:
                        continue
                    text = _strip_html(resp.text)
                    docs.append(
                        Document(
                            content=text,
                            source=current_url,
                            source_type="docs",
                        )
                    )
                except Exception:
                    continue

                if current_depth < self.depth:
                    links = _extract_links(resp.text, current_url)
                    for link in links:
                        parsed = urlparse(link)
                        if parsed.netloc == scope and link not in visited:
                            queue.append((link, current_depth + 1))

        return docs


def _strip_html(html: str) -> str:
    """Remove HTML tags and return plain text."""
    import re

    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_links(html: str, base_url: str) -> list[str]:
    """Extract all href links from an HTML page."""
    import re
    from urllib.parse import urljoin, urlparse

    hrefs = re.findall(r'href=["\']([^"\'#?]+)["\']', html)
    links: list[str] = []
    for href in hrefs:
        full = urljoin(base_url, href)
        parsed = urlparse(full)
        if parsed.scheme in ("http", "https"):
            links.append(full)
    return links
