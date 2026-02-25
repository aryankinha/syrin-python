"""Example: Debugging with debug=True parameter.

Simpler alternative to WorkflowDebugger - just add debug=True to your agent!

Before (with WorkflowDebugger):
    from syrin.cli import WorkflowDebugger
    debugger = WorkflowDebugger(verbose=True)
    debugger.attach(agent)
    result = agent.response("...")
    debugger.print_summary()

After (with debug=True):
    agent = Agent(..., debug=True)
    result = agent.response("...")  # Events print automatically!

The debug=True parameter:
- Works on Agent: Agent(..., debug=True)
- Works on Pipeline: Pipeline(..., debug=True)
- Works on DynamicPipeline: DynamicPipeline(..., debug=True)

When using CLI --trace flag:
- Enables global observability for all agents/pipelines
- Shows span traces in console

Choose what's best for your use case:
1. Single agent debugging -> use debug=True
2. Complex pipeline debugging -> use debug=True or WorkflowDebugger
3. Want to trace everything globally -> use --trace flag
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
    # Option 1: Just add debug=True - events print automatically!
    agent = Agent(
        model=almock,
        system_prompt="You are a helpful assistant with access to tools.",
        tools=[calculator, greet],
        debug=True,
    )

    print("=" * 60)
    print("Running agent with debug=True")
    print("=" * 60)

    result = agent.response("Can you calculate 123 * 456 and then greet me? My name is Alice.")

    print("\n" + "=" * 60)
    print("AGENT RESPONSE")
    print("=" * 60)
    print(result.content)


if __name__ == "__main__":
    main()
