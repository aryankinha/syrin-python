"""CLI Example.

Demonstrates:
- Interactive REPL with an agent
- CLI commands (/quit, /cost, /trace, /clear, /switch)
- Customizing CLI tags and styles
- Running CLI from code

Run: python -m examples.advanced.cli
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from syrin import CLI, Agent, Model

logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MODEL_ID = os.getenv("OPENAI_MODEL_NAME", "openai/gpt-4o-mini")


def example_basic_cli() -> None:
    """Basic CLI structure."""
    print("\n" + "=" * 50)
    print("Basic CLI Example")
    print("=" * 50)

    cli = CLI()
    print(f"CLI user_tag: {cli.user_tag}")
    print(f"CLI agent_tag: {cli.agent_tag}")
    print(f"CLI style: {cli.style}")


def example_custom_tags() -> None:
    """Customizing CLI tags."""
    print("\n" + "=" * 50)
    print("Custom Tags Example")
    print("=" * 50)

    cli = CLI(
        user_tag="User>",
        agent_tag="Assistant:",
    )

    print(f"User tag: {cli.user_tag}")
    print(f"Agent tag: {cli.agent_tag}")

    # Test formatting
    formatted = cli._format_agent_output("Hello, how can I help?", "Assistant")
    print(f"Formatted: {formatted}")


def example_callable_agent_tag() -> None:
    """Using callable for agent tag."""
    print("\n" + "=" * 50)
    print("Callable Agent Tag")
    print("=" * 50)

    def style_output(text: str) -> str:
        return f"\033[92m🤖 {text}\033[0m"

    cli = CLI(agent_tag=style_output)
    formatted = cli._format_agent_output("Hello!", "Bot")
    print(formatted)


def example_cli_commands() -> None:
    """Demonstrating CLI commands."""
    print("\n" + "=" * 50)
    print("CLI Commands")
    print("=" * 50)

    print("Available commands:")
    print("  /quit           - Exit the CLI")
    print("  /cost           - Show budget summary")
    print("  /trace          - Show last response trace")
    print("  /clear          - Clear agent memory")
    print("  /switch <model> - Switch to a different model")


def example_cli_with_agent() -> None:
    """Connecting CLI to an agent (simulated)."""
    print("\n" + "=" * 50)
    print("CLI with Agent")
    print("=" * 50)

    class DemoAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a helpful assistant."

    agent = DemoAgent()

    cli = CLI(user_tag="You")

    # Simulate a conversation
    print("Simulating conversation...\n")

    # Mock the input to test
    inputs = iter(["Hello", "/quit"])

    def mock_input(prompt):
        try:
            return next(inputs)
        except StopIteration as err:
            raise EOFError() from err

    try:
        cli.serve(agent)
    except Exception as e:
        print(f"Note: {e}")


def example_cli_style() -> None:
    """Customizing CLI style."""
    print("\n" + "=" * 50)
    print("CLI Style Example")
    print("=" * 50)

    style = {
        "user_color": "cyan",
        "agent_color": "green",
        "error_color": "red",
        "show_timestamps": True,
    }

    cli = CLI(style=style)
    print(f"Style config: {cli.style}")


def example_cli_commands_simulation() -> None:
    """Simulating CLI command handling."""
    print("\n" + "=" * 50)
    print("CLI Command Simulation")
    print("=" * 50)

    CLI()

    class BudgetAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a helpful assistant."

        @property
        def budget_summary(self):
            return {"current_run_cost": 0.05, "limit": 0.10}

    agent = BudgetAgent()

    # Simulate /cost command
    line = "/cost"
    parts = line.split(maxsplit=1)
    cmd = parts[0].lower()

    if cmd == "/cost":
        summary = getattr(agent, "budget_summary", None)
        if summary:
            print(f"Command: {cmd} -> Budget: {summary}")
        else:
            print(f"Command: {cmd} -> No budget")


def example_multi_agent_cli() -> None:
    """Using CLI with multiple agents."""
    print("\n" + "=" * 50)
    print("Multi-Agent CLI")
    print("=" * 50)

    class ResearchAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a research assistant."

    class ChatAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a friendly chat assistant."

    # You can switch between agents
    print("Agent classes available:")
    print("  - ResearchAgent: For research queries")
    print("  - ChatAgent: For casual conversation")
    print("\nUse /switch command in CLI to change agents")


if __name__ == "__main__":
    example_basic_cli()
    example_custom_tags()
    example_callable_agent_tag()
    example_cli_commands()
    example_cli_style()
    example_cli_commands_simulation()
    example_multi_agent_cli()
