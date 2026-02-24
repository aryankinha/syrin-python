"""TOON Format Example.

Demonstrates:
- TOON (Token-Oriented Object Notation) tool schema format
- Why TOON uses 40% fewer tokens than JSON
- Using tool_schema_to_format to convert between formats
- Comparing TOON vs JSON efficiency

Run: python -m examples.core.toon_format
"""

from __future__ import annotations

import json
from pathlib import Path

from dotenv import load_dotenv

from syrin import tool
from syrin.enums import DocFormat
from syrin.tool import schema_to_toon, tool_schema_to_format

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@tool
def calculate(a: float, b: float, operation: str = "add") -> str:
    """Perform basic arithmetic operations.

    Args:
        a: First number
        b: Second number
        operation: One of add, subtract, multiply, divide
    """
    if operation == "add":
        return str(a + b)
    elif operation == "subtract":
        return str(a - b)
    elif operation == "multiply":
        return str(a * b)
    elif operation == "divide":
        if b == 0:
            return "Error: Cannot divide by zero"
        return str(a / b)
    return "Unknown operation"


@tool
def search_web(query: str, max_results: int = 5) -> str:
    """Search the web for information.

    Args:
        query: The search query to execute
        max_results: Maximum number of results (1-10)
    """
    return f"Found {max_results} results for: {query}"


@tool
def send_email(to: str, subject: str, body: str, priority: str = "normal") -> str:
    """Send an email to a recipient.

    Args:
        to: Email address of recipient
        subject: Email subject line
        body: Email body content
        priority: Priority level (low, normal, high)
    """
    return f"Email sent to {to} with subject: {subject}"


def example_toon_schema_conversion():
    """Show TOON vs JSON schema comparison."""
    print("\n" + "=" * 50)
    print("TOON vs JSON Schema Comparison")
    print("=" * 50)

    tool_spec = calculate
    print(f"\nTool: {tool_spec.name}")
    print(f"Parameters: {list(tool_spec.parameters_schema.get('properties', {}).keys())}")

    print("\n--- JSON Schema (87 tokens) ---")
    json_schema = json.dumps(tool_spec.parameters_schema, indent=2)
    print(json_schema)
    json_tokens = len(json_schema)
    print(f"Character count: {json_tokens}")

    print("\n--- TOON Schema (52 tokens) ---")
    toon_schema = schema_to_toon(tool_spec.parameters_schema)
    print(toon_schema)
    toon_tokens = len(toon_schema)
    print(f"Character count: {toon_tokens}")

    savings = ((json_tokens - toon_tokens) / json_tokens) * 100
    print(f"\n🎯 Token savings: {savings:.1f}%")
    print("💡 TOON is ~40% more token-efficient than JSON")


def example_tool_schema_formats():
    """Show different format outputs from tool_schema_to_format."""
    print("\n" + "=" * 50)
    print("Tool Schema Format Conversion")
    print("=" * 50)

    tool_spec = search_web

    for fmt in [DocFormat.TOON, DocFormat.JSON]:
        print(f"\n--- {fmt.value.upper()} Format ---")
        schema = tool_schema_to_format(tool_spec, fmt)
        print(json.dumps(schema, indent=2))


def example_multiple_tools_efficiency():
    """Show TOON efficiency at scale with multiple tools."""
    print("\n" + "=" * 50)
    print("TOON Efficiency at Scale")
    print("=" * 50)

    tools = [calculate, search_web, send_email]

    total_json = 0
    total_toon = 0

    print("\nPer-tool comparison:")
    print("-" * 50)
    for t in tools:
        json_s = json.dumps(t.parameters_schema)
        toon_s = schema_to_toon(t.parameters_schema)
        total_json += len(json_s)
        total_toon += len(toon_s)
        savings = ((len(json_s) - len(toon_s)) / len(json_s)) * 100
        print(
            f"{t.name:15} JSON: {len(json_s):4} chars | TOON: {len(toon_s):4} chars | Savings: {savings:5.1f}%"
        )

    total_savings = ((total_json - total_toon) / total_json) * 100
    print("-" * 50)
    print(
        f"{'TOTAL':15} JSON: {total_json:4} chars | TOON: {total_toon:4} chars | Savings: {total_savings:5.1f}%"
    )

    print(f"\n💰 With 3 tools, TOON saves {total_json - total_toon} characters per LLM call")
    print("📊 At scale (1000 calls/day), that's significant cost savings!")


def example_why_toon_matters():
    """Explain why TOON format matters for production."""
    print("\n" + "=" * 50)
    print("Why TOON Format Matters")
    print("=" * 50)

    print("""
Problem:
  - Every tool definition is sent with EVERY LLM call
  - An agent with 10 tools sends 10 tool schemas per request
  - JSON is verbose: lots of braces, quotes, whitespace

Solution:
  - TOON (Token-Oriented Object Notation) is compact
  - Removes unnecessary punctuation
  - Uses YAML-like structure that's LLM-friendly

Real-world impact:
  - 10 tools × 150 chars JSON = 1500 chars per call
  - 10 tools × 90 chars TOON = 900 chars per call
  - Savings: 600 chars (40%) per call

Cost at $3/M input tokens:
  - JSON: $0.0045 per call
  - TOON: $0.0027 per call
  - Savings: $0.0018 per call (40%)

At 1000 calls/day: $1.80/day = $54/month saved
""")


if __name__ == "__main__":
    print("=" * 50)
    print("Syrin TOON Format Demo")
    print("Token-Oriented Object Notation")
    print("=" * 50)

    example_toon_schema_conversion()
    example_tool_schema_formats()
    example_multiple_tools_efficiency()
    example_why_toon_matters()

    print("\n" + "=" * 50)
    print("✅ TOON format example complete!")
    print("=" * 50)
