"""Simple Events Example - Demonstrates the new intuitive events API.

This is the new, simple way to observe and react to agent lifecycle events.

Usage:
    agent.on("start", lambda ctx: print(f"Starting: {ctx.input}"))
    agent.on("complete", lambda ctx: print(f"Done! Cost: {ctx.cost}"))
    agent.on("tool", lambda ctx: print(f"Tool: {ctx.name}"))

Run: python -m examples.simple_events
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from syrin import Agent, Model

load_dotenv(Path(__file__).resolve().parent / ".env")

MODEL_ID = os.getenv("OPENAI_MODEL_NAME", "openai/gpt-4o-mini")


def example_simple_logging():
    """Simplest possible logging."""
    print("\n" + "=" * 50)
    print("Simple Logging")
    print("=" * 50)

    agent = Agent(
        model=Model(MODEL_ID),
        system_prompt="You are a helpful assistant.",
    )

    # Simple one-liner logging
    agent.events.on("complete", lambda ctx: print(f"  → Done! Cost: ${ctx.cost:.6f}"))

    result = agent.response("Hello!")
    print(f"Response: {result.content[:50]}...")


def example_track_cost():
    """Track total cost across multiple requests."""
    print("\n" + "=" * 50)
    print("Track Cost Across Requests")
    print("=" * 50)

    total_cost = {"total": 0.0}

    def track_cost(ctx):
        total_cost["total"] += ctx.cost

    agent = Agent(
        model=Model(MODEL_ID),
        system_prompt="You are a helpful assistant.",
    )

    # Track cost on every response
    agent.events.on_response(track_cost)

    agent.response("Hello")
    agent.response("How are you?")
    agent.response("What's the weather?")

    print(f"Total cost: ${total_cost['total']:.6f}")


def example_tool_tracking():
    """Track tool usage."""
    print("\n" + "=" * 50)
    print("Tool Tracking")
    print("=" * 50)

    tools_used = []

    def track_tool(ctx):
        tools_used.append(
            {
                "name": ctx.name,
                "duration": ctx.duration,
            }
        )

    from syrin import tool

    @tool
    def calculate(a: float, b: float) -> str:
        """Calculate a + b."""
        return str(a + b)

    # Note: tool execution needs fixing - this is just for demonstration
    agent = Agent(
        model=Model(MODEL_ID),
        system_prompt="You are a helpful assistant.",
        tools=[calculate],
    )

    agent.events.on_tool(track_tool)

    # This will work once tool execution is fixed
    print("(Tool tracking registered - will track when tools are executed)")


def example_on_all_events():
    """Listen to ALL events at once."""
    print("\n" + "=" * 50)
    print("Listen to All Events")
    print("=" * 50)

    events_logged = []

    def log_all(event, ctx):
        events_logged.append(event)
        print(f"  [{event}]")

    agent = Agent(
        model=Model(MODEL_ID),
        system_prompt="You are a helpful assistant.",
    )

    agent.events.on_all(log_all)

    agent.response("Hi!")

    print(f"\nEvents received: {events_logged}")


def example_before_hook():
    """Use before() to modify behavior."""
    print("\n" + "=" * 50)
    print("Before Hook (modify behavior)")
    print("=" * 50)

    def add_reminder(ctx):
        ctx["user_reminder"] = "Be concise in your response."

    agent = Agent(
        model=Model(MODEL_ID),
        system_prompt="You are a helpful assistant.",
    )

    agent.events.before("request", add_reminder)

    print("(Before hook registered - will add reminder to requests)")


def example_error_handling():
    """Handle errors via events."""
    print("\n" + "===")
    print("Error Handling")
    print("===")

    errors = []

    def handle_error(ctx):
        errors.append(ctx.error)
        print(f"  Error caught: {ctx.error}")

    agent = Agent(
        model=Model(MODEL_ID),
        system_prompt="You are a helpful assistant.",
    )

    agent.events.on_error(handle_error)

    print("(Error handler registered)")


if __name__ == "__main__":
    example_simple_logging()
    example_track_cost()
    example_on_all_events()
    example_before_hook()
    example_error_handling()
