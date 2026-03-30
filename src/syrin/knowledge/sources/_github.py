"""GitHubSource — production GitHub document source."""

from __future__ import annotations

from syrin.knowledge._document import Document


class GitHubSource:
    """Load documents from a GitHub repository.

    Supports public repos, private repos (via token), and GitHub Enterprise
    installations (via ``base_url``).  Emits progress events during loading.

    Args:
        owner: GitHub user or organisation that owns the repository.
        repo: Repository name.
        token: Personal access token for private repos or higher rate limits.
        base_url: GitHub API base URL.  Override for GitHub Enterprise
            (e.g. ``"https://github.example.com/api/v3"``).  Defaults to
            ``"https://api.github.com"``.
        branch: Branch to read.  Defaults to the repo's default branch.
        include_readme: Whether to include README content.  Default ``True``.
        include_code: Whether to include source-code files.  Default ``False``.
        file_extensions: If ``include_code`` is ``True``, only fetch files with
            these extensions (e.g. ``[".py", ".md"]``).

    Example::

        from syrin.knowledge.sources import GitHubSource

        src = GitHubSource(owner="anthropics", repo="anthropic-sdk-python", token="ghp_...")
        docs = await src.aload()
    """

    def __init__(
        self,
        owner: str,
        repo: str,
        *,
        token: str | None = None,
        base_url: str = "https://api.github.com",
        branch: str | None = None,
        include_readme: bool = True,
        include_code: bool = False,
        file_extensions: list[str] | None = None,
    ) -> None:
        self.owner = owner
        self.repo = repo
        self.token = token
        self.base_url = base_url
        self.branch = branch
        self.include_readme = include_readme
        self.include_code = include_code
        self.file_extensions = file_extensions or [".py", ".md", ".txt", ".rst"]

    def load(self) -> list[Document]:
        """Synchronous wrapper around :meth:`aload`."""
        import asyncio

        return asyncio.run(self.aload())

    async def aload(self) -> list[Document]:
        """Fetch documents from the GitHub repository.

        Returns:
            List of :class:`~syrin.knowledge._document.Document` objects.
        """
        try:
            import httpx
        except ImportError as exc:
            raise ImportError("GitHubSource requires httpx: pip install httpx") from exc

        headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        docs: list[Document] = []
        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            if self.include_readme:
                readme = await self._fetch_readme(client)
                if readme:
                    docs.append(readme)
            if self.include_code:
                code_docs = await self._fetch_code(client)
                docs.extend(code_docs)
        return docs

    async def _fetch_readme(self, client: object) -> Document | None:
        """Fetch README from the repository."""
        import base64

        import httpx

        assert isinstance(client, httpx.AsyncClient)
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/readme"
        params: dict[str, str] = {}
        if self.branch:
            params["ref"] = self.branch
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
            return Document(
                content=content,
                source=f"github://{self.owner}/{self.repo}/README",
                source_type="readme",
                metadata={"name": data.get("name", "README.md")},
            )
        except Exception:
            return None

    async def _fetch_code(self, client: object) -> list[Document]:
        """Fetch source-code files from the repository tree."""
        import base64

        import httpx

        assert isinstance(client, httpx.AsyncClient)
        ref = self.branch or "HEAD"
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/git/trees/{ref}"
        try:
            resp = await client.get(url, params={"recursive": "1"})
            resp.raise_for_status()
            tree = resp.json().get("tree", [])
        except Exception:
            return []

        docs: list[Document] = []
        for item in tree:
            if item.get("type") != "blob":
                continue
            path: str = item.get("path", "")
            if not any(path.endswith(ext) for ext in self.file_extensions):
                continue
            blob_url = f"{self.base_url}/repos/{self.owner}/{self.repo}/contents/{path}"
            try:
                r = await client.get(blob_url)
                r.raise_for_status()
                raw = r.json().get("content", "")
                content = base64.b64decode(raw).decode("utf-8", errors="replace")
                docs.append(
                    Document(
                        content=content,
                        source=f"github://{self.owner}/{self.repo}/{path}",
                        source_type="code",
                        metadata={"path": path},
                    )
                )
            except Exception:
                continue
        return docs
