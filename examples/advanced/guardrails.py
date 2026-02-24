"""Guardrails Example.

Demonstrates:
- Using BlockedWordsGuardrail to filter inappropriate content
- Using LengthGuardrail to enforce text length limits
- Creating custom guardrails
- Using GuardrailChain to combine multiple guardrails

Run: python -m examples.advanced.guardrails
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from syrin import Agent, Model
from syrin.enums import GuardrailStage
from syrin.guardrails import (
    BlockedWordsGuardrail,
    Guardrail,
    GuardrailChain,
    GuardrailContext,
    GuardrailDecision,
    LengthGuardrail,
)

logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MODEL_ID = os.getenv("OPENAI_MODEL_NAME", "openai/gpt-4o-mini")


def example_blocked_words() -> None:
    """Using BlockedWordsGuardrail to filter inappropriate content."""
    print("\n" + "=" * 50)
    print("Blocked Words Guardrail")
    print("=" * 50)

    blocked = BlockedWordsGuardrail(blocked_words=["spam", "scam", "phishing"], name="NoSpam")

    # Test with clean text
    result = blocked.check("Hello, this is a legitimate message", GuardrailStage.INPUT)
    print(f"Clean text - Passed: {result.passed}")

    # Test with blocked word
    result = blocked.check("This is a spam message", GuardrailStage.INPUT)
    print(f"Spam text - Passed: {result.passed}, Reason: {result.reason}")


def example_length_guardrail() -> None:
    """Using LengthGuardrail to enforce text length."""
    print("\n" + "=" * 50)
    print("Length Guardrail")
    print("=" * 50)

    length_guard = LengthGuardrail(min_length=10, max_length=100, name="LengthCheck")

    # Test with too short text
    result = length_guard.check("Hi", GuardrailStage.INPUT)
    print(f"Short text - Passed: {result.passed}, Reason: {result.reason}")

    # Test with valid length
    result = length_guard.check("Hello, this is a valid message", GuardrailStage.INPUT)
    print(f"Valid text - Passed: {result.passed}")

    # Test with too long text
    result = length_guard.check("x" * 200, GuardrailStage.INPUT)
    print(f"Long text - Passed: {result.passed}, Reason: {result.reason}")


def example_guardrail_chain() -> None:
    """Using GuardrailChain to combine multiple guardrails."""
    print("\n" + "=" * 50)
    print("Guardrail Chain")
    print("=" * 50)

    chain = GuardrailChain(
        [
            BlockedWordsGuardrail(["badword", "inappropriate"]),
            LengthGuardrail(min_length=5, max_length=500),
        ]
    )

    # Valid input
    result = chain.check("This is a perfectly valid message", GuardrailStage.INPUT)
    print(f"Valid - Passed: {result.passed}")

    # Too short
    result = chain.check("Hi", GuardrailStage.INPUT)
    print(f"Too short - Passed: {result.passed}, Reason: {result.reason}")

    # Contains blocked word
    result = chain.check("This contains badword in it", GuardrailStage.INPUT)
    print(f"Blocked word - Passed: {result.passed}, Reason: {result.reason}")

    print(f"Total guardrails in chain: {len(chain)}")


def example_custom_guardrail() -> None:
    """Creating a custom guardrail."""
    print("\n" + "=" * 50)
    print("Custom Guardrail")
    print("=" * 50)

    class EmailGuardrail(Guardrail):
        """Guardrail that checks for valid email patterns."""

        async def evaluate(self, context: GuardrailContext) -> GuardrailDecision:
            text = context.text or ""
            if "@" in text and "." in text.split("@")[-1]:
                return GuardrailDecision(
                    passed=True,
                    rule="email_check",
                    reason="Valid email found",
                    metadata={"email_found": True},
                )
            return GuardrailDecision(
                passed=False,
                rule="email_check",
                reason="No valid email found in text",
            )

    email_guard = EmailGuardrail(name="EmailCheck")

    import asyncio

    async def test_email_guard():
        ctx = GuardrailContext(text="Contact me at john@example.com", stage=GuardrailStage.INPUT)
        result = await email_guard.evaluate(ctx)
        print(f"With email - Passed: {result.passed}, Metadata: {result.metadata}")

        ctx2 = GuardrailContext(text="Contact me later", stage=GuardrailStage.INPUT)
        result2 = await email_guard.evaluate(ctx2)
        print(f"Without email - Passed: {result2.passed}, Reason: {result2.reason}")

    asyncio.run(test_email_guard())


def example_guardrail_with_agent() -> None:
    """Using guardrails with an agent (manual integration)."""
    print("\n" + "=" * 50)
    print("Guardrails with Agent")
    print("=" * 50)

    # Create guardrail chain
    guardrails = GuardrailChain(
        [
            BlockedWordsGuardrail(["forbidden", "blocked"]),
            LengthGuardrail(min_length=1, max_length=1000),
        ]
    )

    class SafeAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a helpful assistant."

    agent = SafeAgent()

    # Validate input before sending to agent
    user_input = "Hello, how are you?"
    result = guardrails.check(user_input, GuardrailStage.INPUT)

    if result.passed:
        response = agent.response(user_input)
        print("Input passed guardrails")
        print(f"Response: {response.content[:100]}...")
    else:
        print(f"Input blocked: {result.reason}")

    # Test blocked input
    user_input = "This contains forbidden content"
    result = guardrails.check(user_input, GuardrailStage.INPUT)
    if not result.passed:
        print(f"Blocked input: {result.reason}")


def example_output_guardrail() -> None:
    """Using guardrails on output."""
    print("\n" + "=" * 50)
    print("Output Guardrails")
    print("=" * 50)

    # Guardrail to check output length
    output_guard = LengthGuardrail(min_length=10, max_length=200, name="OutputLength")

    class ControlledAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "Give very brief answers."

    agent = ControlledAgent()

    # The agent will produce output, which we can then check
    response = agent.response("What is Python?")

    # Check the output
    result = output_guard.check(response.content, GuardrailStage.OUTPUT)
    print(f"Output length check - Passed: {result.passed}")
    print(f"Output: {response.content[:100]}...")


if __name__ == "__main__":
    example_blocked_words()
    example_length_guardrail()
    example_guardrail_chain()
    example_custom_guardrail()
    example_guardrail_with_agent()
    example_output_guardrail()
