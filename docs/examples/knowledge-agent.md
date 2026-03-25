---
title: Knowledge & RAG
description: Build knowledge-powered agents with retrieval-augmented generation
weight: 360
---

## Knowledge & RAG

Build agents that answer questions from your documents. Syrin provides knowledge management with document loading, chunking, embeddings, and agentic retrieval.

## Simple Knowledge Agent

Start with in-memory knowledge from text sources.

```python
import asyncio
from syrin import Agent, Knowledge, KnowledgeBackend, Model
from syrin.embedding import Embedding

async def main():
    knowledge = Knowledge(
        sources=[
            Knowledge.Text("Python is a high-level programming language."),
            Knowledge.Text("Syrin is a library for building AI agents."),
            Knowledge.Text("RAG means Retrieval-Augmented Generation."),
        ],
        embedding=Embedding.OpenAI("text-embedding-3-small"),
        backend=KnowledgeBackend.MEMORY,
    )
    
    agent = Agent(
        model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
        system_prompt="Use search_knowledge when asked about Python or Syrin.",
        knowledge=knowledge,
    )
    
    result = agent.run("What is Syrin?")
    print(result.content)

asyncio.run(main())
```

**What just happened:**
1. Created knowledge base with text sources
2. Embedded documents for similarity search
3. Attached to agent (auto-adds `search_knowledge` tool)
4. Agent retrieved relevant info and synthesized answer

## Document Loading

Load from files, URLs, and GitHub.

```python
from syrin import Knowledge, KnowledgeSource
from syrin.knowledge import GitHubLoader, URLLoader, FileLoader

knowledge = Knowledge(
    sources=[
        # PDF and text files
        KnowledgeSource.from_file("manual.pdf"),
        KnowledgeSource.from_file("guide.txt"),
        
        # Web pages
        KnowledgeSource.from_url("https://docs.example.com/api"),
        
        # GitHub repository
        KnowledgeSource.from_github(
            repo="owner/repo",
            path="docs/",
            branch="main",
        ),
    ],
    embedding=Embedding.OpenAI("text-embedding-3-small"),
    backend=KnowledgeBackend.CHROMADB,
)
```

**What just happened:**
1. Loaded from multiple source types
2. All sources chunked and embedded
3. Stored in ChromaDB vector database
4. Ready for semantic search

## Chunking Strategies

Control how documents are split.

```python
from syrin.knowledge import chunkers

knowledge = Knowledge(
    sources=[KnowledgeSource.from_file("document.pdf")],
    embedding=Embedding.OpenAI("text-embedding-3-small"),
    chunker=chunkers.RecursiveCharacter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". "],
    ),
)
```

**What just happened:**
1. Documents split into ~500 token chunks
2. 50 token overlap maintains context
3. Separators preserve paragraph and sentence boundaries

## Semantic Chunking

AI-powered chunking that respects meaning.

```python
from syrin.knowledge import chunkers

knowledge = Knowledge(
    sources=[KnowledgeSource.from_file("article.pdf")],
    chunker=chunkers.Semantic(
        max_tokens=300,
        breakpoint_threshold=0.8,
    ),
)
```

**What just happened:**
1. Chunks split at semantic boundaries
2. Related sentences stay together
3. Better retrieval quality

## Agentic RAG

Multi-step retrieval for complex questions.

```python
from syrin import Agent, Knowledge
from syrin.knowledge import AgenticRAG

knowledge = Knowledge(
    sources=[KnowledgeSource.from_github(repo="acme/docs")],
    backend=KnowledgeBackend.QDRANT,
)

agentic_rag = AgenticRAG(
    knowledge=knowledge,
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    max_steps=3,
)

agent = Agent(
    model=Model.Almock(),
    system_prompt="Answer questions using the knowledge base.",
    knowledge=agentic_rag,  # Use agentic retrieval
)
```

**What just happened:**
1. Question triggers initial search
2. Agent decides if more info needed
3. Refines search based on results
4. Synthesizes final answer

## Knowledge Verification

Check retrieval confidence.

```python
from syrin import Agent, Knowledge, Grounding
from syrin.enums import GroundingMode

knowledge = Knowledge(sources=[...])

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    knowledge=knowledge,
    grounding=Grounding(
        mode=GroundingMode.STRICT,
        min_confidence=0.7,
    ),
)

result = agent.run("What is the warranty period?")

# Check confidence
for source in result.grounding.sources:
    print(f"Source: {source.chunk.content[:50]}...")
    print(f"Confidence: {source.confidence:.2f}")
```

**What just happened:**
1. Each answer grounded in retrieved chunks
2. Confidence scores indicate reliability
3. Mode controls when to say "I don't know"

## Direct Knowledge Search

Search without an agent.

```python
import asyncio
from syrin import Knowledge

async def search_examples():
    knowledge = Knowledge(
        sources=[
            Knowledge.Text("Python supports async/await."),
            Knowledge.Text("JavaScript is event-driven."),
        ],
        embedding=Embedding.OpenAI("text-embedding-3-small"),
        backend=KnowledgeBackend.MEMORY,
    )
    
    # Direct search
    results = await knowledge.search("Tell me about Python async")
    
    for result in results:
        print(f"Content: {result.chunk.content}")
        print(f"Score: {result.score:.3f}")

asyncio.run(search_examples())
```

**What just happened:**
1. Searched knowledge base directly
2. Results ranked by semantic similarity
3. Score indicates relevance (higher = better)

## PostgreSQL Backend

Production-grade vector storage.

```python
from syrin import Knowledge

knowledge = Knowledge(
    sources=[KnowledgeSource.from_directory("docs/")],
    embedding=Embedding.OpenAI("text-embedding-3-small"),
    backend=KnowledgeBackend.POSTGRES,
    connection_string="postgresql://user:pass@localhost:5432/knowledge",
    collection="product_docs",
)
```

**What just happened:**
1. Documents stored in PostgreSQL with pgvector
2. Scales to millions of chunks
3. Production-ready persistence

## Serving a Knowledge Agent

Expose via HTTP API.

```python
from syrin import Agent, Knowledge, Model

knowledge = Knowledge(
    sources=[KnowledgeSource.from_directory("docs/")],
    backend=KnowledgeBackend.CHROMADB,
)

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
    knowledge=knowledge,
    system_prompt="Answer questions about our products.",
)

if __name__ == "__main__":
    agent.serve(port=8000, enable_playground=True)
```

```bash
# Run and visit http://localhost:8000/playground
python -m examples.19_knowledge.serve_agentic_postgres
```

## Running the Examples

```bash
# Knowledge agent
PYTHONPATH=. python -m examples.19_knowledge.knowledge_agent

# Full RAG lifecycle
PYTHONPATH=. python -m examples.19_knowledge.full_rag_lifecycle

# Agentic RAG
PYTHONPATH=. python -m examples.19_knowledge.agentic_rag

# Serve with PostgreSQL
PYTHONPATH=. python -m examples.19_knowledge.serve_agentic_postgres
```

## What's Next?

- Learn about [grounding and confidence](/integrations/grounding)
- Explore [MCP integration](/integrations/mcp) for external tools
- Understand [structured output](/agent/structured-output)

## See Also

- [Knowledge pool documentation](/integrations/knowledge-pool)
- [Loaders documentation](/integrations/knowledge-loaders)
- [Chunking documentation](/integrations/knowledge-chunking)
- [RAG documentation](/integrations/knowledge-rag)
