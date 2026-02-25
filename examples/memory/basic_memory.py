"""Memory Example.

Demonstrates:
- Creating an agent with conversation memory
- Using different memory types (CORE, EPISODIC, SEMANTIC, PROCEDURAL)
- Remember and recall operations

Run: python -m examples.memory.basic_memory
"""

from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent, Memory, MemoryType

logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def example_basic_memory() -> None:
    """Basic memory operations: remember() stores facts; recall() retrieves them."""
    print("\n" + "=" * 50)
    print("Basic Memory Example")
    print("=" * 50)

    class Assistant(Agent):
        model = almock
        system_prompt = "You are a helpful assistant that remembers user preferences."

    assistant = Assistant(memory=Memory())

    print("1. User says their name; we store it in persistent memory:")
    result1 = assistant.response("My name is Alice.")
    assistant.remember("The user's name is Alice.", memory_type=MemoryType.CORE, importance=1.0)
    print(f"   Response: {result1.content}")
    print("   (Stored the user's name in persistent memory.)")

    print("\n2. Second turn (recall finds the stored name):")
    result2 = assistant.response("What's my name?")
    print(f"   Response: {result2.content}")


def example_memory_types() -> None:
    """Different memory types."""
    print("\n" + "=" * 50)
    print("Memory Types Example")
    print("=" * 50)

    class Assistant(Agent):
        model = almock
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
