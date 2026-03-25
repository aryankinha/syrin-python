---
title: Memory Backends
description: Choose where your agent's memories are stored
weight: 22
---

## Where Do Memories Live?

By default, Syrin stores memories in memory (RAM). This is fast and requires no setup—but memories disappear when your app restarts.

For persistent memory, choose a backend that fits your needs:

| Backend | Setup | Persistence | Semantic Search | Best For |
|---------|-------|-------------|----------------|----------|
| **Memory** | None | ❌ (RAM) | ❌ | Testing, prototypes |
| **SQLite** | None | ✅ (file) | ❌ | Simple apps, single-user |
| **Redis** | Server | ✅ | ❌ | Fast, distributed |
| **PostgreSQL** | Server | ✅ | Optional | Production, teams |
| **Qdrant** | Server | ✅ | ✅ | Semantic search |
| **Chroma** | None | ✅ (file) | ✅ | Local prototyping |

---

## In-Memory (Default)

The simplest option. No setup required.

```python
from syrin import Memory

# Default - in-memory (RAM)
memory = Memory()

# Explicit
memory = Memory(backend=MemoryBackend.MEMORY)
```

### When to Use

- **Testing** your agent logic
- **Prototyping** before committing to persistence
- **Short-lived** agents that don't need history

### Trade-offs

| Pros | Cons |
|------|------|
| Zero setup | Lost on restart |
| Fastest speed | Can't share between processes |
| No dependencies | Limited storage |

---

## SQLite

Persistent storage in a single file. No server needed.

```python
from syrin import Memory
from syrin.enums import MemoryBackend

# File path (optional - defaults to ~/.syrin/memory.db)
memory = Memory(
    backend=MemoryBackend.SQLITE,
    path="./data/memory.db"
)
```

### When to Use

- **Single-user** applications
- **Persistent** memory without servers
- **Simple deployments** with one machine
- **Starting out** with memory

### Trade-offs

| Pros | Cons |
|------|------|
| Persistent | Single machine |
| Zero server setup | Basic search only |
| Portable file | Not for high concurrency |

---

## Redis

Ultra-fast, distributed memory with optional TTL.

```bash
pip install syrin[vector]  # or pip install redis
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
        prefix="myapp:memory:",  # Key prefix for isolation
        ttl=86400,  # Optional: expire after 24 hours
    )
)
```

### When to Use

- **High-performance** applications
- **Distributed systems** with multiple agents
- **Session-based** memory with expiration
- **Caching layer** in front of database

### Trade-offs

| Pros | Cons |
|------|------|
| Very fast | Requires Redis server |
| Distributed | No semantic search |
| TTL support | Extra infrastructure |

---

## PostgreSQL

Production-grade relational storage.

```bash
pip install syrin[postgres]  # or pip install psycopg2-binary
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
        table="memories",  # Optional table name
    )
)
```

### With Vector Search (pgvector)

For semantic search with PostgreSQL:

```bash
pip install pgvector
```

```python
memory = Memory(
    backend=MemoryBackend.POSTGRES,
    postgres=PostgresConfig(
        host="localhost",
        database="syrin",
        vector_size=384,  # Enable pgvector with embedding size
    )
)
```

### When to Use

- **Production applications**
- **Team environments** with shared memory
- **Need SQL queries** on memory data
- **Want one database** for everything

### Trade-offs

| Pros | Cons |
|------|------|
| Enterprise-grade | Requires PostgreSQL |
| SQL support | Vector search needs pgvector |
| Shared across processes | More complex setup |

---

## Qdrant

Vector database for semantic search.

```bash
pip install syrin[vector]  # or pip install qdrant-client
```

### Local Embedded (No Server)

```python
from syrin import Memory
from syrin.enums import MemoryBackend
from syrin.memory import QdrantConfig

memory = Memory(
    backend=MemoryBackend.QDRANT,
    qdrant=QdrantConfig(
        path="./qdrant_data",  # Local storage
        collection="memories",
        namespace="user-123",  # Per-user isolation
    )
)
```

### Qdrant Cloud or Remote Server

```python
memory = Memory(
    backend=MemoryBackend.QDRANT,
    qdrant=QdrantConfig(
        url="https://your-instance.qdrant.tech",
        api_key="your-api-key",  # For cloud
        collection="memories",
        namespace="tenant-abc",
    )
)
```

