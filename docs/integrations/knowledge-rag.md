---
title: Knowledge RAG
description: Configure retrieval-augmented generation for agents
weight: 193
---

## Making RAG Work for Your Agent

You have documents loaded and chunked. Now you need to connect them to your agent. This guide covers everything from basic search to advanced agentic retrieval.

## Basic Agentic RAG

The simplest RAG setup:

```python
from syrin import Knowledge, Agent, Model
from syrin.embedding import Embedding

knowledge = Knowledge(
    sources=[
        Knowledge.PDF("./docs/manual.pdf"),
        Knowledge.Markdown("./docs/guide.md"),
    ],
    embedding=Embedding.OpenAI("text-embedding-3-small"),
)

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    knowledge=knowledge,
)
```

The agent automatically gets a `search_knowledge` tool:

```python
result = agent.run("How do I install the software?")
# Agent searches knowledge base and uses results in answer
```

## Understanding the Search Pipeline

When an agent uses `search_knowledge`, it embeds the query into a vector, performs a vector search to find similar chunks, scores and filters results to keep only those above the threshold, then returns the chunks to the agent.

## Search Configuration

### Top-K: Number of Results

```python
knowledge = Knowledge(
    sources=[...],
    embedding=embedding,
    top_k=5,  # Return top 5 results
)
```

The right `top_k` depends on your question type. For precise questions with small chunks, 3–5 results is usually sufficient. For general questions with medium chunks, 5–10 works better. For complex queries with large chunks, 10–20 gives the agent enough material to synthesize from.

### Score Threshold: Minimum Relevance

```python
knowledge = Knowledge(
    sources=[...],
    embedding=embedding,
    score_threshold=0.3,  # Only return chunks with score >= 0.3
)
```

Scores range from 0 (no match) to 1 (identical). A score of 0.7 or higher means very similar content — you can trust these results. Scores between 0.5 and 0.7 are likely relevant. Scores between 0.3 and 0.5 are possibly relevant but may include noise. Anything below 0.3 is probably noise and should be filtered out.

## Agentic RAG: Beyond Simple Retrieval

Simple RAG works for straightforward questions. For complex queries, use **Agentic RAG**:

```python
from syrin.knowledge import AgenticRAGConfig

knowledge = Knowledge(
    sources=[...],
    embedding=embedding,
    agentic=True,  # Enable agentic features
    agentic_config=AgenticRAGConfig(
        max_search_iterations=3,
        decompose_complex=True,
        grade_results=True,
        relevance_threshold=0.5,
    ),
)
```

### What Agentic RAG Adds

When `agentic=True`, the agent gets three tools. `search_knowledge` performs a single semantic search. `search_knowledge_deep` does multi-step retrieval — it decomposes the query, searches from multiple angles, and synthesizes the results. `verify_knowledge` runs fact verification against sources before returning results.

### Query Decomposition

For complex questions, break them into sub-queries:

**Query:** "Compare Python and JavaScript for web development"

Decomposed into sub-queries:
1. "Python web development"
2. "JavaScript web development"
3. "Python vs JavaScript comparison"

### Result Grading

LLMs evaluate whether results actually answer the question:

```python
AgenticRAGConfig(
    grade_results=True,  # Enable LLM-based grading
)
```

Without grading, retrieval is based on vector similarity alone. With grading, the LLM evaluates semantic relevance — catching cases where a chunk is mathematically similar but doesn't actually answer the question.

### Query Refinement

If initial results are poor, rewrite the query:

```python
AgenticRAGConfig(
    max_search_iterations=3,  # Try up to 3 times
    relevance_threshold=0.5,  # Accept results above this
)
```

The flow is: search with original query, grade results, if poor — refine query and retry. Repeat until results are good or max iterations is reached.

### When to Use Agentic RAG

For simple factual questions, standard RAG is fine — agentic is overkill and burns more tokens. For multi-part questions, comparative analysis, and research tasks, agentic RAG earns its keep. For simple lookups, just use plain retrieval.

## Metadata Filtering

Filter search results by metadata:

```python
from syrin.knowledge import Knowledge

knowledge = Knowledge(
    sources=[
        Knowledge.Markdown("./docs/v1/", ...),  # v1 docs
        Knowledge.Markdown("./docs/v2/", ...),  # v2 docs
    ],
    embedding=embedding,
)

# Filter by source
results = await knowledge.search(
    "installation",
    filter={"source": "docs/v2/guide.md"},
)
```

Common filters include `source` for a specific file, `source_type` for document format like "pdf" or "markdown", and any custom metadata you attached via loaders.

## Context Injection

Control how knowledge is added to context:

