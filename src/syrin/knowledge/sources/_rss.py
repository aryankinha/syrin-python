"""RSSSource and BlogSource — load from RSS feeds and sitemaps."""

from __future__ import annotations

from syrin.knowledge._document import Document


class RSSSource:
    """Load articles from an RSS or Atom feed.

    Args:
        feed_url: URL of the RSS/Atom feed.
        max_items: Maximum number of feed items to load.  Default ``50``.
        fetch_full_content: If ``True``, follow each item link and fetch
            the full article text.  Default ``False`` (use feed summary).

    Example::

        from syrin.knowledge.sources import RSSSource

        src = RSSSource(feed_url="https://blog.example.com/rss.xml", max_items=20)
        docs = await src.aload()
    """

    def __init__(
        self,
        feed_url: str,
        *,
        max_items: int = 50,
        fetch_full_content: bool = False,
    ) -> None:
        self.feed_url = feed_url
        self.max_items = max_items
        self.fetch_full_content = fetch_full_content

    def load(self) -> list[Document]:
        """Synchronous wrapper around :meth:`aload`."""
        import asyncio

        return asyncio.run(self.aload())

    async def aload(self) -> list[Document]:
        """Fetch feed items and return them as documents.

        Returns:
            List of :class:`~syrin.knowledge._document.Document` objects.
        """
        try:
            import httpx
        except ImportError as exc:
            raise ImportError("RSSSource requires httpx: pip install httpx") from exc

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(self.feed_url)
            resp.raise_for_status()
            items = _parse_feed(resp.text)

        docs: list[Document] = []
        for item in items[: self.max_items]:
            content = item.get("summary", "") or item.get("title", "")
            docs.append(
                Document(
                    content=content,
                    source=item.get("link", self.feed_url),
                    source_type="rss",
                    metadata={
                        "title": item.get("title", ""),
                        "published": item.get("published", ""),
                    },
                )
            )
        return docs


class BlogSource:
    """Load blog posts from a sitemap URL.

    Args:
        sitemap_url: URL of the XML sitemap.
        max_pages: Maximum number of blog posts to fetch.  Default ``100``.

    Example::

        from syrin.knowledge.sources import BlogSource

        src = BlogSource(sitemap_url="https://blog.example.com/sitemap.xml")
        docs = await src.aload()
    """

    def __init__(
        self,
        sitemap_url: str,
        *,
        max_pages: int = 100,
    ) -> None:
        self.sitemap_url = sitemap_url
        self.max_pages = max_pages

    def load(self) -> list[Document]:
        """Synchronous wrapper around :meth:`aload`."""
        import asyncio

        return asyncio.run(self.aload())

    async def aload(self) -> list[Document]:
        """Crawl the sitemap and return page content as documents.

        Returns:
            List of :class:`~syrin.knowledge._document.Document` objects.
        """
        try:
            import httpx
        except ImportError as exc:
            raise ImportError("BlogSource requires httpx: pip install httpx") from exc

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(self.sitemap_url)
            resp.raise_for_status()
            urls = _parse_sitemap(resp.text)

        docs: list[Document] = []
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            for url in urls[: self.max_pages]:
                try:
                    r = await client.get(url)
                    r.raise_for_status()
                    text = _strip_html(r.text)
                    docs.append(
                        Document(
                            content=text,
                            source=url,
                            source_type="blog",
                        )
                    )
                except Exception:
                    continue
        return docs


def _parse_feed(xml: str) -> list[dict[str, str]]:
    """Parse RSS 2.0 or Atom feed XML into a list of item dicts."""
    import re

    items: list[dict[str, str]] = []
    # Try RSS <item> blocks first
    item_blocks = re.findall(r"<item>(.*?)</item>", xml, re.DOTALL)
    if not item_blocks:
        # Try Atom <entry> blocks
        item_blocks = re.findall(r"<entry>(.*?)</entry>", xml, re.DOTALL)
    for block in item_blocks:
        item: dict[str, str] = {}
        for tag in ("title", "link", "description", "summary", "published", "pubDate"):
            m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", block, re.DOTALL)
            if m:
                item[tag if tag != "pubDate" else "published"] = re.sub(
                    r"<[^>]+>", "", m.group(1)
                ).strip()
        items.append(item)
    return items


def _parse_sitemap(xml: str) -> list[str]:
    """Extract all <loc> URLs from a sitemap."""
    import re

    return re.findall(r"<loc>(https?://[^<]+)</loc>", xml)


def _strip_html(html: str) -> str:
    import re

    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()
