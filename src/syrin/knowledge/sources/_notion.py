"""NotionSource — load documents from Notion databases and pages."""

from __future__ import annotations

from syrin.knowledge._document import Document


class NotionSource:
    """Load pages from a Notion database.

    Supports recursive page traversal to include sub-pages and nested content.

    Args:
        database_id: The Notion database ID to query.
        token: Notion integration secret (``secret_xxx...``).
        recursive: If ``True``, recursively fetch child pages.  Default ``False``.
        filter_formula: Optional Notion filter object (dict) to narrow results.

    Example::

        from syrin.knowledge.sources import NotionSource

        src = NotionSource(
            database_id="abc123...",
            token="secret_xyz...",
            recursive=True,
        )
        docs = await src.aload()
    """

    def __init__(
        self,
        database_id: str,
        token: str,
        *,
        recursive: bool = False,
        filter_formula: dict[str, object] | None = None,
    ) -> None:
        self.database_id = database_id
        self.token = token
        self.recursive = recursive
        self.filter_formula = filter_formula

    def load(self) -> list[Document]:
        """Synchronous wrapper around :meth:`aload`."""
        import asyncio

        return asyncio.run(self.aload())

    async def aload(self) -> list[Document]:
        """Fetch pages from the Notion database.

        Returns:
            List of :class:`~syrin.knowledge._document.Document` objects.
        """
        try:
            import httpx
        except ImportError as exc:
            raise ImportError("NotionSource requires httpx: pip install httpx") from exc

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

        docs: list[Document] = []
        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            await self._fetch_database(client, self.database_id, docs)
        return docs

    async def _fetch_database(
        self,
        client: object,
        database_id: str,
        docs: list[Document],
    ) -> None:
        import httpx

        assert isinstance(client, httpx.AsyncClient)

        body: dict[str, object] = {}
        if self.filter_formula:
            body["filter"] = self.filter_formula

        url = f"https://api.notion.com/v1/databases/{database_id}/query"
        start_cursor: str | None = None
        while True:
            if start_cursor:
                body["start_cursor"] = start_cursor
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()
            for page in data.get("results", []):
                page_id: str = page.get("id", "")
                title = _extract_page_title(page)
                content = await self._fetch_page_content(client, page_id)
                docs.append(
                    Document(
                        content=content,
                        source=f"notion://{page_id}",
                        source_type="notion",
                        metadata={"title": title},
                    )
                )
                if self.recursive:
                    await self._fetch_children(client, page_id, docs)
            if not data.get("has_more"):
                break
            start_cursor = data.get("next_cursor")

    async def _fetch_page_content(self, client: object, page_id: str) -> str:
        import httpx

        assert isinstance(client, httpx.AsyncClient)

        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            blocks = resp.json().get("results", [])
            return _blocks_to_text(blocks)
        except Exception:
            return ""

    async def _fetch_children(
        self,
        client: object,
        page_id: str,
        docs: list[Document],
    ) -> None:
        import httpx

        assert isinstance(client, httpx.AsyncClient)

        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            for block in resp.json().get("results", []):
                if block.get("type") == "child_page":
                    child_id = block.get("id", "")
                    content = await self._fetch_page_content(client, child_id)
                    docs.append(
                        Document(
                            content=content,
                            source=f"notion://{child_id}",
                            source_type="notion",
                        )
                    )
        except Exception:
            pass


def _extract_page_title(page: dict[str, object]) -> str:
    props = page.get("properties", {})
    if isinstance(props, dict):
        for _key, val in props.items():
            if isinstance(val, dict) and val.get("type") == "title":
                titles = val.get("title", [])
                if isinstance(titles, list) and titles:
                    return str(titles[0].get("plain_text", ""))
    return ""


def _blocks_to_text(blocks: list[object]) -> str:
    parts: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        btype = block.get("type", "")
        inner = block.get(btype, {})
        if isinstance(inner, dict):
            for rt in inner.get("rich_text", []):
                if isinstance(rt, dict):
                    parts.append(rt.get("plain_text", ""))
    return " ".join(parts)
