"""Example: Using debug=True for easy observability.

This example shows how to enable debug logging with a single parameter:
    agent = Agent(..., debug=True)
    pipeline = DynamicPipeline(..., debug=True)

No need to attach a debugger or write custom hooks!
"""

import os

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent
from syrin.tool import tool

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")


@tool(name="calculator", description="Perform calculations")
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        result = eval(expression)
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {e}"


@tool(name="greet", description="Greet someone")
def greet(name: str) -> str:
    """Greet a person by name."""
    return f"Hello, {name}! Welcome to syrin."


def main():
    # Create agent with debug=True - that's it!
    # All events will be printed to console automatically
    agent = Agent(
        model=almock,
        system_prompt="You are a helpful assistant with access to tools.",
        tools=[calculator, greet],
        debug=True,  # <-- Just add this!
    )

    print("=" * 60)
    print("Running agent with debug=True")
    print("=" * 60)
    print()

    # Run the agent - events will be printed automatically
    result = agent.response("Can you calculate 123 * 456 and then greet me? My name is Alice.")

    print("\n" + "=" * 60)
    print("AGENT RESPONSE")
    print("=" * 60)
    print(result.content)
    print()
    print(f"Total cost: ${result.cost:.6f}")


if __name__ == "__main__":
    main()