### With Custom Embeddings

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
        )
    )
)
```

### When to Use

- **Semantic search** (find by meaning, not keywords)
- **RAG applications**
- **Multi-tenant** with namespace isolation
- **Production** vector search

### Trade-offs

| Pros | Cons |
|------|------|
| Semantic search | Requires Qdrant |
| Namespace isolation | More complex |
| Scalable | Extra infrastructure |

---

## Chroma

Lightweight embedded vector database.

```bash
pip install syrin[vector]  # or pip install chromadb
```

```python
from syrin import Memory
from syrin.enums import MemoryBackend
from syrin.memory import ChromaConfig

memory = Memory(
    backend=MemoryBackend.CHROMA,
    chroma=ChromaConfig(
        path="./chroma_db",  # Local persistent storage
        collection="memories",
    )
)
```

### When to Use

- **Local prototyping**
- **Quick experiments** with vector search
- **Single-user** applications
- **Zero-config** vector search

### Trade-offs

| Pros | Cons |
|------|------|
| Embedded (no server) | Less scalable than Qdrant |
| Easy setup | Fewer features |
| Good for dev | Production may need Qdrant |

---

## Comparison Table

| Backend | Setup | Persistence | Semantic Search | Scalability | Use Case |
|---------|-------|-------------|----------------|-------------|----------|
| Memory | None | ❌ | ❌ | Single process | Testing |
| SQLite | None | ✅ | ❌ | Single machine | Simple apps |
| Redis | Server | ✅ | ❌ | Distributed | Fast cache |
| PostgreSQL | Server | ✅ | Optional (pgvector) | Enterprise | Production |
| Qdrant | Server/Cloud | ✅ | ✅ | Scalable | Semantic search |
| Chroma | None | ✅ | ✅ | Local only | Prototyping |

---

## Choosing a Backend

### Start Simple

```python
# 1. Begin with in-memory for testing
memory = Memory()

# 2. Switch to SQLite for persistence
memory = Memory(backend=MemoryBackend.SQLITE, path="./memory.db")

# 3. Choose production backend based on needs:
#    - Need semantic search? → Qdrant or Chroma
#    - Need distributed? → Redis or PostgreSQL
#    - Need simplicity? → SQLite
```

### Decision Guide

Choose your backend based on these questions:

**Do you need persistence?**
- No → Use `Memory` (in-memory)
- Yes → Continue to Step 2

**Do you need semantic search?**
- Yes:
  - Local/prototyping → Chroma
  - Production → Qdrant
- No:
  - Simple app → SQLite
  - Distributed system → Redis
  - Enterprise/team → PostgreSQL

## Multi-Tenant Isolation

For applications with multiple users, use namespace isolation:

```python
# Redis with prefix
memory = Memory(
    backend=MemoryBackend.REDIS,
    redis=RedisConfig(
        prefix=f"tenant-{tenant_id}:",  # Isolate by tenant
    )
)

# Qdrant with namespace
memory = Memory(
    backend=MemoryBackend.QDRANT,
    qdrant=QdrantConfig(
        namespace=f"user-{user_id}",  # Per-user collection
    )
)

# PostgreSQL with tenant column
# (Filter by tenant_id in queries)
```

---

## Migration Between Backends

Export from one backend, import to another:

```python
from syrin import Memory
from syrin.enums import MemoryBackend

# Export from SQLite
sqlite_memory = Memory(backend=MemoryBackend.SQLITE, path="./old_memory.db")
snapshot = sqlite_memory.export()

# Import to PostgreSQL
pg_memory = Memory(
    backend=MemoryBackend.POSTGRES,
    postgres=PostgresConfig(host="localhost", database="syrin")
)
count = pg_memory.import_from(snapshot)
print(f"Migrated {count} memories")
```

---

## Connection Management

Close connections when done:

```python
memory = Memory(backend=MemoryBackend.REDIS, redis=RedisConfig(host="localhost"))

# Use memory...

# Close when done (important for Redis)
memory.close()
```

Or use context manager (when supported):

```python
with Memory(backend=MemoryBackend.SQLITE, path="./memory.db") as memory:
    memory.remember("User's name is Alice", memory_type=MemoryType.CORE)
```

---

## What's Next?

- [Memory Overview](/core/memory) - Back to memory basics
- [Memory Types](/core/memory-types) - Core, Episodic, Semantic, Procedural

## See Also

- [Agents](/agent/overview) - Building agents with memory
- [Budget](/core/budget) - Control memory costs
