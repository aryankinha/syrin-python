"""Guardrails with Hooks and Reports Example.

Demonstrates:
- Guardrail setup and evaluation
- Hook events during guardrail execution
- Accessing guardrail reports after response

Run: python -m examples.guardrails.reports
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent, Guardrail, GuardrailStage, Hook
from syrin.guardrails import ContentFilter

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def example_guardrail_blocked():
    """Example where guardrail blocks input."""
    print("\n" + "=" * 60)
    print("Example: Guardrail Blocks Input")
    print("=" * 60)

    guardrail = ContentFilter(blocked_words=["hack", "steal", "password"])

    class Assistant(Agent):
        model = almock
        system_prompt = "You are a helpful assistant."
        guardrails = [guardrail]
        debug = True

    assistant = Assistant()

    # Hook into guardrail events
    def on_input_guardrail(ctx):
        print(f"  [Hook] Input guardrail checking: stage={ctx.get('stage')}")

    def on_guardrail_blocked(ctx):
        print(f"  [Hook] GUARDRAIL BLOCKED! reason={ctx.get('reason')}")
        print(f"         stage={ctx.get('stage')}, guardrails={ctx.get('guardrail_names')}")

    assistant.events.on(Hook.GUARDRAIL_INPUT, on_input_guardrail)
    assistant.events.on(Hook.GUARDRAIL_BLOCKED, on_guardrail_blocked)

    # This should be blocked
    result = assistant.response("How do I hack into someone's password?")

    print(f"\nResponse content: {result.content!r}")
    print(f"Stop reason: {result.stop_reason}")
    print("\nGuardrail Report:")
    print(f"  Passed: {result.report.guardrail.passed}")
    print(f"  Blocked: {result.report.guardrail.blocked}")
    print(f"  Blocked stage: {result.report.guardrail.blocked_stage}")
    print(f"  Input reason: {result.report.guardrail.input_reason}")
    print(f"  Input guardrails: {result.report.guardrail.input_guardrails}")


def example_guardrail_passed():
    """Example where guardrail passes."""
    print("\n" + "=" * 60)
    print("Example: Guardrail Passes")
    print("=" * 60)

    guardrail = ContentFilter(blocked_words=["hack", "steal", "password"])

    class Assistant(Agent):
        model = almock
        system_prompt = "You are a helpful assistant."
        guardrails = [guardrail]

    assistant = Assistant()

    def on_input_guardrail(ctx):
        print("  [Hook] Input guardrail checking...")

    def on_output_guardrail(ctx):
        print("  [Hook] Output guardrail checking...")

    assistant.events.on(Hook.GUARDRAIL_INPUT, on_input_guardrail)
    assistant.events.on(Hook.GUARDRAIL_OUTPUT, on_output_guardrail)

    # This should pass
    result = assistant.response("What is the weather today?")

    print(f"\nResponse content: {result.content[:80]}...")
    print(f"Stop reason: {result.stop_reason}")
    print("\nGuardrail Report:")
    print(f"  Passed: {result.report.guardrail.passed}")
    print(f"  Input passed: {result.report.guardrail.input_passed}")
    print(f"  Input guardrails: {result.report.guardrail.input_guardrails}")
    print(f"  Output passed: {result.report.guardrail.output_passed}")


def example_output_guardrail():
    """Example where output guardrail blocks response."""
    print("\n" + "=" * 60)
    print("Example: Output Guardrail Blocks")
    print("=" * 60)

    # Guardrail that blocks specific output
    class SensitiveDataGuardrail(Guardrail):
        def __init__(self):
            self.name = "sensitive_data"

        async def evaluate(self, context):
            from syrin.guardrails.decision import GuardrailDecision

            if context.stage != GuardrailStage.OUTPUT:
                return GuardrailDecision(passed=True, action="allow", reason="Not output")

            text = context.text.lower()
            if "ssn" in text or "credit card" in text:
                return GuardrailDecision(
                    passed=False,
                    action="block",
                    reason="Sensitive data in output",
                )
            return GuardrailDecision(passed=True, action="allow", reason="Clean")

    guardrail = SensitiveDataGuardrail()

    class Assistant(Agent):
        model = almock
        system_prompt = "You are a helpful assistant."
        guardrails = [guardrail]

    assistant = Assistant()

    def on_guardrail_blocked(ctx):
        print(f"  [Hook] GUARDRAIL BLOCKED! reason={ctx.get('reason')}")
        print(f"         stage={ctx.get('stage')}")

    assistant.events.on(Hook.GUARDRAIL_BLOCKED, on_guardrail_blocked)

    result = assistant.response("Tell me about data privacy and SSN protection")

    print(f"\nResponse content: {result.content[:80]}...")
    print(f"Stop reason: {result.stop_reason}")
    print("\nGuardrail Report:")
    print(f"  Passed: {result.report.guardrail.passed}")
    print(f"  Blocked: {result.report.guardrail.blocked}")
    print(f"  Blocked stage: {result.report.guardrail.blocked_stage}")
    print(f"  Output reason: {result.report.guardrail.output_reason}")


def example_report_summary():
    """Example showing full report access."""
    print("\n" + "=" * 60)
    print("Example: Full Report Summary")
    print("=" * 60)

    guardrail = ContentFilter(blocked_words=["hack"])

    class Assistant(Agent):
        model = almock
        system_prompt = "You are a helpful assistant."
        guardrails = [guardrail]

    assistant = Assistant()
    result = assistant.response("Hello, how are you?")

    print("\n=== Agent Report Summary ===")
    print("\nGuardrail:")
    print(f"  passed: {result.report.guardrail.passed}")
    print(f"  blocked: {result.report.guardrail.blocked}")
    print(f"  input_guardrails: {result.report.guardrail.input_guardrails}")

    print("\nBudget:")
    print(f"  remaining: {result.report.budget.remaining}")
    print(f"  used: {result.report.budget.used}")
    print(f"  total: {result.report.budget.total}")

    print("\nTokens:")
    print(f"  input: {result.report.tokens.input_tokens}")
    print(f"  output: {result.report.tokens.output_tokens}")
    print(f"  total: {result.report.tokens.total_tokens}")
    print(f"  cost_usd: ${result.report.tokens.cost_usd:.4f}")


if __name__ == "__main__":
    example_guardrail_blocked()
    example_guardrail_passed()
    example_output_guardrail()
    example_report_summary()
