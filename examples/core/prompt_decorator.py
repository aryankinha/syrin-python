"""Prompt Decorator Example.

Demonstrates:
- Using @prompt decorator for parameterized system prompts
- Creating specialized agents from a single template

Run: python -m examples.core.prompt_decorator
"""

from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent, prompt

logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@prompt
def expert_prompt(domain: str, tone: str = "professional") -> str:
    """Generate system prompt for expert agents."""
    return f"You are an expert in {domain}. Provide accurate, detailed, and {tone} responses."


def example_prompt_decorator() -> None:
    """Using @prompt decorator for parameterized prompts."""
    print("\n" + "=" * 50)
    print("Prompt Decorator Example")
    print("=" * 50)

    class ScienceExpert(Agent):
        model = almock
        system_prompt = expert_prompt(domain="quantum physics", tone="academic")

    class BusinessExpert(Agent):
        model = almock
        system_prompt = expert_prompt(domain="business strategy", tone="practical")

    print("1. Created specialized experts from @prompt template:")
    print(f"   Science: {ScienceExpert()._system_prompt[:50]}...")
    print(f"   Business: {BusinessExpert()._system_prompt[:50]}...")

    print("\n2. Each expert answers differently:")
    science = ScienceExpert()
    business = BusinessExpert()

    question = "What is innovation?"
    print(f"   Question: {question}")

    science_result = science.response(question)
    print(f"   Science: {science_result.content[:60]}...")

    business_result = business.response(question)
    print(f"   Business: {business_result.content[:60]}...")


if __name__ == "__main__":
    example_prompt_decorator()
