"""CSV loader. No optional dependencies."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from syrin.knowledge._document import Document, DocumentMetadata


class CSVLoader:
    """Load CSV files. Each chunk of rows becomes a Document.

    Supports configurable rows_per_document. When None, the entire file
    is one Document. Header row is included in each chunk.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        rows_per_document: int | None = None,
        encoding: str = "utf-8",
    ) -> None:
        """Initialize CSVLoader.

        Args:
            path: Path to the CSV file.
            rows_per_document: Rows per Document. None = entire file as one Document.
            encoding: File encoding. Default utf-8.
        """
        self._path = Path(path)
        self._rows_per_document = rows_per_document
        self._encoding = encoding

    @property
    def path(self) -> Path:
        """Path to the CSV file."""
        return self._path

    def load(self) -> list[Document]:
        """Load the CSV file.

        Returns:
            List of Documents. When rows_per_document is set, each chunk
            is a Document with header preserved.
        """
        if not self._path.exists():
            raise FileNotFoundError(f"CSV file does not exist: {self._path}")

        content = self._path.read_text(encoding=self._encoding)
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        if not rows:
            return [
                Document(
                    content="",
                    source=str(self._path),
                    source_type="csv",
                    metadata={},
                )
            ]

        header = rows[0]
        data_rows = rows[1:]

        if self._rows_per_document is None:
            text = _rows_to_text([header] + data_rows)
            return [
                Document(
                    content=text,
                    source=str(self._path),
                    source_type="csv",
                    metadata={"total_rows": len(data_rows)},
                )
            ]

        docs: list[Document] = []
        chunk_size = self._rows_per_document
        for i in range(0, len(data_rows), chunk_size):
            chunk = [header] + data_rows[i : i + chunk_size]
            text = _rows_to_text(chunk)
            meta: DocumentMetadata = {
                "chunk_index": i // chunk_size,
                "row_start": i + 1,
                "row_end": min(i + chunk_size, len(data_rows)),
            }
            docs.append(
                Document(
                    content=text,
                    source=str(self._path),
                    source_type="csv",
                    metadata=meta,
                )
            )
        return docs

    async def aload(self) -> list[Document]:
        """Load CSV asynchronously."""
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.load)


def _rows_to_text(rows: list[list[str]]) -> str:
    """Convert rows to readable text (header + rows as lines)."""
    if not rows:
        return ""
    lines = [",".join(cell.replace(",", ";") for cell in row) for row in rows]
    return "\n".join(lines)


__all__ = ["CSVLoader"]
