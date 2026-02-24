"""Handoff Example.

Demonstrates:
- Agent handoff between specialized agents
- Context transfer via memory
- Budget transfer between agents

Run: python -m examples.multi_agent.handoff
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from syrin import Agent, Memory, MemoryType, Model, prompt

logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MODEL_ID = os.getenv("OPENAI_MODEL_NAME", "openai/gpt-4o-mini")


@prompt
def analyzer_prompt() -> str:
    """System prompt for analyzer agent."""
    return "You are an analyzer agent. Analyze information and provide key findings."


@prompt
def presenter_prompt() -> str:
    """System prompt for presenter agent."""
    return "You are a presenter agent. Present information clearly and concisely."


def example_handoff() -> None:
    """Simple handoff between agents."""
    print("\n" + "=" * 50)
    print("Handoff Example")
    print("=" * 50)

    class Analyzer(Agent):
        model = Model(MODEL_ID)
        system_prompt = analyzer_prompt()

    class Presenter(Agent):
        model = Model(MODEL_ID)
        system_prompt = presenter_prompt()

    analyzer = Analyzer()

    print("1. Analyzer processes a task:")
    result1 = analyzer.response("Analyze the benefits of renewable energy")
    print(f"   Result: {result1.content[:80]}...")
    print(f"   Cost: ${result1.cost:.6f}")

    print("\n2. Handoff to Presenter:")
    result2 = analyzer.handoff(Presenter, "Present the analysis")
    print(f"   Result: {result2.content[:80]}...")
    print(f"   Cost: ${result2.cost:.6f}")


def example_handoff_with_context() -> None:
    """Handoff with context transfer via memory."""
    print("\n" + "=" * 50)
    print("Handoff with Context Transfer")
    print("=" * 50)

    class Analyzer(Agent):
        model = Model(MODEL_ID)
        system_prompt = analyzer_prompt()

    class Presenter(Agent):
        model = Model(MODEL_ID)
        system_prompt = presenter_prompt()

    analyzer = Analyzer(memory=Memory())
    analyzer.remember(
        "Key finding: AI growth is accelerating at 40% per year", memory_type=MemoryType.SEMANTIC
    )
    print("1. Analyzer stores key finding in memory")

    print("\n2. Handoff with context transfer:")
    result = analyzer.handoff(Presenter, "Present the findings", transfer_context=True)
    print(f"   Result: {result.content[:80]}...")
    print(f"   Cost: ${result.cost:.6f}")

    if result.budget and result.budget.remaining is not None:
        print(f"   Budget remaining: ${result.budget.remaining:.4f}")
        print(f"   Budget used: ${result.budget.used:.4f}")


if __name__ == "__main__":
    example_handoff()
    example_handoff_with_context()
