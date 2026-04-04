---
title: Knowledge Pool
description: Add external knowledge to your agents with Retrieval-Augmented Generation
weight: 190
---

## The Knowledge Problem

Your AI agent is brilliant. It can write code, analyze data, and answer questions. But there's a problem: it only knows what was in its training data.

What about your company's internal documentation? Recent news that happened after training? Private data in your database? A specific PDF your user uploaded?

This is the **knowledge problem**. LLMs have a fixed knowledge cutoff and can't access your specific data.

## The RAG Solution

**Retrieval-Augmented Generation (RAG)** solves this. Instead of relying only on the model's training, RAG retrieves relevant documents when you ask a question, includes those documents in the context, and lets the model answer based on current, specific information.

The RAG flow works in five steps. The user query is converted to a vector embedding. That vector is compared against document embeddings in the database. The top-k most similar documents are retrieved. Those retrieved documents are added to the context. The LLM generates an answer using the context.

## Why RAG Matters

### When to Use Which Approach

Three approaches exist for giving agents specialized knowledge. **Fine-tuning** bakes knowledge into the model weights — best for permanent behavior changes, but expensive and slow to update. **Prompt injection** puts context directly in the system prompt — good for one-time context that doesn't change. **RAG** retrieves from external documents at query time — the right choice for fresh, specific, or frequently-changing data.

RAG wins when your data changes frequently, you need company-specific information, users upload documents, you want to cite sources, or cost matters (cheaper than fine-tuning).

### RAG vs Fine-tuning

Five factors distinguish them. Data freshness: RAG gives you real-time access; fine-tuning bakes in a static snapshot that requires retraining to update. Cost: RAG is lower because you skip GPU training time; fine-tuning requires substantial compute. Source attribution: with RAG you always know which document the answer came from; with fine-tuning that knowledge is baked into weights and can't be traced. Updates: with RAG you just add or remove documents; fine-tuning requires a full training run. Best for: RAG excels at facts and documents; fine-tuning excels at style and patterns.

## The RAG Pipeline in Detail

RAG isn't just "search and return." A production RAG system has seven stages.

**Loading (Ingestion)** — Documents come from various sources: PDFs, Word docs, Markdown files, databases, APIs, websites, wikis, user uploads. Each source needs a **loader** that converts it to a standard document format.

**Chunking (Text Splitting)** — Documents are too large for context windows. We split them into **chunks**. Good chunking preserves context within chunks, balances chunk size vs. information density, and handles special content like tables and code.

**Embedding (Vectorization)** — Each chunk becomes a **vector**:

```python
chunk = "Python is a high-level programming language"
embedding = embed_model.encode(chunk)
# → [0.123, -0.456, 0.789, ...]  # 1536 dimensions for OpenAI
```

Similar chunks have similar vectors. This enables **semantic search** — finding conceptually related content, not just keyword matches.

**Storage (Vector Database)** — Vectors are stored for fast retrieval. When you search, your query is embedded, the database finds similar vectors, and chunks are returned ranked by similarity score.

**Retrieval (Search)** — At query time, embed the question, search the vector database, return the top-k most similar chunks.

**Augmentation (Context Injection)** — Retrieved chunks are added to the prompt:

```
System: Answer based on the context.
Context: [Retrieved documents about Python]
User: What is Python?
```

**Generation (Answer)** — The LLM generates an answer using both its internal knowledge, the retrieved context, and instructions to cite sources.

## Syrin's Knowledge Pool

Syrin provides a complete RAG implementation with the `Knowledge` class:

```python
from syrin import Knowledge, Agent, Model
from syrin.embedding import Embedding

knowledge = Knowledge(
    sources=[
        Knowledge.PDF("./docs/manual.pdf"),
        Knowledge.Markdown("./docs/guide.md"),
        Knowledge.URL("https://example.com/info"),
    ],
    embedding=Embedding.OpenAI("text-embedding-3-small"),
)
```

### The Knowledge Pipeline

The Knowledge system orchestrates the full RAG pipeline: load documents from various sources, chunk documents into smaller pieces, embed chunks into vectors, store vectors in the database, search for relevant chunks, inject chunks into agent context.

### Key Features

