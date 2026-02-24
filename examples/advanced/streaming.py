"""Streaming Example.

Demonstrates:
- Using stream() for synchronous streaming
- Using astream() for async streaming
- Handling StreamChunk objects
- Real-time output processing

Run: python -m examples.advanced.streaming
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from syrin import Agent, Model

logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MODEL_ID = os.getenv("OPENAI_MODEL_NAME", "openai/gpt-4o-mini")


def example_stream() -> None:
    """Using stream() for synchronous streaming."""
    print("\n" + "=" * 50)
    print("Stream Example")
    print("=" * 50)

    class StreamAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a helpful assistant."

    agent = StreamAgent()

    print("Streaming response:")
    chunks = []
    for chunk in agent.stream("Tell me a short story"):
        chunks.append(chunk)
        print(f"[{chunk.index}] {chunk.text}", end="", flush=True)

    print("\n")
    print(f"Total chunks: {len(chunks)}")


def example_stream_chunk() -> None:
    """Understanding StreamChunk objects."""
    print("\n" + "=" * 50)
    print("Stream Chunk Properties")
    print("=" * 50)

    class StreamAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a helpful assistant."

    agent = StreamAgent()

    for chunk in agent.stream("What is AI?"):
        print(f"Index: {chunk.index}")
        print(f"Text: {chunk.text}")
        print(f"Is first: {chunk.is_first}")
        print(f"Is last: {chunk.is_last}")
        print(f"Tokens so far: {chunk.tokens_so_far}")
        print("---")
        break  # Just show first chunk


async def example_astream() -> None:
    """Using astream() for async streaming."""
    print("\n" + "=" * 50)
    print("Async Stream Example")
    print("=" * 50)

    class AsyncStreamAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a helpful assistant."

    agent = AsyncStreamAgent()

    print("Async streaming response:")
    full_text = ""
    async for chunk in agent.astream("Explain machine learning"):
        full_text += chunk.text
        print(f"[{chunk.index}] {chunk.text}", end="", flush=True)

    print("\n")
    print(f"Total text length: {len(full_text)}")


async def example_astream_with_metrics() -> None:
    """Streaming with metrics tracking."""
    print("\n" + "=" * 50)
    print("Stream with Metrics")
    print("=" * 50)

    class MetricsAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a helpful assistant."

    agent = MetricsAgent()

    total_tokens = 0
    chunk_count = 0

    async for chunk in agent.astream("Hello"):
        chunk_count += 1
        total_tokens = chunk.tokens_so_far

    print(f"Chunks received: {chunk_count}")
    print(f"Final token count: {total_tokens}")


def example_stream_collect() -> None:
    """Collecting stream chunks."""
    print("\n" + "=" * 50)
    print("Collect Stream Chunks")
    print("=" * 50)

    class CollectAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a helpful assistant."

    agent = CollectAgent()

    # Collect all chunks into a list
    chunks = list(agent.stream("Count to 3"))

    # Combine text
    full_text = "".join(c.text for c in chunks)

    print(f"Chunks: {len(chunks)}")
    print(f"Full text: '{full_text}'")


async def example_stream_processing() -> None:
    """Processing stream chunks in real-time."""
    print("\n" + "=" * 50)
    print("Real-time Processing")
    print("=" * 50)

    class ProcessingAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a helpful assistant."

    agent = ProcessingAgent()

    word_count = 0
    async for chunk in agent.astream("Write a short poem"):
        words = chunk.text.split()
        word_count += len(words)

        if chunk.is_last:
            print(f"\nFinal word count: {word_count}")


def example_stream_with_tools() -> None:
    """Streaming with tool calls."""
    print("\n" + "=" * 50)
    print("Stream with Tools")
    print("=" * 50)

    from syrin import tool

    @tool
    def calculate(a: float, b: float) -> str:
        return str(a + b)

    class ToolStreamAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "Use the calculator tool."
        tools = [calculate]

    agent = ToolStreamAgent()

    # Stream can include tool call information
    for chunk in agent.stream("What is 5 + 3?"):
        if chunk.tool_call:
            print(f"[TOOL] {chunk.tool_call}")
        else:
            print(f"[TEXT] {chunk.text}", end="", flush=True)


async def main() -> None:
    """Run all async examples."""
    await example_astream()
    await example_astream_with_metrics()
    await example_stream_processing()
    example_stream()
    example_stream_chunk()
    example_stream_collect()
    example_stream_with_tools()


if __name__ == "__main__":
    asyncio.run(main())
