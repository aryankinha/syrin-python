"""Lifecycle Events Example - The simple, intuitive way to observe agent lifecycle.

Usage:
    from syrin.enums import Hook

    # Simple one-liners using shortcuts
    agent.events.on_complete(lambda ctx: print(f"Done! Cost: {ctx.cost}"))
    agent.events.on_tool(lambda ctx: print(f"Tool: {ctx.name}"))

    # Or using Hook enums directly
    agent.events.on(Hook.AGENT_RUN_END, lambda ctx: print(f"Done!"))
    agent.events.on(Hook.TOOL_CALL_END, lambda ctx: print(f"Tool: {ctx.name}"))

    # Track everything
    agent.events.on_all(lambda event, ctx: print(f"{event}: {ctx}"))

    # Before/after hooks (can modify behavior!)
    agent.events.before(Hook.LLM_REQUEST_START, lambda ctx: ctx.update({"reminder": "Be concise"}))

Events available via shortcuts:
    - on_start()    : Agent run started
    - on_request() : LLM request made
    - on_response() : LLM response received
    - on_tool()    : Tool executed
    - on_error()   : Error occurred
    - on_complete(): Agent run finished
    - on_budget()  : Budget check

Run: python -m examples.advanced.hooks
"""

from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent
from syrin.enums import Hook

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def example_simple_logging():
    """Simplest possible logging."""
    print("\n" + "=" * 50)
    print("Simple Logging")
    print("=" * 50)

    agent = Agent(
        model=almock,
        system_prompt="You are a helpful assistant.",
    )

    # Simple one-liner logging using shortcut
    agent.events.on_complete(lambda ctx: print(f"  → Done! Cost: ${ctx.get('cost', 0):.6f}"))

    result = agent.response("Hello!")
    print(f"\nResponse: {result.content[:50]}...")


def example_track_cost():
    """Track total cost across multiple requests."""
    print("\n" + "=" * 50)
    print("Track Cost")
    print("=" * 50)

    total_cost = {"total": 0.0}

    def track_cost(ctx):
        total_cost["total"] += ctx.get("cost", 0)

    agent = Agent(
        model=almock,
        system_prompt="You are a helpful assistant.",
    )

    agent.events.on_response(track_cost)

    agent.response("Hello")
    agent.response("How are you?")
    agent.response("What's the weather?")

    print(f"Total cost: ${total_cost['total']:.6f}")


def example_listen_to_all():
    """Listen to ALL events."""
    print("\n" + "=" * 50)
    print("Listen to All Events")
    print("=" * 50)

    def log_all(event, ctx):
        print(f"  [{event.value if hasattr(event, 'value') else event}]")

    agent = Agent(
        model=almock,
        system_prompt="You are a helpful assistant.",
    )

    agent.events.on_all(log_all)

    result = agent.response("Hi!")
    print(f"\nResponse: {result.content}")


def example_before_after():
    """Use before/after hooks to modify behavior."""
    print("\n" + "=" * 50)
    print("Before/After Hooks")
    print("=" * 50)

    calls = []

    def before_request(ctx):
        calls.append("before_request")
        ctx["custom_temp"] = 0.5

    def after_request(ctx):
        calls.append("after_request")

    agent = Agent(
        model=almock,
        system_prompt="You are a helpful assistant.",
    )

    agent.events.before(Hook.LLM_REQUEST_START, before_request)
    agent.events.after(Hook.LLM_REQUEST_END, after_request)

    result = agent.response("Say hi")
    print(f"Hooks called: {calls}")
    print(f"Response: {result.content[:30]}...")


def example_tool_tracking():
    """Track tool execution."""
    print("\n" + "=" * 50)
    print("Tool Tracking")
    print("=" * 50)

    from syrin.tool import tool

    @tool
    def calculate(expr: str) -> str:
        """Evaluate a math expression."""
        return str(eval(expr))

    class CalcAgent(Agent):
        model = almock
        system_prompt = "Use the calculate tool for math."
        tools = [calculate]

    agent = CalcAgent()

    tool_calls = []

    def on_tool(ctx):
        tool_calls.append({"name": ctx.name, "args": ctx.arguments})

    agent.events.on_tool(on_tool)

    result = agent.response("What is 10 + 20?")
    print(f"Tool calls tracked: {tool_calls}")
    print(f"Response: {result.content}")


if __name__ == "__main__":
    examples = [
        example_simple_logging,
        example_track_cost,
        example_listen_to_all,
        example_before_after,
        example_tool_tracking,
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"Error in {example.__name__}: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 50)
    print("All examples completed!")
    print("=" * 50)
