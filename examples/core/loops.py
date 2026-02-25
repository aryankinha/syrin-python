"""Example demonstrating Loop strategies in syrin.

Simple and clean API for controlling agent execution loops.
"""

from pathlib import Path

# Load .env from examples/ directory
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv

    load_dotenv(env_path)

from examples.models.models import almock
from syrin import Agent
from syrin.loop import (
    CodeActionLoop,
    HumanInTheLoop,
    LoopResult,
    PlanExecuteLoop,
    ReactLoop,
    SingleShotLoop,
)

model = almock


def example_single_shot():
    """SingleShotLoop - One LLM call, no tool iteration."""
    print("\n=== SingleShotLoop ===")
    print("Use case: Simple questions that don't need tools")

    agent = Agent(
        model=model,
        loop=SingleShotLoop(),  # Simple!
    )

    response = agent.response("What is the capital of France?")
    print("Q: What is the capital of France?")
    print(f"A: {response.content}")


def example_react():
    """ReactLoop - Think → Act → Observe (default)."""
    print("\n=== ReactLoop ===")
    print("Use case: Multi-step tasks with tools")

    agent = Agent(
        model=model,
        loop=ReactLoop(max_iterations=5),
    )

    response = agent.response("What is 5 + 3?")
    print("Q: What is 5 + 3?")
    print(f"A: {response.content}")


def example_human_in_the_loop():
    """HumanInTheLoop - Human approval for tools."""
    print("\n=== HumanInTheLoop ===")
    print("Use case: Safety-critical apps needing human oversight")

    approved_count = 0

    async def approve(tool_name: str, args: dict) -> bool:
        """Simple approval callback."""
        nonlocal approved_count
        approved_count += 1
        print(f"  🔔 Tool '{tool_name}' called, args: {args}")
        return True  # Allow all

    agent = Agent(
        model=model,
        loop=HumanInTheLoop(approve=approve, max_iterations=5),
    )

    response = agent.response("What is the square root of 144?")
    print("Q: What is the square root of 144?")
    print(f"A: {response.content}")
    print(f"Tools evaluated: {approved_count}")


def example_plan_execute():
    """PlanExecuteLoop - Plan all steps, then execute each."""
    print("\n=== PlanExecuteLoop ===")
    print("Use case: Complex multi-step tasks that benefit from upfront planning")

    agent = Agent(
        model=model,
        loop=PlanExecuteLoop(
            max_plan_iterations=3,
            max_execution_iterations=10,
        ),
    )

    response = agent.response(
        "Research the top 3 programming languages in 2024 and summarize their pros and cons"
    )
    print("Q: Research programming languages")
    print(f"A: {response.content[:300]}...")
    print(f"Iterations: {response.iterations}")


def example_code_action():
    """CodeActionLoop - LLM writes Python code to execute."""
    print("\n=== CodeActionLoop ===")
    print("Use case: Mathematical computations, data processing")

    agent = Agent(
        model=model,
        loop=CodeActionLoop(
            max_iterations=5,
            timeout_seconds=30,
        ),
    )

    response = agent.response("What is the sum of all even numbers from 1 to 100?")
    print("Q: Sum of even numbers 1-100?")
    print(f"A: {response.content}")
    print(f"Iterations: {response.iterations}")


def example_custom_loop():
    """Custom loop - Implement your own strategy."""
    print("\n=== Custom Loop ===")
    print("Use case: Specialized execution patterns")

    class MyLoop:
        """Custom loop - just implement run()."""

        name = "my_custom"

        async def run(self, ctx, user_input: str) -> LoopResult:
            """Simple single-shot implementation. ctx is AgentRunContext (build_messages, complete, etc.)."""
            from syrin.types import Message, MessageRole

            messages = [Message(role=MessageRole.USER, content=user_input)]
            response = await ctx.complete(messages)

            return LoopResult(
                content=f"[Custom] {response.content}",
                stop_reason="end_turn",
                iterations=1,
            )

    agent = Agent(
        model=model,
        loop=MyLoop(),  # Pass instance
    )

    response = agent.response("Hello!")
    print("Q: Hello!")
    print(f"A: {response.content}")


if __name__ == "__main__":
    print("=" * 50)
    print("Syrin Loop Strategies")
    print("Model: almock")
    print("=" * 50)

    example_single_shot()
    print()
    example_react()
    print()
    example_human_in_the_loop()
    print()
    example_plan_execute()
    print()
    example_code_action()
    print()
    example_custom_loop()
    print()
    print("✅ Done!")
