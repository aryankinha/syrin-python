"""Tools and Tasks Example.

Demonstrates:
- Creating tools with the @tool decorator
- Using type hints for parameter validation
- Tool execution with event hooks
- HumanInTheLoop approval system
- TOON format for token-efficient tool schemas
- Multiple tools working together

Run: python -m examples.core.tools_and_tasks
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent, tool
from syrin.enums import DocFormat
from syrin.loop import HumanInTheLoop, ReactLoop
from syrin.tool import schema_to_toon, tool_schema_to_format

logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
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
def get_weather(city: str, unit: str = "celsius") -> str:
    """Get the current weather for a city.

    Args:
        city: Name of the city
        unit: Temperature unit (celsius or fahrenheit)
    """
    # This is a mock - in real use, call a weather API
    return f"The weather in {city} is 22°{unit[0].upper()}"


@tool
def search_documents(query: str, max_results: int = 5) -> list[str]:
    """Search through documents for matching content.

    Args:
        query: Search query string
        max_results: Maximum number of results to return
    """
    # Mock document search
    mock_docs = [
        "Document 1: Python programming guide",
        "Document 2: Machine learning tutorial",
        "Document 3: Web development best practices",
        "Document 4: Data science handbook",
        "Document 5: API design patterns",
    ]
    return mock_docs[:max_results]


def example_tools() -> None:
    """Demonstrate using tools with an agent."""
    print("\n" + "=" * 50)
    print("Tools Example")
    print("=" * 50)

    class MathAssistant(Agent):
        model = almock
        system_prompt = "You are a helpful assistant that uses tools when needed."
        tools = [calculate, get_weather]

    assistant = MathAssistant()

    # Use the calculator tool
    result = assistant.response("What is 15 times 7?")
    print("Question: What is 15 times 7?")
    print(f"Answer: {result.content}")
    print(f"Tool calls: {len(result.tool_calls)}")
    for tc in result.tool_calls:
        print(f"  - {tc.name}: {tc.arguments}")

    print()

    # Use weather tool
    result = assistant.response("What's the weather in Tokyo?")
    print("Question: What's the weather in Tokyo?")
    print(f"Answer: {result.content}")


def example_tools_with_events() -> None:
    """Demonstrate tool execution with event hooks."""
    print("\n" + "=" * 50)
    print("Tools with Event Hooks")
    print("=" * 50)

    class MathAssistant(Agent):
        model = almock
        system_prompt = "You are a helpful assistant. Use tools for calculations."
        tools = [calculate]
        loop = ReactLoop(max_iterations=3)

    assistant = MathAssistant()

    # Track tool execution via events
    tools_used = []

    def on_tool_event(ctx):
        tools_used.append({"name": ctx.name, "args": ctx.arguments})
        print(f"  🔧 Tool called: {ctx.name}({ctx.arguments})")

    assistant.events.on_tool(on_tool_event)

    print("\nQuestion: What is 25 times 8?")
    result = assistant.response("What is 25 times 8?")
    print(f"Answer: {result.content}")

    if tools_used:
        print("\n✅ Tool was executed via event hook!")
        for t in tools_used:
            print(f"   - {t['name']}: {t['args']}")


def example_human_in_the_loop() -> None:
    """Demonstrate HumanInTheLoop approval system."""
    print("\n" + "=" * 50)
    print("HumanInTheLoop - Tool Approval")
    print("=" * 50)

    approvals_log = []

    async def approve_tool(name: str, args: dict) -> bool:
        """Approve all tools for this demo."""
        approvals_log.append({"name": name, "args": args, "approved": True})
        print(f"  ✅ APPROVED: {name}({args})")
        return True

    class SafeAgent(Agent):
        model = almock
        system_prompt = "You are a safe agent. Use calculate tool for math."
        tools = [calculate]
        loop = HumanInTheLoop(approve=approve_tool, max_iterations=3)

    assistant = SafeAgent()

    print("\nQuestion: What is 100 divided by 5?")
    result = assistant.response("What is 100 divided by 5?")
    print(f"Answer: {result.content}")

    if approvals_log:
        print("\n✅ Approval system working!")
        for a in approvals_log:
            print(f"   - {a['name']}: {a['args']}")


def example_toon_format() -> None:
    """Demonstrate TOON format for tool schemas."""
    print("\n" + "=" * 50)
    print("TOON Format - Token Efficiency")
    print("=" * 50)

    print("\nTool: calculate")
    print("Parameters:", list(calculate.parameters_schema.get("properties", {}).keys()))

    print("\n--- JSON Schema ---")
    json_schema = json.dumps(calculate.parameters_schema, indent=2)
    print(json_schema)
    json_tokens = len(json_schema)

    print("\n--- TOON Schema ---")
    toon_schema = schema_to_toon(calculate.parameters_schema)
    print(toon_schema)
    toon_tokens = len(toon_schema)

    savings = ((json_tokens - toon_tokens) / json_tokens) * 100
    print(f"\nToken savings: {savings:.1f}%")
    print("(TOON uses ~40% fewer tokens than JSON)")

    print("\n--- Format Comparison ---")
    for fmt in [DocFormat.TOON, DocFormat.JSON]:
        schema = tool_schema_to_format(calculate, fmt)
        print(f"\n{fmt.value.upper()}: {len(str(schema))} chars")


def example_multiple_tools() -> None:
    """Demonstrate using multiple tools together."""
    print("\n" + "=" * 50)
    print("Multiple Tools Example")
    print("=" * 50)

    class ResearchAssistant(Agent):
        model = almock
        system_prompt = "You are a research assistant. Use tools to help answer questions."
        tools = [calculate, get_weather, search_documents]

    assistant = ResearchAssistant()

    result = assistant.response(
        "First find documents about Python, then calculate how many days "
        "until the year 2030, and finally check the weather in San Francisco."
    )
    print("Question: Complex multi-tool request")
    print(f"Answer: {result.content}")
    print(f"Tool calls made: {len(result.tool_calls)}")


if __name__ == "__main__":
    print("=" * 50)
    print("Syrin Tools and Tasks Examples")
    print("=" * 50)

    example_tools()
    example_tools_with_events()
    example_human_in_the_loop()
    example_toon_format()
    example_multiple_tools()

    print("\n" + "=" * 50)
    print("✅ All examples complete!")
    print("=" * 50)
