"""Workflow — run multiple agents in sequence, passing output forward.

Demonstrates:
- Workflow() for sequential multi-agent execution
- @prompt for per-agent dynamic system prompts
- Workflow result with content and cost

Run:
    python examples/07_multi_agent/pipeline.py
"""

from __future__ import annotations

import asyncio

from syrin import Agent, Model, prompt
from syrin.workflow import Workflow

model = Model.mock()


@prompt
def researcher_prompt(domain: str) -> str:
    return f"You are a researcher specializing in {domain}."


@prompt
def writer_prompt(style: str) -> str:
    return f"You are a writer with a {style} style."


class Researcher(Agent):
    name = "researcher"
    description = "Researches topics and gathers information"
    model = model
    system_prompt = researcher_prompt(domain="technology")


class Writer(Agent):
    name = "writer"
    description = "Writes content in professional style"
    model = model
    system_prompt = writer_prompt(style="professional")


async def main() -> None:
    print("-- Workflow: Researcher -> Writer --")

    wf = (
        Workflow("research-pipeline")
        .step(Researcher, task="Find information about renewable energy")
        .step(Writer, task="Write about renewable energy")
    )
    result = await wf.run("renewable energy")

    print(f"  Result: {result.content[:100]}...")
    print(f"  Cost:   ${result.cost:.6f}")


if __name__ == "__main__":
    asyncio.run(main())
