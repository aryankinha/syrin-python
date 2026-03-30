---
title: Knowledge Pool
description: Add external knowledge to your agents with Retrieval-Augmented Generation
weight: 190
---

## The Knowledge Problem

Your AI agent is brilliant. It can write code, analyze data, and answer questions. But there's a problem: it only knows what was in its training data.

What about:
- Your company's internal documentation?
- Recent news that happened after training?
- Private data in your database?
- A specific PDF your user uploaded?

This is the **knowledge problem**. LLMs have a fixed knowledge cutoff and can't access your specific data.

## The RAG Solution

**Retrieval-Augmented Generation (RAG)** solves this. Instead of relying only on the model's training, RAG:

1. Retrieves relevant documents when you ask a question
2. Includes those documents in the context
3. Lets the model answer based on current, specific information

The RAG flow:
1. User Query is converted to a vector embedding
2. Vector embedding is compared against document embeddings
3. Top-k most similar documents are retrieved
4. Retrieved documents are added to the context
5. LLM generates answer using the context

## Why RAG Matters

### Static Knowledge vs Dynamic Knowledge

| Approach | Knowledge Source | Use Case |
| --- | --- | --- |
| Fine-tuning | Model weights | Permanent behavior changes |
| Prompt injection | System prompt | One-time context |
| **RAG** | **External documents** | **Fresh, specific data** |

RAG is the right choice when:

- Your data changes frequently
- You need company-specific information
- Users upload documents
- You want to cite sources
- Cost matters (cheaper than fine-tuning)

### RAG vs Fine-tuning

| Factor | RAG | Fine-tuning |
| --- | --- | --- |
| Data freshness | Real-time | Static (re-train needed) |
| Cost | Lower (no training) | Higher (GPU time) |
| Source attribution | Easy (know which doc) | Hard (in weights) |
| Updates | Just add/remove docs | Re-train model |
| Best for | Facts, documents | Style, patterns |

## The RAG Pipeline in Detail

RAG isn't just "search and return." A production RAG system has several stages:

### 1. Loading (Ingestion)

Documents come from various sources:
- PDFs, Word docs, Markdown files
- Databases, APIs
- Websites, wikis
- User uploads

Each source needs a **loader** that converts it to a standard document format.

### 2. Chunking (Text Splitting)

Documents are too large for context windows. We split them into **chunks**.

For example, a long document might be split into:
- Introduction chunk
- Chapter 1 chunk
- Chapter 2 chunk
- etc.

Good chunking:
- Preserves context within chunks
- Balances chunk size vs information density
- Handles special content (tables, code)

### 3. Embedding (Vectorization)

Each chunk becomes a **vector** (list of numbers):

```python
chunk = "Python is a high-level programming language"
embedding = embed_model.encode(chunk)
# → [0.123, -0.456, 0.789, ...]  # 1536 dimensions for OpenAI
```

Similar chunks have similar vectors. This enables **semantic search** — finding conceptually related content, not just keyword matches.

### 4. Storage (Vector Database)

Vectors are stored in a **vector database** for fast retrieval. When you search:

1. Your query is embedded
2. Database finds vectors similar to your query
3. Returns chunks ranked by similarity score

Popular vector databases:
- **SQLite**: Built-in, simple, good for small scale
- **PostgreSQL**: With pgvector, production-ready
- **Chroma**: Purpose-built, easy to start
- **Qdrant**: High-performance, cloud-native

### 5. Retrieval (Search)

When a user asks a question:

1. Embed the question
2. Search the vector database
3. Return top-k most similar chunks

### 6. Augmentation (Context Injection)

The retrieved chunks are added to the prompt:

```
System: Answer based on the context.
Context: [Retrieved documents about Python]
User: What is Python?
```

### 7. Generation (Answer)

The LLM generates an answer using both:
- Its internal knowledge
- The retrieved context
- Instructions to cite sources

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

The Knowledge system orchestrates the full RAG pipeline:

1. **Load** documents from various sources
2. **Chunk** documents into smaller pieces
3. **Embed** chunks into vectors
4. **Store** vectors in the database
5. **Search** for relevant chunks
6. **Inject** chunks into agent context

### Key Features

**Multiple Source Types**
- Files: PDF, DOCX, Markdown, Text
- URLs and web scraping
- Code files: Python, JavaScript, etc.
- Structured: JSON, YAML, CSV, Excel
- Directories and GitHub repos
- Google Drive

**Smart Chunking**
- Auto-detect document type
- Preserve structure (headers, tables)
- Configurable chunk size
- Multiple strategies (recursive, semantic, by page)

**Flexible Storage**
- In-memory (prototyping)
- SQLite (local persistence)
- PostgreSQL (production)
- Chroma (vector-native)
- Qdrant (high-performance)

**Agent Integration**
- Automatic `search_knowledge` tool
- Agentic RAG for complex queries
- Grounding layer for fact verification

## Beyond Basic RAG

Syrin's Knowledge Pool goes beyond simple retrieval:

### Agentic RAG

For complex questions, standard RAG can fail. Agentic RAG:

1. **Decomposes** complex queries into sub-queries
2. **Retrieves** from multiple angles
3. **Grades** result relevance
4. **Refines** queries if results are poor
5. **Verifies** facts before answering

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

Even with good retrieval, LLMs can hallucinate. The grounding layer:

1. **Extracts** facts from retrieved documents
2. **Verifies** each fact against sources
3. **Generates** citations
4. **Flags** unverified claims

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

Use Knowledge Pool when:

- Users ask about specific documents
- Information changes frequently
- You need source attribution
- Company-specific knowledge matters
- Cost constraints prevent fine-tuning

Consider alternatives when:

- You need permanent behavior changes → Fine-tuning
- Real-time data is critical → API integration
- Simple key-value lookup → Database queries

## What You Can Customize

Syrin's Knowledge Pool is highly configurable:

| Component | What You Can Change |
| --- | --- |
| Sources | Any document type, custom loaders |
| Chunking | Strategy, size, overlap |
| Embedding | Provider, model, dimensions |
| Storage | Backend, connection, collection |
| Retrieval | Top-k, score threshold |
| Agentic RAG | Decomposition, grading, refinement |
| Grounding | Fact extraction, verification |

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
