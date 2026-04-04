---
title: Memory Backends
description: Choose where your agent's memories are stored
weight: 22
---

## Where Do Memories Live?

By default, Syrin stores memories in RAM. Fast, zero setup — and completely gone when your process restarts.

For memories that survive restarts, you pick a backend. There are six options, ranging from "zero setup, local file" to "distributed vector database with semantic search."

## In-Memory (Default)

The default. No configuration needed.

```python
from syrin import Memory

memory = Memory()  # RAM only — fast, ephemeral
```

RAM storage is ideal for testing your agent logic, running quick prototypes, or building short-lived agents that don't need history. It's the fastest option and has zero dependencies. The tradeoff: every restart wipes the slate clean, and you can't share memories between processes.

## SQLite

Persistent storage in a single file. No server, no dependencies.

```python
from syrin import Memory
from syrin.enums import MemoryBackend

# Defaults to ~/.syrin/memory.db if path is omitted
memory = Memory(
    backend=MemoryBackend.SQLITE,
    path="./data/memory.db",
)
```

SQLite is the right move for single-user apps, personal projects, or any situation where you need persistence but don't want to run a server. It's also completely portable — copy the file and your memories come with it.

The limitation is concurrency. SQLite works fine for one user, but starts struggling with high-volume parallel writes. If you're building a multi-user service, step up to Redis or PostgreSQL.

## Redis

Ultra-fast distributed memory with optional TTL. Good for session-based memory that should expire.

```bash
pip install syrin[vector]  # or: pip install redis
```

```python
from syrin import Memory
from syrin.enums import MemoryBackend
from syrin.memory import RedisConfig

memory = Memory(
    backend=MemoryBackend.REDIS,
    redis=RedisConfig(
        host="localhost",
        port=6379,
        db=0,
        prefix="myapp:memory:",  # Namespace to avoid key collisions
        ttl=86400,                # Expire memories after 24 hours (optional)
    ),
)
```

Redis excels when you need sub-millisecond memory reads, when multiple agents or processes share the same memory pool, or when memories should naturally expire (TTL is built in). The tradeoff is infrastructure — you need a Redis server, and Redis doesn't support semantic (meaning-based) search.

## PostgreSQL

Production-grade relational storage. The right choice for team environments, SQL-queryable memory, or situations where you want one database for everything.

```bash
pip install syrin[postgres]  # or: pip install psycopg2-binary
```

```python
from syrin import Memory
from syrin.enums import MemoryBackend
from syrin.memory import PostgresConfig

memory = Memory(
    backend=MemoryBackend.POSTGRES,
    postgres=PostgresConfig(
        host="localhost",
        port=5432,
        database="syrin",
        user="postgres",
        password="your-password",
        table="memories",  # Optional custom table name
    ),
)
```

If you want semantic search with PostgreSQL, install `pgvector` and add the `vector_size` parameter:

```bash
pip install pgvector
```

```python
memory = Memory(
    backend=MemoryBackend.POSTGRES,
    postgres=PostgresConfig(
        host="localhost",
        database="syrin",
        vector_size=384,  # Enables pgvector with this embedding dimension
    ),
)
```

## Qdrant

A dedicated vector database — the best choice when semantic search (finding memories by meaning, not keywords) is important.

```bash
pip install syrin[vector]  # or: pip install qdrant-client
```

### Embedded (No Server)

```python
from syrin import Memory
from syrin.enums import MemoryBackend
from syrin.memory import QdrantConfig

memory = Memory(
    backend=MemoryBackend.QDRANT,
    qdrant=QdrantConfig(
        path="./qdrant_data",    # Local file storage
        collection="memories",
        namespace="user-123",    # Isolate memories per user
    ),
)
```

### Qdrant Cloud or Remote Server

```python
memory = Memory(
    backend=MemoryBackend.QDRANT,
    qdrant=QdrantConfig(
        url="https://your-instance.qdrant.tech",
        api_key="your-api-key",
        collection="memories",
        namespace="tenant-abc",
    ),
)
```

### Custom Embeddings

By default, Qdrant uses Syrin's built-in embedding model. For OpenAI embeddings:

```python
from syrin.memory import EmbeddingConfig

memory = Memory(
    backend=MemoryBackend.QDRANT,
    qdrant=QdrantConfig(
        path="./qdrant_data",
        collection="memories",
        embedding_config=EmbeddingConfig(
            provider="openai",
            model="text-embedding-3-small",
            dimensions=1536,
        ),
    ),
)
```

Qdrant is the right choice for RAG applications, multi-tenant systems with namespace isolation, or any use case where "find the most relevant memory" matters more than "find the exact memory."

## Chroma

A lightweight embedded vector database. Easier to set up than Qdrant, good for local development and prototyping with semantic search.

```bash
pip install syrin[vector]  # or: pip install chromadb
```

```python
from syrin import Memory
from syrin.enums import MemoryBackend
from syrin.memory import ChromaConfig

memory = Memory(
    backend=MemoryBackend.CHROMA,
    chroma=ChromaConfig(
        path="./chroma_db",
        collection="memories",
    ),
)
```

Chroma shines for local semantic search without a server. The tradeoff compared to Qdrant is scalability and features — Chroma is great for one user, Qdrant is better for multi-tenant production systems.

## Choosing a Backend

Start simple and upgrade as your needs grow:

```python
from syrin import Memory
from syrin.enums import MemoryBackend

# Stage 1: Testing — in-memory, zero setup
memory = Memory()

# Stage 2: Need persistence — SQLite, still no server
memory = Memory(backend=MemoryBackend.SQLITE, path="./memory.db")

# Stage 3: Production — choose based on your needs
# Semantic search needed? → Qdrant (production) or Chroma (local)
# Distributed, high concurrency? → Redis or PostgreSQL
# SQL queries on memory? → PostgreSQL
# Simple single-machine persistence? → SQLite still works
```

## Multi-Tenant Isolation

For applications with multiple users, isolate memories by user:

```python
from syrin import Memory
from syrin.enums import MemoryBackend
from syrin.memory import RedisConfig, QdrantConfig

# Redis: use a key prefix per user
memory = Memory(
    backend=MemoryBackend.REDIS,
    redis=RedisConfig(prefix=f"user-{user_id}:"),
)

# Qdrant: use a namespace per user
memory = Memory(
    backend=MemoryBackend.QDRANT,
    qdrant=QdrantConfig(namespace=f"user-{user_id}", collection="memories"),
)
```

## Migrating Between Backends

Export from one backend and import into another:

```python
from syrin import Memory
from syrin.enums import MemoryBackend
from syrin.memory import PostgresConfig

# Export from SQLite
sqlite_memory = Memory(backend=MemoryBackend.SQLITE, path="./old_memory.db")
snapshot = sqlite_memory.export()

# Import to PostgreSQL
pg_memory = Memory(
    backend=MemoryBackend.POSTGRES,
    postgres=PostgresConfig(host="localhost", database="syrin"),
)
count = pg_memory.import_from(snapshot)
print(f"Migrated {count} memories")
```

## What's Next?

- [Memory Types](/core/memory-types) — Core, Episodic, Semantic, Procedural
- [Memory Overview](/core/memory) — Back to memory basics
- [Agent Configuration](/agent/agent-configuration) — Wire memory into your agent
