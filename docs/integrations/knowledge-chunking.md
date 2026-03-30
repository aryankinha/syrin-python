---
title: Knowledge Chunking
description: Split documents into optimal chunks for retrieval
weight: 192
---

## The Art of Splitting

You've loaded a 500-page PDF. Now what?

LLMs have limited context windows. You can't feed them entire documents. You need to **chunk** — split documents into smaller, self-contained pieces that can be retrieved and understood independently.

But chunking isn't just "cut every 500 characters." Do it wrong and you get:

- Chunks with incomplete thoughts
- Lost context between chunks
- Retrieval misses because relevant info is split across chunks

Do it right and each chunk is a **complete unit of meaning** that can stand alone.

## Why Chunking Matters

### The Context Window Problem

A typical LLM context window is 8,192 tokens, but a 500-page document might contain 50,000 tokens. The document won't fit, so you need to chunk it.

If chunks are too big, irrelevant content dilutes the signal.
If chunks are too small, context is lost.

### The Retrieval Quality Problem

Good retrieval requires chunks that:

1. **Contain complete thoughts** — Not half a sentence
2. **Have enough context** — Understandable alone
3. **Are semantically dense** — Not mostly whitespace
4. **Overlap boundaries** — Related content stays connected

## Chunking Strategies

Syrin provides multiple chunking strategies, each optimized for different content:

| Strategy | Best For | How It Works |
| --- | --- | --- |
| `AUTO` | Mixed docs | Detects type, picks best strategy |
| `RECURSIVE` | General text | Splits at paragraphs, sentences, words |
| `MARKDOWN` | Markdown | Preserves headers, tables, code |
| `CODE` | Source code | Respects syntax, functions, classes |
| `PAGE` | PDFs | One chunk per page |
| `SENTENCE` | Simple text | Groups sentences together |
| `TOKEN` | Fixed sizes | Splits by token count |
| `SEMANTIC` | Dense content | Splits at meaning boundaries |

### AUTO Strategy (Recommended)

Let Syrin choose based on document type:

```python
from syrin.knowledge import Knowledge, ChunkConfig, ChunkStrategy

knowledge = Knowledge(
    sources=[...],
    chunk_config=ChunkConfig(
        strategy=ChunkStrategy.AUTO,
        chunk_size=512,
    ),
)
```

| Document Type | Selected Strategy |
| --- | --- |
| Markdown | `MARKDOWN` |
| Code | `CODE` |
| PDF | `PAGE` |
| Plain text | `RECURSIVE` |

### RECURSIVE Strategy

The default for general text. Splits at natural boundaries, starting with paragraphs, then sentences, then words if needed.

```python
knowledge = Knowledge(
    sources=[...],
    chunk_config=ChunkConfig(
        strategy=ChunkStrategy.RECURSIVE,
        chunk_size=512,         # Target tokens per chunk
        chunk_overlap=50,       # Overlap between chunks
        min_chunk_size=50,      # Drop chunks below this size
    ),
)
```

### MARKDOWN Strategy

Preserves Markdown structure:

```python
knowledge = Knowledge(
    sources=[...],
    chunk_config=ChunkConfig(
        strategy=ChunkStrategy.MARKDOWN,
        chunk_size=512,
        preserve_tables=True,    # Don't split tables
        preserve_code_blocks=True,  # Don't split code
        preserve_headers=True,   # Include heading hierarchy
    ),
)
```

**Input:**
```markdown
# Introduction

This is the intro section.

## Features

- Feature 1
- Feature 2

## Installation

Step 1: Install
Step 2: Configure
```

**Output chunks:**
```
Chunk 1: # Introduction / This is the intro section.
Chunk 2: ## Features / - Feature 1 / - Feature 2
Chunk 3: ## Installation / Step 1: Install / Step 2: Configure
```

### CODE Strategy

Respects code structure:

```python
knowledge = Knowledge(
    sources=[...],
    chunk_config=ChunkConfig(
        strategy=ChunkStrategy.CODE,
        chunk_size=512,
        language="python",  # Specify for better splitting
    ),
)
```

For code, chunks are split at function and class boundaries rather than arbitrary character limits.

### PAGE Strategy

One chunk per page (good for PDFs):

```python
knowledge = Knowledge(
    sources=[...],
    chunk_config=ChunkConfig(
        strategy=ChunkStrategy.PAGE,
        chunk_size=1000,  # Per-page target
    ),
)
```

### SEMANTIC Strategy

Uses embeddings to find meaning boundaries:

