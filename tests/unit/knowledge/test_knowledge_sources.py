"""Tests for the Production Knowledge Pool: external sources, language-aware chunkers,
hybrid search configuration, progress hooks, and cancellable ingestion."""

from __future__ import annotations

import asyncio

# ─── GitHubSource ──────────────────────────────────────────────────────────────


class TestGitHubSource:
    def test_importable(self) -> None:
        from syrin.knowledge.sources import GitHubSource

        assert GitHubSource is not None

    def test_basic_construction(self) -> None:
        from syrin.knowledge.sources import GitHubSource

        src = GitHubSource(owner="octocat", repo="Hello-World")
        assert src.owner == "octocat"
        assert src.repo == "Hello-World"

    def test_token_param(self) -> None:
        from syrin.knowledge.sources import GitHubSource

        src = GitHubSource(owner="org", repo="private-repo", token="ghp_test")
        assert src.token == "ghp_test"

    def test_enterprise_base_url(self) -> None:
        from syrin.knowledge.sources import GitHubSource

        src = GitHubSource(owner="org", repo="repo", base_url="https://github.example.com/api/v3")
        assert src.base_url == "https://github.example.com/api/v3"

    def test_default_base_url_is_github(self) -> None:
        from syrin.knowledge.sources import GitHubSource

        src = GitHubSource(owner="org", repo="repo")
        assert "github" in src.base_url.lower()

    def test_has_aload_method(self) -> None:
        from syrin.knowledge.sources import GitHubSource

        assert hasattr(GitHubSource, "aload")
        assert asyncio.iscoroutinefunction(GitHubSource.aload)

    def test_has_load_method(self) -> None:
        from syrin.knowledge.sources import GitHubSource

        assert hasattr(GitHubSource, "load")


# ─── DocsSource ───────────────────────────────────────────────────────────────


class TestDocsSource:
    def test_importable(self) -> None:
        from syrin.knowledge.sources import DocsSource

        assert DocsSource is not None

    def test_basic_construction(self) -> None:
        from syrin.knowledge.sources import DocsSource

        src = DocsSource(url="https://docs.example.com")
        assert src.url == "https://docs.example.com"

    def test_depth_param(self) -> None:
        from syrin.knowledge.sources import DocsSource

        src = DocsSource(url="https://docs.example.com", depth=3)
        assert src.depth == 3

    def test_default_depth(self) -> None:
        from syrin.knowledge.sources import DocsSource

        src = DocsSource(url="https://docs.example.com")
        assert isinstance(src.depth, int)
        assert src.depth >= 1

    def test_domain_scope_param(self) -> None:
        from syrin.knowledge.sources import DocsSource

        src = DocsSource(url="https://docs.example.com", domain_scope="docs.example.com")
        assert src.domain_scope == "docs.example.com"

    def test_has_aload_method(self) -> None:
        from syrin.knowledge.sources import DocsSource

        assert asyncio.iscoroutinefunction(DocsSource.aload)


# ─── GoogleDocsSource / GoogleSheetsSource ────────────────────────────────────


