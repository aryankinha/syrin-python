"""
Syrin Guardrails - Foundation Layer Examples

Basic guardrails for content filtering, PII detection, and parallel evaluation.
"""

import asyncio

from syrin.enums import GuardrailStage
from syrin.guardrails import (
    ContentFilter,
    Guardrail,
    GuardrailChain,
    GuardrailContext,
    GuardrailDecision,
    ParallelEvaluationEngine,
    PIIScanner,
)


async def example_basic_content_filter():
    """Basic content filtering with blocked words."""
    print("\n=== Basic Content Filter ===\n")

    guardrail = ContentFilter(
        blocked_words=["password", "secret", "api_key"], name="security_filter"
    )

    # Test with safe text
    safe_context = GuardrailContext(text="Hello, how are you today?", stage=GuardrailStage.INPUT)

    result = await guardrail.evaluate(safe_context)
    print(f"Safe text: {result.passed}")
    print(f"Rule: {result.rule}")

    # Test with blocked text
    blocked_context = GuardrailContext(text="My password is 123456", stage=GuardrailStage.INPUT)

    result = await guardrail.evaluate(blocked_context)
    print(f"\nBlocked text: {not result.passed}")
    print(f"Rule: {result.rule}")
    print(f"Reason: {result.reason}")
    print(f"Alternatives: {result.alternatives}")


async def example_pii_detection():
    """PII detection and redaction."""
    print("\n=== PII Detection ===\n")

    scanner = PIIScanner(name="pii_scanner", redact=True, redaction_char="*")

    context = GuardrailContext(
        text="Contact me at john@example.com or call 555-123-4567", stage=GuardrailStage.INPUT
    )

    result = await scanner.evaluate(context)
    print(f"PII detected: {not result.passed}")
    print(f"Reason: {result.reason}")
    print(f"Findings: {result.metadata['findings']}")
    print(f"Redacted text: {result.metadata.get('redacted_text')}")


async def example_parallel_evaluation():
    """Running multiple guardrails in parallel."""
    print("\n=== Parallel Evaluation ===\n")

    content_filter = ContentFilter(blocked_words=["spam", "scam"])
    pii_scanner = PIIScanner()

    engine = ParallelEvaluationEngine(timeout=5.0)

    # Test text that passes both
    context = GuardrailContext(text="This is a normal message", stage=GuardrailStage.INPUT)

    result = await engine.evaluate(context, [content_filter, pii_scanner])
    print(f"All guardrails passed: {result.passed}")
    print(f"Total latency: {result.total_latency_ms:.2f}ms")
    print(f"Number of checks: {len(result.decisions)}")

    # Test text that fails one
    context = GuardrailContext(
        text="This is spam and my email is test@test.com", stage=GuardrailStage.INPUT
    )

    result = await engine.evaluate(context, [content_filter, pii_scanner])
    print(f"\nBlocked: {not result.passed}")
    print(f"Rule: {result.rule}")
    print(f"Reason: {result.reason}")


async def example_guardrail_chain():
    """Sequential guardrail chain that stops on first failure."""
    print("\n=== Guardrail Chain (Sequential) ===\n")

    chain = GuardrailChain(
        [
            ContentFilter(blocked_words=["blocked"]),
            PIIScanner(),  # Won't run if first fails
        ]
    )

    # Test with text that passes first but has PII
    context = GuardrailContext(
        text="Hello, my email is user@example.com", stage=GuardrailStage.INPUT
    )

    result = await chain.evaluate(context)
    print(f"Chain result: {result.passed}")
    print(f"Decisions evaluated: {len(result.decisions)}")

    # Test with text that fails first
    context = GuardrailContext(text="This is blocked content", stage=GuardrailStage.INPUT)

    result = await chain.evaluate(context)
    print(f"\nBlocked early: {not result.passed}")
    print(f"Decisions evaluated: {len(result.decisions)}")


async def example_custom_guardrail():
    """Creating a custom guardrail."""
    print("\n=== Custom Guardrail ===\n")

    class LengthGuardrail(Guardrail):
        """Custom guardrail that checks message length."""

        def __init__(self, min_length=1, max_length=1000, name=None):
            super().__init__(name)
            self.min_length = min_length
            self.max_length = max_length

        async def evaluate(self, context: GuardrailContext) -> GuardrailDecision:
            length = len(context.text)

            if length < self.min_length:
                return GuardrailDecision(
                    passed=False,
                    rule="too_short",
                    reason=f"Message too short: {length} chars (min: {self.min_length})",
                    metadata={"length": length, "min": self.min_length},
                )

            if length > self.max_length:
                return GuardrailDecision(
                    passed=False,
                    rule="too_long",
                    reason=f"Message too long: {length} chars (max: {self.max_length})",
                    metadata={"length": length, "max": self.max_length},
                )

            return GuardrailDecision(passed=True, rule="length_ok", metadata={"length": length})

    guardrail = LengthGuardrail(min_length=5, max_length=50)

    test_cases = [
        ("Hi", "too short"),
        ("Hello world, this is a great day!", "just right"),
        ("A" * 100, "too long"),
    ]

    for text, description in test_cases:
        context = GuardrailContext(text=text, stage=GuardrailStage.INPUT)
        result = await guardrail.evaluate(context)
        print(f"{description}: passed={result.passed}, length={len(text)}")
        if not result.passed:
            print(f"  Reason: {result.reason}")


async def example_decision_inspection():
    """Inspecting detailed decision information."""
    print("\n=== Decision Inspection ===\n")

    guardrail = ContentFilter(blocked_words=["forbidden"])

    context = GuardrailContext(text="This contains a forbidden word", stage=GuardrailStage.INPUT)

    result = await guardrail.evaluate(context)

    print("Full Decision Details:")
    print(f"  Passed: {result.passed}")
    print(f"  Rule: {result.rule}")
    print(f"  Reason: {result.reason}")
    print(f"  Confidence: {result.confidence}")
    print(f"  Action: {result.action}")
    print(f"  Metadata: {result.metadata}")
    print(f"  Alternatives: {result.alternatives}")
    print("\nJSON Representation:")
    print(result.to_json())


async def main():
    """Run all foundation examples."""
    print("=" * 60)
    print("Syrin Guardrails - Foundation Layer Examples")
    print("=" * 60)

    await example_basic_content_filter()
    await example_pii_detection()
    await example_parallel_evaluation()
    await example_guardrail_chain()
    await example_custom_guardrail()
    await example_decision_inspection()

    print("\n" + "=" * 60)
    print("All foundation examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
