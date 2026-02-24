"""Memory Example.

Demonstrates:
- Creating an agent with conversation memory
- Using different memory types (CORE, EPISODIC, SEMANTIC, PROCEDURAL)
- Remember and recall operations

Run: python -m examples.memory.basic_memory
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from syrin import Agent, Memory, MemoryType, Model

logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MODEL_ID = os.getenv("OPENAI_MODEL_NAME", "openai/gpt-4o-mini")


def example_basic_memory() -> None:
    """Basic memory operations."""
    print("\n" + "=" * 50)
    print("Basic Memory Example")
    print("=" * 50)

    class Assistant(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a helpful assistant that remembers user preferences."

    assistant = Assistant(memory=Memory())

    print("1. Initial conversation:")
    result1 = assistant.response("My name is Alice.")
    print(f"   Response: {result1.content}")

    print("\n2. Second turn (should remember name):")
    result2 = assistant.response("What's my name?")
    print(f"   Response: {result2.content}")


def example_memory_types() -> None:
    """Different memory types."""
    print("\n" + "=" * 50)
    print("Memory Types Example")
    print("=" * 50)

    class Assistant(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a helpful assistant."

    assistant = Assistant(memory=Memory())

    print("1. Storing different memory types:")

    assistant.remember("User prefers to be addressed as Dr. Smith", memory_type=MemoryType.CORE)
    print("   CORE: User prefers to be addressed as Dr. Smith")

    assistant.remember("User asked about machine learning at 2pm", memory_type=MemoryType.EPISODIC)
    print("   EPISODIC: User asked about machine learning at 2pm")

    assistant.remember("User works in healthcare technology", memory_type=MemoryType.SEMANTIC)
    print("   SEMANTIC: User works in healthcare technology")

    assistant.remember(
        "When user asks about ML, first recommend PyTorch", memory_type=MemoryType.PROCEDURAL
    )
    print("   PROCEDURAL: When user asks about ML, first recommend PyTorch")

    print("\n2. Listing all memories:")
    for mem in assistant.recall():
        print(f"   [{mem.type.value}] {mem.content[:50]}...")


if __name__ == "__main__":
    example_basic_memory()
    example_memory_types()
