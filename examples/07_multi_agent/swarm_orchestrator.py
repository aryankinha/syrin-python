"""Swarm ORCHESTRATOR topology — LLM-driven task delegation.

In the ORCHESTRATOR topology a designated orchestrator agent analyses the
shared goal, decides which workers to call, sequences their execution, and
synthesises their outputs into a final answer.  Unlike a fixed workflow, the
delegation logic lives in the LLM — the orchestrator can adapt based on the
goal, the workers available, and intermediate results.

Use this topology when:
  - The decomposition strategy should be dynamic, not hard-coded.
  - Different goals require different subsets of workers.
  - You want the LLM to reason about which specialist is best suited to each sub-task.

Convention:
  - The first agent in the list is treated as the orchestrator.
  - Subsequent agents are workers; the orchestrator references them by role.

Requires:
    OPENAI_API_KEY — set in your environment before running.

Run:
    OPENAI_API_KEY=sk-... uv run python examples/07_multi_agent/swarm_orchestrator.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from syrin import Agent, Budget, Model
from syrin.enums import Hook, SwarmTopology
from syrin.swarm import Swarm, SwarmConfig

if not os.environ.get("OPENAI_API_KEY"):
    print("Error: OPENAI_API_KEY is not set. This example requires a real API key.")
    sys.exit(1)

_MODEL = Model.OpenAI("gpt-4o-mini")


# ── Agent definitions ─────────────────────────────────────────────────────────
#
# Orchestrator first, then workers. The orchestrator's system prompt should
# describe the workers and explain the delegation protocol clearly.


class ResearchOrchestratorAgent(Agent):
    """Coordinates a research team: delegates sub-tasks and synthesises findings."""

    model = _MODEL
    system_prompt = (
        "You are a senior research director coordinating a specialist team. "
        "Your team consists of:\n"
        "  - MarketDataAgent: retrieves quantitative market metrics (size, growth, share).\n"
        "  - CompetitivePositioningAgent: analyses competitive dynamics and moats.\n"
        "  - StrategicAdvisoryAgent: translates findings into executive recommendations.\n\n"
        "When given a research goal:\n"
        "1. Identify which sub-tasks each specialist should handle.\n"
        "2. Synthesise the outputs into a structured research briefing with three sections: "
        "   Market Overview, Competitive Landscape, and Strategic Recommendation.\n"
        "3. Be concise and specific — board-level readers have no time for filler."
    )


class MarketDataAgent(Agent):
    """Retrieves quantitative market metrics: size, CAGR, and share breakdown."""

    model = _MODEL
    system_prompt = (
        "You are a quantitative market analyst. "
        "For any market domain provided, deliver a tight 3-4 sentence data summary: "
        "total addressable market size (current year), compound annual growth rate, "
        "revenue share held by the top three players, and one key demand driver. "
        "Cite specific numbers. No vague qualifications."
    )


class CompetitivePositioningAgent(Agent):
    """Maps the competitive landscape: moats, pricing dynamics, and emerging threats."""

    model = _MODEL
    system_prompt = (
        "You are a competitive strategy analyst specialising in technology markets. "
        "For any market domain, write a 3-4 sentence analysis of: the primary source "
        "of competitive advantage held by market leaders, current pricing pressure "
        "(race to zero vs. premium consolidation), and the single most credible "
        "disruptive threat in the next 12 months. Be specific."
    )


class StrategicAdvisoryAgent(Agent):
    """Converts market and competitive intelligence into a crisp investment verdict."""

    model = _MODEL
    system_prompt = (
        "You are a managing director at a strategy consultancy. "
        "Given a market domain, write a 2-3 sentence investment verdict: "
        "state the primary opportunity window (with a timeline), the non-negotiable "
        "risk factor, and a clear recommendation (invest now / wait / avoid). "
        "Write for a board audience. No hedging language."
    )


# ── Example 1: Orchestrator-directed research briefing ───────────────────────
#
# The orchestrator receives the goal, reasons about sub-task allocation, and
# produces a synthesised briefing. All agents run in the swarm; the orchestrator
# controls the narrative arc.


async def example_orchestrator_research() -> None:
    print("\n── Example 1: Orchestrator-directed research briefing ───────────")

    swarm = Swarm(
        agents=[
            ResearchOrchestratorAgent(),
            MarketDataAgent(),
            CompetitivePositioningAgent(),
            StrategicAdvisoryAgent(),
        ],
        goal="Generative AI infrastructure market — investment thesis 2025",
        config=SwarmConfig(topology=SwarmTopology.ORCHESTRATOR),
    )
    result = await swarm.run()

    print(result.content)
    print("\nCost breakdown:")
    for agent_name, cost in result.cost_breakdown.items():
        print(f"  {agent_name}: ${cost:.4f}")


# ── Example 2: Budget-controlled orchestration ────────────────────────────────
#
# Attach a shared budget so the orchestrator cannot commission more work than
# the allocated pool allows. The swarm halts if the pool is exhausted before
# all workers complete.


async def example_with_budget() -> None:
    print("\n── Example 2: Budget-controlled orchestration ───────────────────")

    swarm = Swarm(
        agents=[
            ResearchOrchestratorAgent(),
            MarketDataAgent(),
            StrategicAdvisoryAgent(),
        ],
        goal="Quantum computing — commercial readiness horizon 2025-2030",
        config=SwarmConfig(topology=SwarmTopology.ORCHESTRATOR),
        budget=Budget(
            max_cost=0.10,
        ),
    )
    result = await swarm.run()

    if result.budget_report:
        print(f"Total spent: ${result.budget_report.total_spent:.4f}")
        for entry in result.budget_report.per_agent:
            print(f"  {entry.agent_name}: ${entry.spent:.4f}")
    print(f"\nSummary:\n{result.content}")


# ── Example 3: Monitoring orchestrator lifecycle ──────────────────────────────
#
# Hooks surface every delegation decision in real time — useful for audit logs,
# dashboards, and tracing which workers the orchestrator chose to invoke.


async def example_orchestrator_hooks() -> None:
    print("\n── Example 3: Orchestrator lifecycle hooks ──────────────────────")

    swarm = Swarm(
        agents=[
            ResearchOrchestratorAgent(),
            MarketDataAgent(),
            CompetitivePositioningAgent(),
        ],
        goal="Edge AI chips — supply chain and market outlook 2025",
        config=SwarmConfig(topology=SwarmTopology.ORCHESTRATOR),
    )

    events: list[str] = []
    swarm.events.on(Hook.SWARM_STARTED, lambda _ctx: events.append("SWARM_STARTED"))
    swarm.events.on(
        Hook.AGENT_JOINED_SWARM,
        lambda ctx: events.append(f"DELEGATED TO: {ctx.get('agent_name')}"),
    )
    swarm.events.on(Hook.SWARM_ENDED, lambda _ctx: events.append("SWARM_ENDED"))

    await swarm.run()
    for event in events:
        print(f"  {event}")


# ── Main ──────────────────────────────────────────────────────────────────────


async def main() -> None:
    await example_orchestrator_research()
    await example_with_budget()
    await example_orchestrator_hooks()
    print("\nAll orchestrator swarm examples completed.")


if __name__ == "__main__":
    asyncio.run(main())
