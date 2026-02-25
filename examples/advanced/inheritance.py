"""Agent Inheritance Example.

Demonstrates:
- Creating agent classes with inheritance
- Merging tools from parent classes
- Overriding system prompts and budgets

Run: python -m examples.advanced.inheritance
"""

from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent, tool

logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def example_inheritance() -> None:
    """Agent class inheritance."""
    print("\n" + "=" * 50)
    print("Agent Inheritance Example")
    print("=" * 50)

    @tool
    def repeat(text: str, count: int = 1) -> str:
        """Repeat text count times."""
        return " ".join([text] * count)

    class BaseAgent(Agent):
        model = almock
        system_prompt = "You are a helpful assistant."
        tools = [repeat]

    class SpecializedAgent(BaseAgent):
        system_prompt = "You are a specialized assistant."

    print("1. Base agent tools:", [t.name for t in BaseAgent()._tools])
    print("2. Specialized inherits tools:", [t.name for t in SpecializedAgent()._tools])
    print("3. Specialized prompt:", SpecializedAgent()._system_prompt[:50], "...")

    result = SpecializedAgent().response("Say hello")
    print(f"\n4. Response: {result.content}")


if __name__ == "__main__":
    example_inheritance()
