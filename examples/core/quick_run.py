"""Quick start example using syrin.run().

This demonstrates the simplest way to use Syrin - a single function call
without needing to create an Agent instance.
"""

from pathlib import Path

from dotenv import load_dotenv

import syrin

# Configure global settings (optional)
syrin.configure(trace=True)

# Load environment
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Simple one-shot call - just pass input and model
result = syrin.run(
    "What is the capital of France?",
    model="openai/gpt-4o-mini",
)

print(f"Answer: {result.content}")
print(f"Cost: ${result.cost:.4f}")
print(f"Tokens: {result.tokens.total_tokens}")

# Using model string with provider prefix (auto-detected)
result2 = syrin.run(
    "Summarize this in one sentence: Python is a great programming language.",
    model="openai/gpt-4o-mini",
)
print(f"\n{result2.content}")

# Using Model instance
result3 = syrin.run(
    "What is 2+2?",
    model=syrin.Model.OpenAI("gpt-4o"),
)
print(f"\n{result3.content}")

# With system prompt
result4 = syrin.run(
    "What is Python?",
    model="openai/gpt-4o-mini",
    system_prompt="Explain like I'm five years old.",
)
print(f"\n{result4.content}")

# With budget control
budget = syrin.Budget(
    run=0.10,  # $0.10 max per run
    on_exceeded=syrin.raise_on_exceeded,
)
result5 = syrin.run(
    "Hello!",
    model="openai/gpt-4o-mini",
    budget=budget,
)
print(f"\n{result5.content}")
print(f"Budget used: ${result5.cost:.4f}")
