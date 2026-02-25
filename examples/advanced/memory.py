"""Memory System Examples.

Demonstrates:
- 4-type memory (Core, Episodic, Semantic, Procedural)
- Memory decay curves
- Memory budget awareness
- Memory observability with spans
- Agent integration with persistent memory

Run: python -m examples.advanced.memory
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent
from syrin.enums import DecayStrategy, MemoryBackend, MemoryType
from syrin.memory import (
    BACKENDS,
    CoreMemory,
    Decay,
    EpisodicMemory,
    Memory,
    MemoryBudget,
    MemoryEntry,
    MemoryStore,
    ProceduralMemory,
    SemanticMemory,
    create_memory,
    get_backend,
)
from syrin.observability import set_debug

logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def example_memory_types():
    """Example 1: Using memory type classes."""
    print("\n=== Example 1: Memory Type Classes ===\n")

    # Create different types of memories with type-specific defaults
    core = CoreMemory(
        id="core-1",
        content="My name is John Smith",
        importance=0.95,  # Core defaults high
    )
    print(f"Core memory: {core.content}")
    print(f"  Type: {core.type.value}, Importance: {core.importance}")

    episodic = EpisodicMemory(
        id="ep-1",
        content="Yesterday I visited the Eiffel Tower",
    )
    print(f"\nEpisodic: {episodic.content}")
    print(f"  Type: {episodic.type.value}, Importance: {episodic.importance}")

    semantic = SemanticMemory(
        id="sem-1",
        content="Python is a programming language",
    )
    print(f"\nSemantic: {semantic.content}")
    print(f"  Type: {semantic.type.value}, Importance: {semantic.importance}")

    procedural = ProceduralMemory(
        id="proc-1",
        content="How to make coffee: boil water, add grounds, pour water",
    )
    print(f"\nProcedural: {procedural.content}")
    print(f"  Type: {procedural.type.value}, Importance: {procedural.importance}")

    # Factory function
    mem = create_memory(MemoryType.CORE, "factory-1", "Created via factory")
    print(f"\nFactory created: {mem.content} ({mem.type.value})")


def example_memory_store():
    """Example 2: Using MemoryStore."""
    print("\n=== Example 2: MemoryStore ===\n")

    store = MemoryStore()

    # Add memories
    store.add(content="User prefers dark mode", memory_type=MemoryType.CORE)
    store.add(content="Yesterday's meeting was at 3pm", memory_type=MemoryType.EPISODIC)
    store.add(content="Paris is the capital of France", memory_type=MemoryType.SEMANTIC)
    store.add(
        content="How to reset password: click forgot password", memory_type=MemoryType.PROCEDURAL
    )

    print("Added 4 memories")
    print(f"Stats: {store.get_stats()}")

    # Recall specific type
    core_memories = store.recall(memory_type=MemoryType.CORE)
    print(f"\nCore memories: {[m.content for m in core_memories]}")

    # Recall with query
    related = store.recall("password")
    print(f"Recall 'password': {[m.content for m in related]}")

    # List all
    all_memories = store.list()
    print(f"\nAll memories ({len(all_memories)}):")
    for mem in all_memories:
        print(f"  - [{mem.type.value}] {mem.content[:40]}...")


def example_decay():
    """Example 3: Memory decay curves."""
    print("\n=== Example 3: Memory Decay ===\n")

    from syrin.memory import MemoryEntry

    # Create decay with exponential strategy
    decay = Decay(
        strategy=DecayStrategy.EXPONENTIAL,
        rate=0.95,
        reinforce_on_access=True,
        min_importance=0.1,
    )

    # Create old memory (24 hours ago)
    old_memory = MemoryEntry(
        id="old-1",
        content="Old information",
        type=MemoryType.EPISODIC,
        importance=1.0,
        created_at=datetime.now() - timedelta(hours=24),
    )

    print(f"Before decay: importance = {old_memory.importance}")
    decay.apply(old_memory)
    print(f"After decay (24h old): importance = {old_memory.importance:.3f}")

    # Reinforce on access
    decay.on_access(old_memory)
    print(
        f"After access: importance = {old_memory.importance:.3f}, access_count = {old_memory.access_count}"
    )

    # Create new memory
    new_memory = MemoryEntry(
        id="new-1",
        content="New information",
        type=MemoryType.EPISODIC,
        importance=1.0,
    )

    decay.apply(new_memory)
    print(f"\nNew memory (just created): importance = {new_memory.importance:.3f}")


def example_memory_budget():
    """Example 4: Memory budget awareness."""
    print("\n=== Example 4: Memory Budget ===\n")

    from syrin.budget import warn_on_exceeded

    # Create budget with warn on exceed
    budget = MemoryBudget(
        extraction_budget=0.001,  # Very small
        on_exceeded=warn_on_exceeded,
    )

    store = MemoryStore(budget=budget)

    # Add memory - with very small budget it might warn
    result = store.add(
        content="Short fact",
        memory_type=MemoryType.SEMANTIC,
    )
    print(f"Added short fact: {result}")

    # Stats show budget usage
    print(f"Store stats: {store.get_stats()}")


def example_agent_memory():
    """Example 5: Agent with persistent memory."""
    print("\n=== Example 5: Agent with Persistent Memory ===\n")

    # Create agent with persistent memory
    agent = Agent(
        model=almock,
        memory=Memory(
            types=[
                MemoryType.CORE,
                MemoryType.EPISODIC,
                MemoryType.SEMANTIC,
                MemoryType.PROCEDURAL,
            ],
            top_k=5,
        ),
    )

    # Store memories
    agent.remember("My name is John", memory_type=MemoryType.CORE)
    agent.remember("I live in San Francisco", memory_type=MemoryType.CORE)
    agent.remember("Yesterday I had pizza for lunch", memory_type=MemoryType.EPISODIC)
    agent.remember("Python uses indentation for blocks", memory_type=MemoryType.SEMANTIC)
    agent.remember(
        "How to make tea: boil water, add tea bag, pour water", memory_type=MemoryType.PROCEDURAL
    )

    print("Stored 5 memories across all types")

    # Recall specific type
    core_memories = agent.recall(memory_type=MemoryType.CORE)
    print(f"\nCore memories: {[m.content for m in core_memories]}")

    # Search memories
    related = agent.recall("name")
    print(f"Recall 'name': {[m.content for m in related]}")

    # Forget specific memory
    if core_memories:
        agent.forget(memory_id=core_memories[0].id)
        print(f"\nForgot: {core_memories[0].content}")


def example_memory_observability():
    """Example 6: Memory observability with spans."""
    print("\n=== Example 6: Memory Observability ===\n")

    # Enable debug mode for observability
    set_debug(True)

    store = MemoryStore()

    # Memory operations create spans automatically
    store.add(content="This will be traced", memory_type=MemoryType.EPISODIC)
    store.recall("traced")

    print("Check console output above to see memory spans!")

    set_debug(False)


def example_memory_backends():
    """Example 7: Different storage backends."""
    print("\n=== Example 7: Storage Backends ===\n")

    # SQLite backend (persistent, file-based)
    print("1. SQLite backend:")
    sqlite_backend = get_backend(MemoryBackend.SQLITE, path="./example_memory.db")
    sqlite_backend.add(
        MemoryEntry(
            id="sql-1",
            content="SQLite is persistent",
            type=MemoryType.SEMANTIC,
        )
    )
    results = sqlite_backend.search("SQLite")
    print(f"   Stored and retrieved: {results[0].content if results else 'none'}")
    sqlite_backend.close()

    # In-memory backend
    print("\n2. In-memory backend:")
    memory_backend = get_backend(MemoryBackend.MEMORY)
    memory_backend.add(
        MemoryEntry(
            id="mem-1",
            content="In-memory is fast",
            type=MemoryType.SEMANTIC,
        )
    )
    results = memory_backend.search("fast")
    print(f"   Stored and retrieved: {results[0].content if results else 'none'}")

    print("\nBackends available:")
    for name, backend in BACKENDS.items():
        print(f"   - {name.value}: {backend.__name__}")


def main():
    """Run all examples."""
    print("=" * 60)
    print("Syrin Memory System Examples")
    print("=" * 60)

    example_memory_types()
    example_memory_store()
    example_decay()
    example_memory_budget()
    example_agent_memory()
    example_memory_observability()
    example_memory_backends()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