```python
knowledge = Knowledge(
    sources=[...],
    chunk_config=ChunkConfig(
        strategy=ChunkStrategy.SEMANTIC,
        chunk_size=512,
        similarity_threshold=0.5,  # Split at meaning drops
        embedding=embedding_model,  # Required for semantic splitting
    ),
)
```

This splits at places where meaning changes significantly.

## Configuration Options

### Chunk Size

Target tokens per chunk:

```python
ChunkConfig(
    chunk_size=512,  # 512 tokens (adjust for your model)
)
```

**Guidelines:**

| Model Context | Recommended Chunk |
| --- | --- |
| 4k | 256-512 tokens |
| 8k | 512-1024 tokens |
| 32k | 1024-2048 tokens |
| 128k | 2048-4096 tokens |

### Chunk Overlap

Overlap preserves context across boundaries. A chunk might share the last 50 tokens with the next chunk.

```python
ChunkConfig(
    chunk_size=512,
    chunk_overlap=64,  # 12% overlap
)
```

### Minimum Chunk Size

Drop tiny chunks that lack context:

```python
ChunkConfig(
    chunk_size=512,
    min_chunk_size=50,  # Drop chunks < 50 tokens
)
```

## Choosing a Strategy

### Decision Guide

Choose based on your document type:

- Mixed documents → AUTO
- Markdown docs → MARKDOWN
- Source code → CODE
- PDFs → PAGE or RECURSIVE
- Other text → RECURSIVE

### Content-Specific Tips

**Technical Documentation**
```python
ChunkConfig(
    strategy=ChunkStrategy.MARKDOWN,
    chunk_size=512,
    preserve_tables=True,
    preserve_code_blocks=True,
)
```

**User Manuals**
```python
ChunkConfig(
    strategy=ChunkStrategy.RECURSIVE,
    chunk_size=512,
    chunk_overlap=50,
)
```

**Research Papers**
```python
ChunkConfig(
    strategy=ChunkStrategy.PAGE,  # Pages often have clear sections
    chunk_size=1000,
)
```

**Code Repositories**
```python
ChunkConfig(
    strategy=ChunkStrategy.CODE,
    chunk_size=512,
    language="python",  # Or detect from extension
)
```

## Advanced: Custom Chunking

Implement your own chunker:

```python
from syrin.knowledge import Chunker, Chunk, ChunkConfig, Document

class MyChunker(CustomChunker):
    def chunk(self, documents: list[Document]) -> list[Chunk]:
        chunks = []
        for doc in documents:
            # Your custom logic
            for i, section in enumerate(split_by_headers(doc.content)):
                chunks.append(Chunk(
                    content=section,
                    metadata=doc.metadata,
                    document_id=doc.source,
                    chunk_index=i,
                    token_count=count_tokens(section),
                ))
        return chunks
```

## Performance Considerations

### Chunk Size vs. Speed

| Chunk Size | Embedding Cost | Retrieval Quality |
| --- | --- | --- |
| Small (256) | More vectors | Fine-grained, may miss context |
| Medium (512) | Balanced | Good balance |
| Large (1024) | Fewer vectors | More context, less precise |

### Storage Considerations

| Chunk Size | Approx. Chunks/Doc | Vector DB Size |
| --- | --- | --- |
| 256 tokens | ~100 | ~100KB vectors |
| 512 tokens | ~50 | ~50KB vectors |
| 1024 tokens | ~25 | ~25KB vectors |

## Testing Your Chunking

Check what chunks are created:

```python
from syrin.knowledge import get_chunker, ChunkConfig, ChunkStrategy

config = ChunkConfig(
    strategy=ChunkStrategy.RECURSIVE,
    chunk_size=256,
)
chunker = get_chunker(config)

# Test with sample document
from syrin.knowledge import Document
doc = Document(
    content="Your document text here...",
    source="test",
    source_type="text",
)
chunks = chunker.chunk([doc])

for chunk in chunks:
    print(f"[{chunk.chunk_index}] {len(chunk.content)} chars, {chunk.token_count} tokens")
```

## What's Next?

- [RAG Configuration](/agent-kit/integrations/knowledge-rag) — Configure retrieval
- [Knowledge Pool](/agent-kit/integrations/knowledge-pool) — Complete overview
- [Embedding Providers](/agent-kit/integrations/knowledge-pool) — Vector generation

## See Also

- [Document Loaders](/agent-kit/integrations/knowledge-loaders) — Source formats
- [Vector Storage](/agent-kit/integrations/knowledge-pool) — Storage backends
- [Retrieval Tuning](/agent-kit/integrations/knowledge-rag) — Optimize search
