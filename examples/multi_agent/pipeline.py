"""Pipeline Example.

Demonstrates:
- Sequential pipeline execution
- Parallel pipeline execution
- Pipeline with budget

Run: python -m examples.multi_agent.pipeline
"""

from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent, Budget, Pipeline, prompt

logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@prompt
def researcher_prompt(domain: str) -> str:
    return f"You are a researcher specializing in {domain}."


@prompt
def writer_prompt(style: str) -> str:
    return f"You are a writer with a {style} style."


@prompt
def editor_prompt() -> str:
    return "You are an editor. Improve and refine the given text."


def example_sequential_pipeline() -> None:
    """Sequential pipeline execution."""
    print("\n" + "=" * 50)
    print("Sequential Pipeline Example")
    print("=" * 50)

    class Researcher(Agent):
        model = almock
        system_prompt = researcher_prompt(domain="technology")

    class Writer(Agent):
        model = almock
        system_prompt = writer_prompt(style="professional")

    class Editor(Agent):
        model = almock
        system_prompt = editor_prompt()

    pipeline = Pipeline()

    print("1. Running research -> write -> edit pipeline...")
    result = pipeline.run(
        [
            (Researcher, "Find information about renewable energy"),
            (Writer, "Write about renewable energy"),
            (Editor, "Edit this: Renewable energy comes from natural sources."),
        ]
    )

    print(f"   Final result: {result.content[:80]}...")
    print(f"   Total cost: ${result.cost:.6f}")


def example_parallel_pipeline() -> None:
    """Parallel pipeline execution."""
    print("\n" + "=" * 50)
    print("Parallel Pipeline Example")
    print("=" * 50)

    class Analyst(Agent):
        model = almock
        system_prompt = "You are an analyst."

    pipeline = Pipeline()

    print("1. Running three analyses in parallel...")
    results = pipeline.run(
        [
            (Analyst, "What is machine learning?"),
            (Analyst, "What is deep learning?"),
            (Analyst, "What is reinforcement learning?"),
        ]
    ).parallel()

    for i, result in enumerate(results, 1):
        print(f"   Result {i}: {result.content[:50]}...")
        print(f"   Cost {i}: ${result.cost:.6f}")


def example_pipeline_with_budget() -> None:
    """Pipeline with budget."""
    print("\n" + "=" * 50)
    print("Pipeline with Budget")
    print("=" * 50)

    class Researcher(Agent):
        model = almock
        system_prompt = researcher_prompt(domain="science")

    class Writer(Agent):
        model = almock
        system_prompt = writer_prompt(style="concise")

    pipeline = Pipeline(budget=Budget(run=0.30))

    print("1. Running pipeline with $0.30 budget...")
    result = pipeline.run(
        [
            (Researcher, "Research quantum computing"),
            (Writer, "Write summary"),
        ]
    )

    print(f"   Result: {result.content[:60]}...")
    print(f"   Cost: ${result.cost:.6f}")

    if result.budget:
        print(f"   Budget remaining: ${result.budget.remaining:.4f}")


if __name__ == "__main__":
    example_sequential_pipeline()
    example_parallel_pipeline()
    example_pipeline_with_budget()