```python
knowledge = Knowledge(
    sources=[...],
    embedding=embedding,
    inject_system_prompt=True,  # Add knowledge to system prompt
)
```

**With `inject_system_prompt=True`:**
```
System: You are helpful. Use the following context:

[KNOWLEDGE BASE]
- Python is a programming language
- It was created by Guido van Rossum
- RAG means Retrieval-Augmented Generation

User: What is Python?
```

**With `inject_system_prompt=False`:**
```
System: You are helpful.

User: What is Python?
[Agent uses search_knowledge tool]
```

## HyDE: Hypothetical Document Embeddings

A technique for better retrieval:

1. Generate a hypothetical answer
2. Embed the hypothetical answer
3. Use that embedding for retrieval

```python
# Not directly implemented, but can be simulated:
# 1. Ask LLM: "How would you answer this question?"
# 2. Embed the hypothetical answer
# 3. Search with that embedding
```

This helps when queries are vague or poorly phrased.

## Complete Configuration Example

```python
from syrin import Knowledge, Model
from syrin.knowledge import AgenticRAGConfig, ChunkConfig, ChunkStrategy, GroundingConfig
from syrin.embedding import Embedding

knowledge = Knowledge(
    # Sources
    sources=[
        Knowledge.PDF("./docs/technical.pdf"),
        Knowledge.Markdown("./docs/guide.md"),
        Knowledge.Directory("./docs/faq/", glob="**/*.md"),
    ],
    
    # Embedding
    embedding=Embedding.OpenAI("text-embedding-3-small"),
    
    # Storage
    backend=KnowledgeBackend.POSTGRES,
    connection_url="postgresql://localhost:5432/knowledge",
    collection="product_docs",
    
    # Retrieval
    top_k=5,
    score_threshold=0.3,
    
    # Chunking
    chunk_config=ChunkConfig(
        strategy=ChunkStrategy.AUTO,
        chunk_size=512,
        chunk_overlap=50,
        min_chunk_size=50,
    ),
    
    # Agentic RAG
    agentic=True,
    agentic_config=AgenticRAGConfig(
        max_search_iterations=3,
        decompose_complex=True,
        grade_results=True,
        relevance_threshold=0.5,
    ),
    
    # Grounding
    grounding=GroundingConfig(
        enabled=True,
        extract_facts=True,
        cite_sources=True,
        verify_before_use=True,
        confidence_threshold=0.7,
    ),
    
    # Context
    inject_system_prompt=True,
)
```

## Direct Search API

Sometimes you want manual control:

```python
# Search directly
results = await knowledge.search(
    "installation steps",
    top_k=10,
    filter={"source_type": "markdown"},
    score_threshold=0.4,
)

# Process results
for result in results:
    print(f"[{result.rank}] Score: {result.score:.2f}")
    print(f"Content: {result.chunk.content[:200]}...")
    print(f"Source: {result.chunk.document_id}")
    print(f"Page: {result.chunk.metadata.get('page', 'N/A')}")
```

## Adding Sources Dynamically

Update the knowledge base without rebuilding:

```python
# Add new source
knowledge.add_source(Knowledge.PDF("./new_docs/supplement.pdf"))

# Re-ingest to include new source
await knowledge.ingest()

# Check stats
stats = await knowledge.stats()
print(f"Chunks: {stats['chunk_count']}")
```

## Removing Sources

```python
# Remove source and its chunks
await knowledge.remove_source(loader)
```

## Best Practices

**Retrieval quality:** Chunk size matters more than anything else — test with your specific documents. Adjust the score threshold based on whether you need precision (higher threshold) or recall (lower threshold). Keep top_k in the range that gives the agent enough material without burying the signal in noise.

**Performance:** Pre-load on startup so the first query isn't slow. Use SQLite for development and PostgreSQL for production. Cache embeddings so unchanged documents don't get re-embedded on every restart.

**Accuracy:** Include source, page, and section in chunk metadata — the agent can use these in citations. Use agentic RAG for multi-part questions. Enable grounding for any use case where hallucinations would be costly.

## What's Next?

- [Grounding](/agent-kit/integrations/grounding) — Verify facts and prevent hallucinations
- [Grounding Confidence](/agent-kit/integrations/grounding-confidence) — Trust levels and thresholds
- [Agentic RAG](/agent-kit/integrations/knowledge-pool) — Deep dive into agentic features

## See Also

- [Knowledge Pool](/agent-kit/integrations/knowledge-pool) — Complete overview
- [Document Loaders](/agent-kit/integrations/knowledge-loaders) — Source formats
- [Chunking](/agent-kit/integrations/knowledge-chunking) — Document splitting
