"""ConfluenceSource — load documents from Atlassian Confluence."""

from __future__ import annotations

from syrin.knowledge._document import Document


class ConfluenceSource:
    """Load pages from an Atlassian Confluence space.

    Args:
        base_url: Confluence base URL, e.g. ``"https://mycompany.atlassian.net/wiki"``.
        space_key: The Confluence space key to read from.
        token: Atlassian API token (personal access token or basic-auth password).
        email: Email for basic-auth (used with ``token`` for cloud instances).
        label_filter: Only include pages that have all of these labels.
        max_pages: Maximum number of pages to fetch.  Default ``200``.

    Example::

        from syrin.knowledge.sources import ConfluenceSource

        src = ConfluenceSource(
            base_url="https://myco.atlassian.net/wiki",
            space_key="ENG",
            token="ATATT3xFfGF0...",
            email="user@example.com",
        )
        docs = await src.aload()
    """

    def __init__(
        self,
        base_url: str,
        space_key: str,
        token: str,
        *,
        email: str | None = None,
        label_filter: list[str] | None = None,
        max_pages: int = 200,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.space_key = space_key
        self.token = token
        self.email = email
        self.label_filter = label_filter or []
        self.max_pages = max_pages

    def load(self) -> list[Document]:
        """Synchronous wrapper around :meth:`aload`."""
        import asyncio

        return asyncio.run(self.aload())

    async def aload(self) -> list[Document]:
        """Fetch pages from the Confluence space.

        Returns:
            List of :class:`~syrin.knowledge._document.Document` objects.
        """
        import base64

        try:
            import httpx
        except ImportError as exc:
            raise ImportError("ConfluenceSource requires httpx: pip install httpx") from exc

        if self.email:
            creds = base64.b64encode(f"{self.email}:{self.token}".encode()).decode()
            auth_header = f"Basic {creds}"
        else:
            auth_header = f"Bearer {self.token}"

        headers = {
            "Authorization": auth_header,
            "Accept": "application/json",
        }

        url = f"{self.base_url}/rest/api/content"
        params: dict[str, str | int] = {
            "spaceKey": self.space_key,
            "type": "page",
            "expand": "body.storage,metadata.labels",
            "limit": min(50, self.max_pages),
            "start": 0,
        }
        if self.label_filter:
            params["label"] = ",".join(self.label_filter)

        docs: list[Document] = []
        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            while len(docs) < self.max_pages:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", [])
                for page in results:
                    body = page.get("body", {}).get("storage", {}).get("value", "")
                    text = _strip_html(body)
                    docs.append(
                        Document(
                            content=text,
                            source=f"confluence://{self.space_key}/{page.get('id', '')}",
                            source_type="confluence",
                            metadata={"title": page.get("title", "")},
                        )
                    )
                    if len(docs) >= self.max_pages:
                        break
                next_start = data.get("_links", {}).get("next")
                if not next_start or not results:
                    break
                params["start"] = int(params["start"]) + len(results)

        return docs


def _strip_html(html: str) -> str:
    import re

    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&[a-z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()
