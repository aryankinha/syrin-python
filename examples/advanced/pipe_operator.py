"""Pipe Operator Example.

Demonstrates:
- Using pipe() function for chaining functions
- Using Pipe class for fluent API
- Using | operator for piping
- Handling async functions

Run: python -m examples.advanced.pipe_operator
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent, Pipe, pipe

logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def add_exclamation(text: str) -> str:
    return text + "!"


def uppercase(text: str) -> str:
    return text.upper()


def add_greeting(text: str) -> str:
    return f"Hello! {text}"


def example_basic_pipe() -> None:
    """Basic pipe usage with pipe() function."""
    print("\n" + "=" * 50)
    print("Basic Pipe Example")
    print("=" * 50)

    # pipe(value, fn1, fn2, ...) applies functions in sequence
    result = pipe(
        "hello world",
        add_exclamation,
        uppercase,
    )

    print("Input: 'hello world'")
    print(f"Output: '{result}'")


def example_pipe_class() -> None:
    """Using Pipe class for fluent API."""
    print("\n" + "=" * 50)
    print("Pipe Class Example")
    print("=" * 50)

    result = Pipe("hello").then(add_exclamation).then(uppercase).then(add_greeting).result()

    print(f"Result: '{result}'")


def example_pipe_or_operator() -> None:
    """Using | operator for piping."""
    print("\n" + "=" * 50)
    print("Pipe | Operator Example")
    print("=" * 50)

    result = (Pipe("hello world") | add_exclamation | uppercase | add_greeting).result()

    print(f"Result: '{result}'")


def example_pipe_with_agent() -> None:
    """Using pipe with an agent."""
    print("\n" + "=" * 50)
    print("Pipe with Agent Example")
    print("=" * 50)

    class TransformAgent(Agent):
        model = almock
        system_prompt = "You are a helpful assistant."

    agent = TransformAgent()

    def process_with_agent(text: str) -> str:
        response = agent.response(text)
        return response.content

    def extract_answer(text: str) -> str:
        return text.strip()

    result = pipe(
        "What is Python?",
        process_with_agent,
        extract_answer,
    ).result()

    print("Input: 'What is Python?'")
    print(f"Output: {result[:100]}...")


def example_pipe_multiple_values() -> None:
    """Piping through multiple transformations."""
    print("\n" + "=" * 50)
    print("Multiple Transformations")
    print("=" * 50)

    def split_words(text: str) -> list[str]:
        return text.split()

    def count_words(words: list[str]) -> int:
        return len(words)

    def format_count(count: int) -> str:
        return f"Word count: {count}"

    result = pipe(
        "hello world from python",
        split_words,
        count_words,
        format_count,
    )

    print("Input: 'hello world from python'")
    print(f"Output: '{result}'")


async def async_double(x: int) -> int:
    await asyncio.sleep(0.1)  # Simulate async work
    return x * 2


async def async_add(x: int) -> int:
    await asyncio.sleep(0.1)
    return x + 10


def example_pipe_async() -> None:
    """Using pipe with async functions."""
    print("\n" + "=" * 50)
    print("Pipe with Async Example")
    print("=" * 50)

    async def run_async_pipe():
        result = Pipe(5).then(async_double).then(async_add).result()
        return result

    result = asyncio.run(run_async_pipe())
    print("Input: 5")
    print(f"Output: {result}")


def example_pipe_async_method() -> None:
    """Using result_async for async pipes."""
    print("\n" + "=" * 50)
    print("Result Async Example")
    print("=" * 50)

    async def run():
        result = Pipe(10).then(async_double).then(async_add).then(async_double)
        return await result.result_async()

    result = asyncio.run(run())
    print("Input: 10")
    print(f"Output: {result}")


def example_pipe_lambda() -> None:
    """Using lambda functions with pipe."""
    print("\n" + "=" * 50)
    print("Lambda Functions Example")
    print("=" * 50)

    result = pipe(
        "  hello world  ",
        lambda x: x.strip(),
        lambda x: x.upper(),
        lambda x: f"**{x}**",
    )

    print(f"Result: '{result}'")


def example_pipe_complex() -> None:
    """Complex pipe example with data processing."""
    print("\n" + "=" * 50)
    print("Complex Pipe Example")
    print("=" * 50)

    data = {
        "name": "John",
        "age": 30,
        "city": "New York",
    }

    def extract_values(d: dict) -> list:
        return list(d.values())

    def to_strings(items: list) -> list:
        return [str(item) for item in items]

    def join_with_pipe(items: list) -> str:
        return " | ".join(items)

    result = pipe(
        data,
        extract_values,
        to_strings,
        join_with_pipe,
    )

    print(f"Input: {data}")
    print(f"Output: '{result}'")


if __name__ == "__main__":
    example_basic_pipe()
    example_pipe_class()
    example_pipe_or_operator()
    example_pipe_with_agent()
    example_pipe_multiple_values()
    example_pipe_async()
    example_pipe_async_method()
    example_pipe_lambda()
    example_pipe_complex()
