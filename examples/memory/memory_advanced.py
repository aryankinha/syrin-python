"""Advanced Memory Example.

Demonstrates:
- Advanced memory operations
- Memory with decay
- Memory budget tracking
- Memory consolidation
- Different memory backends

Run: python -m examples.memory.memory_advanced
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from syrin import Agent, Decay, Memory, MemoryBudget, MemoryEntry, MemoryType, Model

logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MODEL_ID = os.getenv("OPENAI_MODEL_NAME", "openai/gpt-4o-mini")


def example_memory_decay() -> None:
    """Using memory with decay."""
    print("\n" + "=" * 50)
    print("Memory Decay Example")
    print("=" * 50)

    # Create decay configuration
    decay = Decay(
        strategy="exponential",
        half_life=100,  # Importance halves every 100 interactions
    )

    print(f"Decay strategy: {decay.strategy}")
    print(f"Half life: {decay.half_life}")


def example_memory_budget() -> None:
    """Using memory with budget."""
    print("\n" + "=" * 50)
    print("Memory Budget Example")
    print("=" * 50)

    budget = MemoryBudget(
        max_tokens=4000,  # Max tokens for memory context
        max_entries=100,  # Max memory entries
        cost_per_token=0.0001,  # Cost per token
    )

    print(f"Max tokens: {budget.max_tokens}")
    print(f"Max entries: {budget.max_entries}")
    print(f"Cost per token: {budget.cost_per_token}")


def example_memory_entry() -> None:
    """Working with MemoryEntry."""
    print("\n" + "=" * 50)
    print("Memory Entry Example")
    print("=" * 50)

    entry = MemoryEntry(
        content="User prefers dark mode",
        memory_type=MemoryType.CORE,
        importance=0.9,
        metadata={"source": "user_preference"},
    )

    print(f"Content: {entry.content}")
    print(f"Type: {entry.type}")
    print(f"Importance: {entry.importance}")
    print(f"Metadata: {entry.metadata}")


def example_recall_with_query() -> None:
    """Using recall with query."""
    print("\n" + "=" * 50)
    print("Recall with Query Example")
    print("=" * 50)

    class Assistant(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a helpful assistant."

    assistant = Assistant(memory=Memory())

    # Store some memories
    assistant.remember("User likes Python programming")
    assistant.remember("User works at a startup")
    assistant.remember("User prefers afternoon meetings")
    assistant.remember("User is learning machine learning")

    # Recall with query
    results = assistant.recall(query="programming work")
    print("Recall results for 'programming work':")
    for r in results:
        print(f"  - {r.content[:50]}...")


def example_forget_memory() -> None:
    """Using forget to remove memories."""
    print("\n" + "=" * 50)
    print("Forget Memory Example")
    print("=" * 50)

    class Assistant(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a helpful assistant."

    assistant = Assistant(memory=Memory())

    # Store memories
    assistant.remember("User's favorite color is blue")
    assistant.remember("User's favorite color is red")  # Override

    # List memories before
    print("Before forget:")
    for mem in assistant.recall():
        print(f"  - {mem.content}")

    # Note: In a real implementation, you'd have a forget method
    # For now, let's just show the concept
    print("\nNote: forget() would remove specific memories")


def example_memory_context_window() -> None:
    """How memories are injected into context."""
    print("\n" + "=" * 50)
    print("Memory Context Window")
    print("=" * 50)

    class Assistant(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a helpful assistant."
        persistent_memory = Memory()

    assistant = Assistant()

    # Add memories
    for i in range(10):
        assistant.remember(f"Memory {i}: Important fact #{i}")

    # The memory system decides what to inject based on:
    # - Relevance to current query
    # - Importance scores
    # - Available context space
    print("Added 10 memories")
    print("Memory system will inject relevant ones into context")


def example_memory_consolidation() -> None:
    """Memory consolidation concepts."""
    print("\n" + "=" * 50)
    print("Memory Consolidation Example")
    print("=" * 50)

    # Consolidation helps manage memory by:
    # - Combining similar memories
    # - Extracting key patterns
    # - Pruning old/unimportant memories

    print("Consolidation strategies:")
    print("  1. Merge similar episodic memories")
    print("  2. Extract patterns from semantic memory")
    print("  3. Prune low-importance memories")
    print("  4. Summarize old conversations")


def example_agent_memory_lifecycle() -> None:
    """Complete memory lifecycle with agent."""
    print("\n" + "=" * 50)
    print("Agent Memory Lifecycle")
    print("=" * 50)

    class Assistant(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a helpful assistant that remembers user context."
        persistent_memory = Memory()

    assistant = Assistant()

    # Session 1
    print("Session 1:")
    r1 = assistant.response("I'm interested in learning about AI")
    print(f"  Response: {r1.content[:50]}...")

    # Store important context
    assistant.remember("User interested in AI", memory_type=MemoryType.SEMANTIC)

    # Session 2 (new call - memory persists)
    print("\nSession 2:")
    r2 = assistant.response("What should I start with?")
    print(f"  Response: {r2.content[:50]}...")


def example_memory_importance() -> None:
    """Setting importance on memories."""
    print("\n" + "=" * 50)
    print("Memory Importance Example")
    print("=" * 50)

    class Assistant(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a helpful assistant."
        persistent_memory = Memory()

    assistant = Assistant()

    # High importance - core identity
    assistant.remember("User's name is Alice", memory_type=MemoryType.CORE, importance=1.0)

    # Medium importance - preferences
    assistant.remember(
        "User prefers concise answers", memory_type=MemoryType.SEMANTIC, importance=0.7
    )

    # Lower importance - ephemeral
    assistant.remember("User asked about weather", memory_type=MemoryType.EPISODIC, importance=0.3)

    # Recalling shows all, but agent can prioritize
    memories = assistant.recall()
    print("Stored memories with importance:")
    for m in memories:
        print(f"  [{m.importance}] {m.content[:40]}...")


if __name__ == "__main__":
    example_memory_decay()
    example_memory_budget()
    example_memory_entry()
    example_recall_with_query()
    example_forget_memory()
    example_memory_context_window()
    example_memory_consolidation()
    example_agent_memory_lifecycle()
    example_memory_importance()
