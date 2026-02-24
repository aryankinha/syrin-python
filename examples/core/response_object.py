"""Example demonstrating the Response object structure and all its attributes.

This shows what you get back from syrin.run() and agent.response().
"""

from pathlib import Path

from dotenv import load_dotenv

import syrin

# Load environment
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Simple call
result = syrin.run(
    "What is 2+2?",
    model="openai/gpt-4o-mini",
)

# =============================================================================
# Response Object - All Available Attributes
# =============================================================================

print("=" * 60)
print("RESPONSE OBJECT STRUCTURE")
print("=" * 60)

# Main content
print("\n1. content (main response):")
print(f"   {result.content!r}")

# Raw response (same as content for text)
print("\n2. raw (raw string):")
print(f"   {result.raw!r}")

# Cost information
print("\n3. cost (USD):")
print(f"   ${result.cost:.6f}")

# Token usage breakdown
print("\n4. tokens (TokenUsage object):")
print(f"   input_tokens:  {result.tokens.input_tokens}")
print(f"   output_tokens: {result.tokens.output_tokens}")
print(f"   total_tokens:  {result.tokens.total_tokens}")

# Model used
print("\n5. model:")
print(f"   {result.model}")

# Duration
print("\n6. duration (seconds):")
print(f"   {result.duration:.3f}s")

# Stop reason
print("\n7. stop_reason:")
print(f"   {result.stop_reason}")

# Budget information (when budget is set)
print("\n8. budget_remaining:")
print(f"   {result.budget_remaining}")

print("\n9. budget_used:")
print(f"   ${result.budget_used:.6f}" if result.budget_used is not None else "   None")

# Trace (list of steps)
print("\n10. trace (execution steps):")
for i, step in enumerate(result.trace):
    print(f"    Step {i + 1}:")
    print(f"      step_type: {step.step_type}")
    print(f"      model: {step.model}")
    print(f"      tokens: {step.tokens}")
    print(f"      cost_usd: ${step.cost_usd:.6f}")
    print(f"      latency_ms: {step.latency_ms:.1f}ms")

# Tool calls (if any)
print("\n11. tool_calls:")
print(f"   {result.tool_calls}")

# Boolean check
print("\n12. bool(response) - success check:")
print(f"   {bool(result)}")

# Budget property (convenience)
print("\n13. response.budget (property):")
print(f"   {result.budget}")

# =============================================================================
# Example with budget
# =============================================================================

print("\n" + "=" * 60)
print("EXAMPLE WITH BUDGET")
print("=" * 60)

budget = syrin.Budget(
    run=0.10,  # $0.10 max per run
    on_exceeded=syrin.raise_on_exceeded,
)

result_with_budget = syrin.run(
    "Hello!",
    model="openai/gpt-4o-mini",
    budget=budget,
)

print(f"\nContent: {result_with_budget.content}")
print(f"Cost: ${result_with_budget.cost:.6f}")
print(f"Budget remaining: ${result_with_budget.budget_remaining:.4f}")
print(f"Budget used: ${result_with_budget.budget_used:.6f}")
print(f"Budget status: {result_with_budget.budget}")

# =============================================================================
# Example with structured output
# =============================================================================

print("\n" + "=" * 60)
print("EXAMPLE WITH STRUCTURED OUTPUT")
print("=" * 60)


# Define the expected output structure using @structured decorator
@syrin.structured
class MathResult:
    expression: str
    result: int
    verified: bool


# Use the structured output by passing it to the Model
model_with_output = syrin.Model.OpenAI("gpt-4o-mini", output=MathResult)

result_structured = syrin.run(
    "What is 15 + 27?",
    model=model_with_output,
)

print(f"\nContent (raw text): {result_structured.content}")
print(f"Tokens used: {result_structured.tokens.total_tokens}")
print(f"Cost: ${result_structured.cost:.6f}")

# Access structured output - now it's automatic!
print("\nStructured output:")
print(f"  result.raw = {result_structured.raw}")
print(f"  result.data = {result_structured.data}")
print(f"  result.data.result = {result_structured.data.get('result')}")
print(f"  result.structured = {result_structured.structured}")
print(f"  result.structured.parsed = {result_structured.structured.parsed}")

# Another example
result_structured2 = syrin.run(
    "What is 100 - 42?",
    model=model_with_output,
)

print("\nSecond query:")
print(f"  result.data.result = {result_structured2.data.get('result')}")
print(f"  result.data.expression = {result_structured2.data.get('expression')}")
