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

When an agent uses `search_knowledge`:

1. **Embed Query** — Convert the user query to a vector
2. **Vector Search** — Find chunks with similar vectors
3. **Score & Filter** — Keep results above the threshold
4. **Return Results** — Pass chunks to the agent

## Search Configuration

### Top-K: Number of Results

```python
knowledge = Knowledge(
    sources=[...],
    embedding=embedding,
    top_k=5,  # Return top 5 results
)
```

| top_k | Use Case |
| --- | --- |
| 3-5 | Precise questions, small chunks |
| 5-10 | General questions, medium chunks |
| 10-20 | Complex queries, large chunks |

### Score Threshold: Minimum Relevance

```python
knowledge = Knowledge(
    sources=[...],
    embedding=embedding,
    score_threshold=0.3,  # Only return chunks with score >= 0.3
)
```

Scores range from 0 (no match) to 1 (identical). Typical thresholds:

| Threshold | Meaning |
| --- | --- |
| 0.7+ | Very similar |
| 0.5-0.7 | Likely relevant |
| 0.3-0.5 | Possibly relevant |
| <0.3 | Probably noise |

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

When `agentic=True`, the agent gets three tools:

| Tool | Purpose |
| --- | --- |
| `search_knowledge` | Single semantic search |
| `search_knowledge_deep` | Multi-step retrieval |
| `verify_knowledge` | Fact verification |

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

**Without grading:** Retrieval based on vector similarity alone.
**With grading:** LLM evaluates semantic relevance.

### Query Refinement

If initial results are poor, rewrite the query:

```python
AgenticRAGConfig(
    max_search_iterations=3,  # Try up to 3 times
    relevance_threshold=0.5,  # Accept results above this
)
```

**Flow:**
1. Search with original query
2. Grade results
3. If poor: refine query and retry
4. Repeat until good results or max iterations

### When to Use Agentic RAG

| Scenario | Use Agentic RAG? |
| --- | --- |
| Simple factual questions | No (overkill) |
| Multi-part questions | Yes |
| Comparative analysis | Yes |
| Research tasks | Yes |
| Simple lookups | No |

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

Common filters:
- `source`: Specific file
- `source_type`: "pdf", "markdown", etc.
- Custom metadata from loaders

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

### Retrieval Quality

1. **Chunk size matters** — Test with your specific documents
2. **Score threshold** — Adjust based on precision vs recall needs
3. **Top-k** — Balance between breadth and noise

### Performance

1. **Pre-load on startup** — Don't wait for first search
```python
await knowledge.ingest()  # Load at startup
```

2. **Use appropriate backend** — SQLite for dev, Postgres for prod
3. **Cache embeddings** — Don't re-embed unchanged documents

### Accuracy

1. **Use metadata** — Include source, page, section in context
2. **Agentic for complex** — Use agentic RAG for multi-part questions
3. **Ground facts** — Enable grounding for hallucination prevention

## What's Next?

- [Grounding](/integrations/grounding) — Verify facts and prevent hallucinations
- [Grounding Confidence](/integrations/grounding-confidence) — Trust levels and thresholds
- [Agentic RAG](/integrations/knowledge-pool) — Deep dive into agentic features

## See Also

- [Knowledge Pool](/integrations/knowledge-pool) — Complete overview
- [Document Loaders](/integrations/knowledge-loaders) — Source formats
- [Chunking](/integrations/knowledge-chunking) — Document splitting
