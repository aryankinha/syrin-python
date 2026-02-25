"""AgentTeam Example.

Demonstrates:
- Creating an AgentTeam with multiple agents
- Shared budget across team members
- Automatic agent selection for tasks

Run: python -m examples.multi_agent.team
"""

from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent, Budget, prompt
from syrin.agent.multi_agent import AgentTeam

logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@prompt
def researcher_prompt(domain: str) -> str:
    return f"You are a researcher specializing in {domain}."


@prompt
def writer_prompt(style: str) -> str:
    return f"You are a writer with a {style} style."


def example_team() -> None:
    """Basic team with shared budget."""
    print("\n" + "=" * 50)
    print("AgentTeam Example")
    print("=" * 50)

    class Researcher(Agent):
        model = almock
        system_prompt = researcher_prompt(domain="technology")

    class Writer(Agent):
        model = almock
        system_prompt = writer_prompt(style="engaging")

    team = AgentTeam(
        agents=[Researcher(), Writer()],
        budget=Budget(run=0.50, shared=True),
    )

    print(f"1. Created team with {len(team.agents)} agents")
    print(f"   Shared budget: ${team.total_budget}")

    print("\n2. Running task with auto-selected agent...")
    result = team.run_task("Research AI trends")
    print(f"   Result: {result.content[:80]}...")
    print(f"   Cost: ${result.cost:.6f}")
    print(f"   Remaining budget: ${team.total_budget - result.cost:.4f}")


def example_team_selection() -> None:
    """Team agent selection."""
    print("\n" + "=" * 50)
    print("Team Agent Selection")
    print("=" * 50)

    class Researcher(Agent):
        model = almock
        system_prompt = researcher_prompt(domain="general")

    class Writer(Agent):
        model = almock
        system_prompt = writer_prompt(style="general")

    team = AgentTeam(agents=[Researcher(), Writer()])

    print("1. Selecting agent for 'research machine learning'...")
    selected = team.select_agent("research machine learning")
    print(f"   Selected: {selected.__class__.__name__}")

    print("\n2. Selecting agent for 'write an article'...")
    selected = team.select_agent("write an article about AI")
    print(f"   Selected: {selected.__class__.__name__}")


if __name__ == "__main__":
    example_team()
    example_team_selection()