**Multiple Source Types** — Files (PDF, DOCX, Markdown, Text), URLs and web scraping, code files (Python, JavaScript), structured data (JSON, YAML, CSV, Excel), directories and GitHub repos, Google Drive.

**Smart Chunking** — Auto-detect document type, preserve structure (headers, tables), configurable chunk size, multiple strategies (recursive, semantic, by page).

**Flexible Storage** — In-memory for prototyping, SQLite for local persistence, PostgreSQL for production, Chroma for vector-native storage, Qdrant for high-performance needs.

**Agent Integration** — Automatic `search_knowledge` tool, agentic RAG for complex queries, grounding layer for fact verification.

## Beyond Basic RAG

Syrin's Knowledge Pool goes beyond simple retrieval.

### Agentic RAG

For complex questions, standard RAG can fail. Agentic RAG decomposes complex queries into sub-queries, retrieves from multiple angles, grades result relevance, refines queries if results are poor, and verifies facts before answering.

```python
knowledge = Knowledge(
    sources=[...],
    embedding=embedding,
    agentic=True,  # Enable agentic retrieval
    agentic_config=AgenticRAGConfig(
        decompose_complex=True,
        grade_results=True,
    ),
)
```

### Grounding Layer

Even with good retrieval, LLMs can hallucinate. The grounding layer extracts facts from retrieved documents, verifies each fact against sources, generates citations, and flags unverified claims.

```python
knowledge = Knowledge(
    sources=[...],
    embedding=embedding,
    grounding=GroundingConfig(
        extract_facts=True,
        verify_before_use=True,
        cite_sources=True,
    ),
)
```

## When to Use Knowledge Pool

Use Knowledge Pool when users ask about specific documents, information changes frequently, you need source attribution, company-specific knowledge matters, or cost constraints prevent fine-tuning.

Consider alternatives when you need permanent behavior changes (fine-tuning), real-time data that requires fresh API calls (API integration), or simple key-value lookups (database queries).

## What You Can Customize

Every layer of the pipeline is configurable. Sources accept any document type or a custom loader. Chunking accepts any strategy, size, and overlap configuration. Embedding accepts any provider and model. Storage accepts any backend and connection. Retrieval is tunable via top_k and score threshold. Agentic RAG supports decomposition, grading, and refinement configuration. Grounding supports fact extraction, verification, and citation configuration.

## Quick Example

Here's a complete example:

```python
from syrin import Knowledge, Agent, Model
from syrin.embedding import Embedding

# 1. Create knowledge base
knowledge = Knowledge(
    sources=[
        Knowledge.PDF("./resume.pdf"),
        Knowledge.Markdown("./skills.md"),
    ],
    embedding=Embedding.OpenAI("text-embedding-3-small"),
)

# 2. Attach to agent
agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    knowledge=knowledge,  # Gets search_knowledge tool
)

# 3. Ask questions
result = agent.run("What programming languages does the user know?")
```

The agent automatically searches the knowledge base and incorporates results into its answer.

## Additional Knowledge Exports

The public knowledge package also includes:

- `HybridSearchConfig` for mixed lexical/vector retrieval tuning.
- `CancellableIngestTask` for long-running ingestion workflows.
- `InMemoryKnowledgeStore`, `get_knowledge_store()`, and `register_knowledge_store()` for store selection and custom store registration.
- `BlogSource`, `ConfluenceSource`, `DocsSource`, `GitHubSource`, `GoogleDocsSource`, `GoogleSheetsSource`, `NotionSource`, and `RSSSource` for source-oriented ingestion pipelines.

## What's Next?

- [Document Loaders](/agent-kit/integrations/knowledge-loaders) — Load from any source
- [Chunking Strategies](/agent-kit/integrations/knowledge-chunking) — Split documents optimally
- [RAG Configuration](/agent-kit/integrations/knowledge-rag) — Configure retrieval and generation
- [Grounding](/agent-kit/integrations/grounding) — Verify facts and cite sources

## See Also

- [Agentic RAG](/agent-kit/integrations/knowledge-rag) — Multi-step retrieval
- [Grounding](/agent-kit/integrations/grounding) — Anti-hallucination layer
- [Embedding Providers](/agent-kit/core/models) — Vector embeddings
