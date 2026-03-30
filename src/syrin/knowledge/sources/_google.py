"""GoogleDocsSource and GoogleSheetsSource — load from Google Workspace."""

from __future__ import annotations

from syrin.knowledge._document import Document


class GoogleDocsSource:
    """Load a Google Doc as a document.

    Requires the Google Docs API.  Authentication is handled via service-account
    credentials (``credentials_path``) or an existing OAuth2 token
    (``access_token``).

    Args:
        document_id: The Google Doc ID (from the URL).
        credentials_path: Path to a service-account JSON key file.
        access_token: Existing OAuth2 access token (alternative to credentials).

    Example::

        from syrin.knowledge.sources import GoogleDocsSource

        src = GoogleDocsSource(
            document_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms",
            credentials_path="service_account.json",
        )
        docs = await src.aload()
    """

    def __init__(
        self,
        document_id: str,
        *,
        credentials_path: str | None = None,
        access_token: str | None = None,
    ) -> None:
        self.document_id = document_id
        self.credentials_path = credentials_path
        self.access_token = access_token

    def load(self) -> list[Document]:
        """Synchronous wrapper around :meth:`aload`."""
        import asyncio

        return asyncio.run(self.aload())

    async def aload(self) -> list[Document]:
        """Fetch the Google Doc content.

        Returns:
            A single-element list containing the document.

        Raises:
            ImportError: If ``google-api-python-client`` is not installed.
            RuntimeError: If no credentials are provided.
        """
        if not self.credentials_path and not self.access_token:
            raise RuntimeError("GoogleDocsSource requires either credentials_path or access_token")
        try:
            import httpx
        except ImportError as exc:
            raise ImportError("GoogleDocsSource requires httpx") from exc

        headers: dict[str, str] = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        elif self.credentials_path:
            # Attempt service-account token exchange
            token = await _get_service_account_token(
                self.credentials_path, "https://www.googleapis.com/auth/documents.readonly"
            )
            headers["Authorization"] = f"Bearer {token}"

        url = f"https://docs.googleapis.com/v1/documents/{self.document_id}"
        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            content = _extract_doc_text(data)
            return [
                Document(
                    content=content,
                    source=f"gdoc://{self.document_id}",
                    source_type="google_doc",
                    metadata={"title": data.get("title", "")},
                )
            ]


class GoogleSheetsSource:
    """Load a Google Sheets spreadsheet as documents.

    Each row is loaded as a document (or a range of cells if ``sheet_range``
    is specified).

    Args:
        spreadsheet_id: The spreadsheet ID (from the URL).
        sheet_range: A1 notation range, e.g. ``"Sheet1!A1:D10"``.
        credentials_path: Path to a service-account JSON key file.
        access_token: Existing OAuth2 access token.

    Example::

        from syrin.knowledge.sources import GoogleSheetsSource

        src = GoogleSheetsSource(
            spreadsheet_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms",
            sheet_range="Sheet1!A1:Z",
            access_token="ya29...",
        )
        docs = await src.aload()
    """

    def __init__(
        self,
        spreadsheet_id: str,
        *,
        sheet_range: str = "Sheet1",
        credentials_path: str | None = None,
        access_token: str | None = None,
    ) -> None:
        self.spreadsheet_id = spreadsheet_id
        self.sheet_range = sheet_range
        self.credentials_path = credentials_path
        self.access_token = access_token

    def load(self) -> list[Document]:
        """Synchronous wrapper around :meth:`aload`."""
        import asyncio

        return asyncio.run(self.aload())

    async def aload(self) -> list[Document]:
        """Fetch the spreadsheet data.

        Returns:
            List of documents, one per row.
        """
        if not self.credentials_path and not self.access_token:
            raise RuntimeError(
                "GoogleSheetsSource requires either credentials_path or access_token"
            )
        try:
            import httpx
        except ImportError as exc:
            raise ImportError("GoogleSheetsSource requires httpx") from exc

        headers: dict[str, str] = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        elif self.credentials_path:
            token = await _get_service_account_token(
                self.credentials_path,
                "https://www.googleapis.com/auth/spreadsheets.readonly",
            )
            headers["Authorization"] = f"Bearer {token}"

        import urllib.parse

        url = (
            f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}"
            f"/values/{urllib.parse.quote(self.sheet_range)}"
        )
        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            rows = data.get("values", [])
            docs: list[Document] = []
            for i, row in enumerate(rows):
                text = "\t".join(str(cell) for cell in row)
                docs.append(
                    Document(
                        content=text,
                        source=f"gsheets://{self.spreadsheet_id}/{self.sheet_range}",
                        source_type="google_sheet",
                        metadata={"row": i},
                    )
                )
            return docs


def _extract_doc_text(data: dict[str, object]) -> str:
    """Extract plain text from a Google Docs API response."""
    parts: list[str] = []
    body = data.get("body", {})
    if isinstance(body, dict):
        for element in body.get("content", []):
            if isinstance(element, dict):
                para = element.get("paragraph")
                if isinstance(para, dict):
                    for el in para.get("elements", []):
                        if isinstance(el, dict):
                            run = el.get("textRun")
                            if isinstance(run, dict):
                                parts.append(str(run.get("content", "")))
    return "".join(parts)


async def _get_service_account_token(credentials_path: str, scope: str) -> str:
    """Exchange service-account JSON key for an access token."""
    import json
    import time

    try:
        import httpx
        import jwt  # type: ignore[import-untyped,unused-ignore,import-not-found]
    except ImportError as exc:
        raise ImportError(
            "Service account auth requires PyJWT and httpx: pip install PyJWT httpx"
        ) from exc

    with open(credentials_path) as f:
        creds = json.load(f)

    now = int(time.time())
    payload = {
        "iss": creds["client_email"],
        "scope": scope,
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
    }
    assertion = jwt.encode(payload, creds["private_key"], algorithm="RS256")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            },
        )
        resp.raise_for_status()
        return str(resp.json()["access_token"])