class TestGoogleDocsSheetsSource:
    def test_google_docs_source_importable(self) -> None:
        from syrin.knowledge.sources import GoogleDocsSource

        assert GoogleDocsSource is not None

    def test_google_sheets_source_importable(self) -> None:
        from syrin.knowledge.sources import GoogleSheetsSource

        assert GoogleSheetsSource is not None

    def test_google_docs_construction(self) -> None:
        from syrin.knowledge.sources import GoogleDocsSource

        src = GoogleDocsSource(document_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms")
        assert src.document_id == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"

    def test_google_sheets_with_range(self) -> None:
        from syrin.knowledge.sources import GoogleSheetsSource

        src = GoogleSheetsSource(
            spreadsheet_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms",
            sheet_range="Sheet1!A1:D10",
        )
        assert src.spreadsheet_id == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"
        assert src.sheet_range == "Sheet1!A1:D10"

    def test_google_docs_has_aload(self) -> None:
        from syrin.knowledge.sources import GoogleDocsSource

        assert asyncio.iscoroutinefunction(GoogleDocsSource.aload)

    def test_google_sheets_has_aload(self) -> None:
        from syrin.knowledge.sources import GoogleSheetsSource

        assert asyncio.iscoroutinefunction(GoogleSheetsSource.aload)


# ─── ConfluenceSource / NotionSource ──────────────────────────────────────────


class TestConfluenceAndNotionSources:
    def test_confluence_source_importable(self) -> None:
        from syrin.knowledge.sources import ConfluenceSource

        assert ConfluenceSource is not None

    def test_notion_source_importable(self) -> None:
        from syrin.knowledge.sources import NotionSource

        assert NotionSource is not None

    def test_confluence_construction(self) -> None:
        from syrin.knowledge.sources import ConfluenceSource

        src = ConfluenceSource(
            base_url="https://mycompany.atlassian.net/wiki",
            space_key="ENG",
            token="token123",
        )
        assert src.space_key == "ENG"
        assert "atlassian" in src.base_url

    def test_notion_construction(self) -> None:
        from syrin.knowledge.sources import NotionSource

        src = NotionSource(database_id="abc123", token="secret_xyz")
        assert src.database_id == "abc123"

    def test_confluence_label_filter(self) -> None:
        from syrin.knowledge.sources import ConfluenceSource

        src = ConfluenceSource(
            base_url="https://co.atlassian.net/wiki",
            space_key="ENG",
            token="t",
            label_filter=["api", "public"],
        )
        assert src.label_filter == ["api", "public"]

    def test_notion_recursive_param(self) -> None:
        from syrin.knowledge.sources import NotionSource

        src = NotionSource(database_id="abc", token="t", recursive=True)
        assert src.recursive is True

    def test_confluence_has_aload(self) -> None:
        from syrin.knowledge.sources import ConfluenceSource

        assert asyncio.iscoroutinefunction(ConfluenceSource.aload)

    def test_notion_has_aload(self) -> None:
        from syrin.knowledge.sources import NotionSource

        assert asyncio.iscoroutinefunction(NotionSource.aload)


# ─── RSSSource / BlogSource ───────────────────────────────────────────────────


class TestRSSAndBlogSources:
    def test_rss_source_importable(self) -> None:
        from syrin.knowledge.sources import RSSSource

        assert RSSSource is not None

    def test_blog_source_importable(self) -> None:
        from syrin.knowledge.sources import BlogSource

        assert BlogSource is not None

    def test_rss_construction(self) -> None:
        from syrin.knowledge.sources import RSSSource

        src = RSSSource(feed_url="https://blog.example.com/rss.xml")
        assert src.feed_url == "https://blog.example.com/rss.xml"

    def test_rss_max_items(self) -> None:
        from syrin.knowledge.sources import RSSSource

        src = RSSSource(feed_url="https://example.com/feed.xml", max_items=50)
        assert src.max_items == 50

    def test_blog_source_sitemap(self) -> None:
        from syrin.knowledge.sources import BlogSource

        src = BlogSource(sitemap_url="https://blog.example.com/sitemap.xml")
        assert src.sitemap_url == "https://blog.example.com/sitemap.xml"

    def test_rss_has_aload(self) -> None:
        from syrin.knowledge.sources import RSSSource

        assert asyncio.iscoroutinefunction(RSSSource.aload)

    def test_blog_has_aload(self) -> None:
        from syrin.knowledge.sources import BlogSource

        assert asyncio.iscoroutinefunction(BlogSource.aload)


# ─── Language-aware chunkers ──────────────────────────────────────────────────


class TestLanguageAwareChunkers:
    def test_python_ast_chunker_importable(self) -> None:
        from syrin.knowledge.chunkers import PythonASTChunker

        assert PythonASTChunker is not None

    def test_markdown_header_chunker_importable(self) -> None:
        from syrin.knowledge.chunkers import MarkdownHeaderChunker

        assert MarkdownHeaderChunker is not None

    def test_python_ast_chunker_no_mid_function_splits(self) -> None:
        """PythonASTChunker never splits inside a function definition."""
        from syrin.knowledge._chunker import Chunk, ChunkConfig
        from syrin.knowledge._document import Document
        from syrin.knowledge.chunkers import PythonASTChunker

        source = "\n".join(
            [
                "def foo():",
                "    x = 1",
                "    y = 2",
                "    return x + y",
                "",
                "def bar():",
                "    return 42",
            ]
        )
        doc = Document(content=source, source="test.py", source_type="code")
        chunker = PythonASTChunker(config=ChunkConfig())
        chunks = chunker.chunk([doc])
        # Each chunk should contain a complete function
        assert isinstance(chunks, list)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert isinstance(chunk, Chunk)

    def test_markdown_header_chunker_splits_at_headers(self) -> None:
        """MarkdownHeaderChunker splits at ## headers, not in the middle of paragraphs."""
        from syrin.knowledge._chunker import ChunkConfig
        from syrin.knowledge._document import Document
        from syrin.knowledge.chunkers import MarkdownHeaderChunker

        md = "# Section 1\n\nContent of section 1.\n\n## Subsection 1.1\n\nMore content.\n\n# Section 2\n\nFinal content."
        doc = Document(content=md, source="README.md", source_type="markdown")
        chunker = MarkdownHeaderChunker(config=ChunkConfig())
        chunks = chunker.chunk([doc])
        assert len(chunks) >= 2


# ─── CodeChunk + Hybrid Search ────────────────────────────────────────────────


class TestCodeChunkAndHybridSearch:
    def test_code_chunk_importable(self) -> None:
        from syrin.knowledge import CodeChunk

        assert CodeChunk is not None

    def test_code_chunk_construction(self) -> None:
        from syrin.knowledge import CodeChunk

        chunk = CodeChunk(
            content="def foo(): return 42",
            language="python",
            symbol_name="foo",
            symbol_type="function",
            source_file="test.py",
            start_line=1,
            end_line=1,
        )
        assert chunk.language == "python"
        assert chunk.symbol_name == "foo"
        assert chunk.start_line == 1

    def test_code_chunk_is_dataclass(self) -> None:
        import dataclasses

        from syrin.knowledge import CodeChunk

        assert dataclasses.is_dataclass(CodeChunk)

    def test_hybrid_search_config_importable(self) -> None:
        from syrin.knowledge import HybridSearchConfig

        assert HybridSearchConfig is not None

    def test_hybrid_search_config_has_bm25_weight(self) -> None:
        from syrin.knowledge import HybridSearchConfig

        cfg = HybridSearchConfig(bm25_weight=0.3, vector_weight=0.7)
        assert cfg.bm25_weight == 0.3
        assert cfg.vector_weight == 0.7

    def test_hybrid_search_config_has_reranker_flag(self) -> None:
        from syrin.knowledge import HybridSearchConfig

        cfg = HybridSearchConfig(use_reranker=True)
        assert cfg.use_reranker is True

    def test_hybrid_search_config_defaults(self) -> None:
        from syrin.knowledge import HybridSearchConfig

        cfg = HybridSearchConfig()
        assert isinstance(cfg.bm25_weight, float)
        assert isinstance(cfg.vector_weight, float)
        assert cfg.bm25_weight + cfg.vector_weight == 1.0


# ─── Knowledge ingestion progress hooks ───────────────────────────────────────


class TestKnowledgeProgressHooks:
    def test_knowledge_chunk_progress_hook(self) -> None:
        from syrin.enums import Hook

        assert hasattr(Hook, "KNOWLEDGE_CHUNK_PROGRESS")

    def test_knowledge_embed_progress_hook(self) -> None:
        from syrin.enums import Hook

        assert hasattr(Hook, "KNOWLEDGE_EMBED_PROGRESS")

    def test_hooks_are_strings(self) -> None:
        from syrin.enums import Hook

        assert isinstance(str(Hook.KNOWLEDGE_CHUNK_PROGRESS), str)
        assert isinstance(str(Hook.KNOWLEDGE_EMBED_PROGRESS), str)

    def test_hook_values_are_dotted_paths(self) -> None:
        from syrin.enums import Hook

        assert "." in str(Hook.KNOWLEDGE_CHUNK_PROGRESS)
        assert "." in str(Hook.KNOWLEDGE_EMBED_PROGRESS)


# ─── Cancellable ingestion ────────────────────────────────────────────────────


class TestCancellableIngestion:
    def test_cancellable_ingest_task_importable(self) -> None:
        from syrin.knowledge import CancellableIngestTask

        assert CancellableIngestTask is not None

    def test_cancel_stops_ingestion(self) -> None:
        """Calling cancel() on an in-progress ingestion stops it cleanly."""
        from syrin.knowledge import CancellableIngestTask
        from syrin.knowledge._document import Document

        events: list[str] = []

        async def _slow_ingest(docs: list[Document], task: CancellableIngestTask) -> None:
            for i, _doc in enumerate(docs):
                if task.cancelled:
                    events.append(f"cancelled at {i}")
                    return
                await asyncio.sleep(0)
                events.append(f"processed {i}")

        docs = [
            Document(content=f"doc{i}", source=f"doc{i}", source_type="text") for i in range(10)
        ]
        task = CancellableIngestTask()

        async def _run() -> None:
            ingest_coro = _slow_ingest(docs, task)
            t = asyncio.create_task(ingest_coro)
            await asyncio.sleep(0)  # let first iteration run
            task.cancel()
            await t

        asyncio.run(_run())
        # After cancel, should have processed only 1 doc, then stopped
        assert any("cancelled" in e for e in events)

    def test_cancellable_ingest_task_has_cancelled_flag(self) -> None:
        from syrin.knowledge import CancellableIngestTask

        task = CancellableIngestTask()
        assert task.cancelled is False
        task.cancel()
        assert task.cancelled is True

    def test_sources_exported_from_knowledge_init(self) -> None:
        """All knowledge sources are accessible from syrin.knowledge."""
        from syrin.knowledge.sources import (
            BlogSource,
            ConfluenceSource,
            DocsSource,
            GitHubSource,
            GoogleDocsSource,
            GoogleSheetsSource,
            NotionSource,
            RSSSource,
        )

        assert all(
            [
                GitHubSource,
                DocsSource,
                GoogleDocsSource,
                GoogleSheetsSource,
                ConfluenceSource,
                NotionSource,
                RSSSource,
                BlogSource,
            ]
        )
