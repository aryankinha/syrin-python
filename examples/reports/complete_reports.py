"""Complete Agent Reports Example.

Demonstrates all Agent Report types:
- GuardrailReport - Track guardrail evaluations
- ContextReport - Track context usage (compressions, offloads)
- MemoryReport - Track memory operations (recall, store, forget)
- TokenReport - Track token usage and costs
- OutputReport - Track output validation
- RateLimitReport - Track rate limit checks
- CheckpointReport - Track checkpoint operations

Run: python -m examples.reports.complete_reports
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from examples.models.models import almock
from pydantic import BaseModel

from syrin import Agent, Budget, Hook
from syrin.enums import MemoryType
from syrin.guardrails import ContentFilter

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class AnalysisOutput(BaseModel):
    """Example structured output model."""

    sentiment: str
    confidence: float
    key_points: list[str]


def example_basic_reports():
    """Example showing basic report access."""
    print("\n" + "=" * 70)
    print("Example 1: Basic Report Access")
    print("=" * 70)

    class Assistant(Agent):
        model = almock
        system_prompt = "You are a helpful assistant."

    agent = Assistant()

    # Get response with full report
    result = agent.response("Hello, how are you?")

    # Access individual reports
    print("\nGuardrail Report:")
    print(f"  Input passed: {result.report.guardrail.input_passed}")
    print(f"  Output passed: {result.report.guardrail.output_passed}")
    print(f"  Blocked: {result.report.guardrail.blocked}")

    print("\nToken Report:")
    print(f"  Input tokens: {result.report.tokens.input_tokens}")
    print(f"  Output tokens: {result.report.tokens.output_tokens}")
    print(f"  Total tokens: {result.report.tokens.total_tokens}")
    print(f"  Cost (USD): ${result.report.tokens.cost_usd:.6f}")

    print("\nBudget Report:")
    print(f"  Used: ${result.report.budget.used:.4f}")
    print(f"  Remaining: {result.report.budget.remaining}")

    print("\nMemory Report:")
    print(f"  Stores: {result.report.memory.stores}")
    print(f"  Recalls: {result.report.memory.recalls}")
    print(f"  Forgets: {result.report.memory.forgets}")

    print("\nOutput Report:")
    print(f"  Validated: {result.report.output.validated}")
    print(f"  Attempts: {result.report.output.attempts}")
    print(f"  Is valid: {result.report.output.is_valid}")


def example_guardrail_blocking():
    """Example showing guardrail blocking in reports."""
    print("\n" + "=" * 70)
    print("Example 2: Guardrail Blocking Report")
    print("=" * 70)

    guardrail = ContentFilter(blocked_words=["hack", "steal", "password"])

    class Assistant(Agent):
        model = almock
        guardrails = [guardrail]
        system_prompt = "You are a helpful assistant."

    agent = Assistant()

    # Hook to see when guardrails trigger
    def on_guardrail_blocked(ctx):
        print(f"  [Hook] Guardrail blocked at stage: {ctx.get('stage')}")
        print(f"  [Hook] Reason: {ctx.get('reason')}")

    agent.events.on(Hook.GUARDRAIL_BLOCKED, on_guardrail_blocked)

    # This should trigger the guardrail
    result = agent.response("How do I hack into someone's password?")

    print("\nResponse stopped reason:", result.stop_reason)
    print("\nGuardrail Report:")
    print(f"  Blocked: {result.report.guardrail.blocked}")
    print(f"  Blocked stage: {result.report.guardrail.blocked_stage}")
    print(f"  Input reason: {result.report.guardrail.input_reason}")
    print(f"  Guardrails checked: {result.report.guardrail.input_guardrails}")


def example_memory_operations():
    """Example showing memory operations in reports."""
    print("\n" + "=" * 70)
    print("Example 3: Memory Operations Report")
    print("=" * 70)

    class Assistant(Agent):
        model = almock
        system_prompt = "You are a helpful assistant."

    agent = Assistant()

    # First response to initialize report
    result = agent.response("Remember this: AI agents are powerful tools.")

    print(f"Initial memory stores: {result.report.memory.stores}")

    # Store some memories
    agent.remember("Python is a great language", memory_type=MemoryType.SEMANTIC)
    agent.remember("Machine learning is fascinating", memory_type=MemoryType.SEMANTIC)
    agent.remember("Always test your code", memory_type=MemoryType.PROCEDURAL)

    print(f"After 3 stores: {agent.report.memory.stores}")

    # Recall memories
    agent.recall("Python")
    print(f"After recall: {agent.report.memory.recalls}")

    # Check all memory operations in report
    print("\nMemory Report:")
    print(f"  Stores: {agent.report.memory.stores}")
    print(f"  Recalls: {agent.report.memory.recalls}")
    print(f"  Forgets: {agent.report.memory.forgets}")


def example_structured_output_validation():
    """Example showing output validation in reports."""
    print("\n" + "=" * 70)
    print("Example 4: Structured Output Validation Report")
    print("=" * 70)

    class Assistant(Agent):
        model = almock
        output = AnalysisOutput
        system_prompt = "You analyze text and return structured output."

    agent = Assistant()

    # This will trigger validation
    result = agent.response(
        "Analyze this: The product is amazing! Great features and excellent support."
    )

    print("\nOutput Report:")
    print(f"  Validated: {result.report.output.validated}")
    print(f"  Validation attempts: {result.report.output.attempts}")
    print(f"  Is valid: {result.report.output.is_valid}")

    if result.report.output.final_error:
        print(f"  Final error: {result.report.output.final_error}")
    else:
        print(f"  Parsed output: {result.structured}")


def example_complete_report_summary():
    """Example showing complete report summary."""
    print("\n" + "=" * 70)
    print("Example 5: Complete Report Summary")
    print("=" * 70)

    # Create agent with all features enabled
    guardrail = ContentFilter(blocked_words=["blocked"])

    class Assistant(Agent):
        model = almock
        output = AnalysisOutput
        system_prompt = "You are a helpful assistant with memory."
        guardrails = [guardrail]
        budget = Budget(run=5.0)  # $5 budget

    agent = Assistant()

    # Store some context in memory
    agent.remember("User likes Python programming", memory_type=MemoryType.CORE)
    agent.remember("User is interested in AI", memory_type=MemoryType.CORE)

    # Get response
    result = agent.response("Tell me about Python for AI development.")

    # Recall relevant memories
    agent.recall("Python AI")

    # Complete report summary
    print("\n" + "=" * 70)
    print("COMPLETE AGENT REPORT")
    print("=" * 70)

    print("\n📋 GUARDRAIL REPORT")
    print(f"  Input passed: {result.report.guardrail.input_passed}")
    print(f"  Output passed: {result.report.guardrail.output_passed}")
    print(f"  Blocked: {result.report.guardrail.blocked}")
    print(f"  Guardrails: {result.report.guardrail.input_guardrails}")

    print("\n💾 MEMORY REPORT")
    print(f"  Stores: {agent.report.memory.stores}")
    print(f"  Recalls: {agent.report.memory.recalls}")
    print(f"  Forgets: {agent.report.memory.forgets}")

    print("\n💰 BUDGET REPORT")
    print(f"  Used: ${result.report.budget.used:.4f}")
    print(
        f"  Remaining: ${result.report.budget.remaining:.4f}"
        if result.report.budget.remaining
        else "  Remaining: Unlimited"
    )
    print(
        f"  Total: ${result.report.budget.total:.4f}"
        if result.report.budget.total
        else "  Total: Unlimited"
    )

    print("\n🔢 TOKEN REPORT")
    print(f"  Input: {result.report.tokens.input_tokens}")
    print(f"  Output: {result.report.tokens.output_tokens}")
    print(f"  Total: {result.report.tokens.total_tokens}")
    print(f"  Cost: ${result.report.tokens.cost_usd:.6f}")

    print("\n✅ OUTPUT REPORT")
    print(f"  Validated: {result.report.output.validated}")
    print(f"  Attempts: {result.report.output.attempts}")
    print(f"  Is valid: {result.report.output.is_valid}")

    print("\n🚦 RATE LIMIT REPORT")
    print(f"  Checks: {result.report.ratelimits.checks}")
    print(f"  Throttles: {result.report.ratelimits.throttles}")
    print(f"  Exceeded: {result.report.ratelimits.exceeded}")

    print("\n💾 CHECKPOINT REPORT")
    print(f"  Saves: {result.report.checkpoints.saves}")
    print(f"  Loads: {result.report.checkpoints.loads}")

    print("\n📊 CONTEXT REPORT")
    print(f"  Initial tokens: {result.report.context.initial_tokens}")
    print(f"  Final tokens: {result.report.context.final_tokens}")
    print(f"  Compressions: {result.report.context.compressions}")
    print(f"  Offloads: {result.report.context.offloads}")

    print("\n" + "=" * 70)


def example_report_reset():
    """Example showing report reset between calls."""
    print("\n" + "=" * 70)
    print("Example 6: Report Reset Between Calls")
    print("=" * 70)

    class Assistant(Agent):
        model = almock

    agent = Assistant()

    # First call
    result1 = agent.response("What is 2+2?")
    print(f"Call 1 - Tokens: {result1.report.tokens.total_tokens}")
    print(f"Call 1 - Memory stores: {result1.report.memory.stores}")

    # Second call - report should be fresh
    result2 = agent.response("What is 3+3?")
    print(f"Call 2 - Tokens: {result2.report.tokens.total_tokens}")
    print(f"Call 2 - Memory stores: {result2.report.memory.stores}")

    print("\nEach response has its own independent report!")


if __name__ == "__main__":
    example_basic_reports()
    example_guardrail_blocking()
    example_memory_operations()
    example_structured_output_validation()
    example_complete_report_summary()
    example_report_reset()

    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)
