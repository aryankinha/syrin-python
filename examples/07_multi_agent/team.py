"""Swarm Example — Multi-agent coordination with shared budget.

Demonstrates:
- Creating a Swarm with multiple specialized agents
- Shared budget across swarm members
- Running a task via swarm.run()

Run: python examples/07_multi_agent/team.py
"""

from __future__ import annotations

import asyncio

from syrin import Agent, Budget, Model, prompt
from syrin.enums import SwarmTopology
from syrin.swarm import Swarm, SwarmConfig

model = Model.mock()


@prompt
def researcher_prompt(domain: str) -> str:
    return f"You are a researcher specializing in {domain}."


@prompt
def writer_prompt(style: str) -> str:
    return f"You are a writer with a {style} style."


class Researcher(Agent):
    name = "researcher"
    description = "Researches topics (technology)"
    model = Model.mock()
    system_prompt = researcher_prompt(domain="technology")


class Writer(Agent):
    name = "writer"
    description = "Writes content in engaging style"
    model = Model.mock()
    system_prompt = writer_prompt(style="engaging")


async def main() -> None:
    # Swarm with shared budget — run routes to the best agent
    print("=== Swarm with shared budget ===\n")
    swarm = Swarm(
        agents=[Researcher, Writer],
        config=SwarmConfig(
            topology=SwarmTopology.CONSENSUS,
            budget=Budget(
                max_cost=0.50,
            ),
        ),
    )
    result = await swarm.run("Research AI trends")
    print(f"Result: {result.content[:80]}...")
    print(f"Cost: ${result.cost:.6f}\n")


if __name__ == "__main__":
    asyncio.run(main())
