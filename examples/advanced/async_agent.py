"""Async Agent Example.

Demonstrates:
- Using async response methods
- Running async agents properly

Run: python -m examples.advanced.async_agent
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent

logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def example_sync_response() -> None:
    """Using sync response() method."""
    print("\n" + "=" * 50)
    print("Sync Response Example")
    print("=" * 50)

    class Assistant(Agent):
        model = almock
        system_prompt = "You are a helpful assistant."

    assistant = Assistant()

    print("1. Using sync response():")
    result = assistant.response("What is 2 + 2?")
    print(f"   Answer: {result.content}")
    print(f"   Cost: ${result.cost:.6f}")


async def example_async_response() -> None:
    """Using async arun() method."""
    print("\n" + "=" * 50)
    print("Async Response Example")
    print("=" * 50)

    class Assistant(Agent):
        model = almock
        system_prompt = "You are a helpful assistant."

    assistant = Assistant()

    print("1. Using async arun():")
    result = await assistant.arun("What is 2 + 2?")
    print(f"   Answer: {result.content}")
    print(f"   Cost: ${result.cost:.6f}")


async def example_multiple_async() -> None:
    """Running multiple async agents in parallel."""
    print("\n" + "=" * 50)
    print("Multiple Async Agents")
    print("=" * 50)

    class Analyzer(Agent):
        model = almock
        system_prompt = "You are an analyst."

    async def analyze(topic: str) -> None:
        agent = Analyzer()
        result = await agent.arun(f"Give a brief analysis of {topic}")
        print(f"   {topic}: {result.content[:60]}...")

    print("1. Running three analyses in parallel:")
    await asyncio.gather(
        analyze("machine learning"),
        analyze("deep learning"),
        analyze("reinforcement learning"),
    )


def example_sync_wrapper() -> None:
    """Using asyncio.run() to run async code."""
    print("\n" + "=" * 50)
    print("Sync Wrapper Example")
    print("=" * 50)

    async def run_async_examples() -> None:
        await example_async_response()
        await example_multiple_async()

    print("1. Wrapping async code with asyncio.run():")
    asyncio.run(run_async_examples())


if __name__ == "__main__":
    example_sync_response()
    example_sync_wrapper()
