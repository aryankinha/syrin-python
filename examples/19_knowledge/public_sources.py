"""Public Knowledge Sources — GitHub repos, RSS feeds, docs sites.

Demonstrates:
- GitHubSource: load documents from a public GitHub repository
- RSSSource: load articles from a public RSS/Atom feed
- Knowledge(): full RAG setup (requires embedding provider)
- Cancellable document loading with asyncio.create_task() + task.cancel()

No API keys required for the document loading demos.
Full RAG (Knowledge + search) requires an embedding provider.

Run:
    python examples/19_knowledge/public_sources.py

Requires: pip install httpx  (for HTTP-based fetching)
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from syrin.knowledge.sources import GitHubSource, RSSSource  # noqa: E402

# ---------------------------------------------------------------------------
# 1. GitHubSource — load README from a public repo
# ---------------------------------------------------------------------------


async def demo_github() -> None:
    print("=" * 60)
    print("GitHubSource — public repo (pydantic/pydantic)")
    print("=" * 60)

    source = GitHubSource(
        owner="pydantic",
        repo="pydantic",
        token=os.getenv("GITHUB_TOKEN"),  # Optional — increases rate limit
        include_readme=True,
        include_code=False,  # README only for speed
    )

    print("Fetching pydantic/pydantic README from GitHub...")
    try:
        docs = await source.aload()
        print(f"Loaded {len(docs)} document(s)")
        for doc in docs[:3]:
            title = doc.metadata.get("title") or doc.source or "untitled"
            print(f"  • {title}: {len(doc.content)} chars")
            print(f"    preview: {doc.content[:120]!r}")
    except Exception as exc:
        print(f"  ✗ {exc}")
        print("  (check network connection; set GITHUB_TOKEN to avoid rate limits)")

    print()


# ---------------------------------------------------------------------------
# 2. RSSSource — load articles from a public feed
# ---------------------------------------------------------------------------


async def demo_rss() -> None:
    print("=" * 60)
    print("RSSSource — Python Blog RSS feed")
    print("=" * 60)

    source = RSSSource(
        feed_url="https://blog.python.org/feeds/posts/default",
        max_items=5,
        fetch_full_content=False,  # Use feed summary only (faster)
    )

    print("Fetching Python Blog RSS feed...")
    try:
        docs = await source.aload()
        print(f"Loaded {len(docs)} article(s)")
        for doc in docs:
            title = doc.metadata.get("title") or "untitled"
            pub = doc.metadata.get("published", "")
            print(f"  • [{pub[:10]}] {title}")
        if docs:
            print("\n  First article preview:")
            print(f"  {docs[0].content[:200]!r}")
    except Exception as exc:
        print(f"  ✗ {exc}")
        print("  (check network connection)")

    print()


# ---------------------------------------------------------------------------
# 3. Cancellable loading demo
# ---------------------------------------------------------------------------


async def demo_cancellable() -> None:
    print("=" * 60)
    print("Cancellable ingestion")
    print("=" * 60)

    source = GitHubSource(
        owner="python",
        repo="cpython",
        include_readme=True,
        include_code=False,
    )

    print("Starting CPython README load (will cancel after 1.5s)...")

    async def _load() -> None:
        docs = await source.aload()
        print(f"  Loaded {len(docs)} documents (completed before cancel)")

    task = asyncio.create_task(_load())

    await asyncio.sleep(1.5)
    if not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            print("  ✓ Loading cancelled cleanly after 1.5s")
    else:
        print("  (completed before cancel fired)")

    print()


# ---------------------------------------------------------------------------
# 4. Knowledge RAG setup (requires embedding — API key needed)
# ---------------------------------------------------------------------------


def demo_knowledge_rag_note() -> None:
    print("=" * 60)
    print("Knowledge RAG (requires embedding provider)")
    print("=" * 60)
    print("""
To use sources with full RAG search:

    from syrin.knowledge import Knowledge
    from syrin.knowledge.sources import GitHubSource, RSSSource
    from syrin.embedding import Embedding

    source = GitHubSource("pydantic", "pydantic")
    knowledge = Knowledge(
        sources=[source],
        embedding=Embedding.OpenAI(api_key=os.getenv("OPENAI_API_KEY")),
    )
    await knowledge.ingest()

    results = await knowledge.search("what is pydantic used for?", top_k=3)
    for r in results:
        print(f"  [{r.score:.2f}] {r.content[:120]}")

    # Attach to agent — context auto-injected into system prompt:
    class RAGAgent(Agent):
        model = Model.Anthropic(api_key=...)
        knowledge = knowledge
        system_prompt = "Answer using provided knowledge."
""")


async def main() -> None:
    await demo_github()
    await demo_rss()
    await demo_cancellable()
    demo_knowledge_rag_note()


if __name__ == "__main__":
    asyncio.run(main())
