"""Parallel swarms — run independent agents simultaneously on a shared goal.

When agents do not depend on each other's output, running them sequentially
wastes time. A parallel swarm dispatches all agents at once, merges their
responses, and completes in the time of the slowest agent — not the sum.

Use this topology for:
  - Market intelligence: research, competitive analysis, and executive summary
    each contribute to the same goal independently.
  - Content review pipelines: SEO, legal, and brand-voice checks run concurrently.
  - Any scenario where agents are independent and all outputs are valuable.

Requires:
    OPENAI_API_KEY — set in your environment before running.

Run:
    OPENAI_API_KEY=sk-... uv run python examples/07_multi_agent/swarm_parallel.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from syrin import Agent, Budget, Model
from syrin.enums import FallbackStrategy, Hook
from syrin.swarm import Swarm, SwarmConfig

if not os.environ.get("OPENAI_API_KEY"):
    print("Error: OPENAI_API_KEY is not set. This example requires a real API key.")
    sys.exit(1)

_MODEL = Model.OpenAI("gpt-4o-mini")


# ── Agent definitions ─────────────────────────────────────────────────────────
#
# Three specialist agents with distinct, narrow mandates. Each receives the
# same goal string from the swarm and contributes a focused perspective.
# No arun override — the real LLM does the work.


class MarketResearchAgent(Agent):
    """Produces a structured market-size and growth analysis."""

    model = _MODEL
    system_prompt = (
        "You are a senior market research analyst. "
        "Given a market domain, write a focused 3-5 sentence analysis covering: "
        "current market size (with year), year-over-year growth rate, primary growth "
        "drivers, and the two or three dominant players. Be specific. Use numbers."
    )


class CompetitiveIntelligenceAgent(Agent):
    """Surfaces competitive dynamics, pricing pressure, and disruptive threats."""

    model = _MODEL
    system_prompt = (
        "You are a competitive intelligence specialist in technology markets. "
        "Given a market domain, write a focused 3-5 sentence analysis covering: "
        "competitive concentration, pricing pressure, the leading differentiation "
        "strategies in the market, and one credible disruptive threat. Be precise."
    )


class ExecutiveBriefAgent(Agent):
    """Distils the opportunity into a direct C-suite recommendation."""

    model = _MODEL
    system_prompt = (
        "You are a management consultant who writes C-suite executive briefs. "
        "Given a market domain, write a 2-3 sentence brief that states the primary "
        "opportunity, the most important risk, and a clear action recommendation. "
        "Write for board-level readers: direct, confident, no filler phrases."
    )


# ── Example 1: Basic parallel swarm ──────────────────────────────────────────
#
# Three agents receive the same goal and run concurrently. The result combines
# all three outputs into a single SwarmResult.


async def example_basic_parallel() -> None:
    print("\n── Example 1: Basic parallel swarm ──────────────────────────────")

    swarm = Swarm(
        agents=[
            MarketResearchAgent(),
            CompetitiveIntelligenceAgent(),
            ExecutiveBriefAgent(),
        ],
        goal="AI developer tooling market — 2025 outlook",
    )
    result = await swarm.run()

    print(result.content)
    print("\nCost breakdown:")
    for agent_name, cost in result.cost_breakdown.items():
        print(f"  {agent_name}: ${cost:.4f}")


# ── Example 2: Shared budget pool ─────────────────────────────────────────────
#
# Passing a Budget to a Swarm enables automatic sharing — all agents draw from
# the same pool. The swarm enforces the total limit and budget_report records
# every cent.


async def example_shared_budget() -> None:
    print("\n── Example 2: Shared budget pool with per-agent cap ─────────────")

    budget = Budget(max_cost=0.10)
    swarm = Swarm(
        agents=[
            MarketResearchAgent(),
            CompetitiveIntelligenceAgent(),
            ExecutiveBriefAgent(),
        ],
        goal="Healthcare AI — competitive landscape 2025",
        budget=budget,
    )
    result = await swarm.run()

    if result.budget_report:
        print(f"Total spent: ${result.budget_report.total_spent:.4f}")
        for entry in result.budget_report.per_agent:
            print(f"  {entry.agent_name}: ${entry.spent:.4f}")


# ── Example 3: Swarm lifecycle hooks ─────────────────────────────────────────
#
# Hooks give a real-time view of the swarm's execution — useful for logging,
# dashboards, alerting, and audit trails. Every lifecycle event carries the
# full context: agent name, cost, goal, and topology.


async def example_lifecycle_hooks() -> None:
    print("\n── Example 3: Lifecycle hooks ───────────────────────────────────")

    swarm = Swarm(
        agents=[MarketResearchAgent(), CompetitiveIntelligenceAgent()],
        goal="Renewable energy storage — investment signals 2025",
    )

    events: list[str] = []
    swarm.events.on(Hook.SWARM_STARTED, lambda _ctx: events.append("SWARM_STARTED"))
    swarm.events.on(
        Hook.AGENT_JOINED_SWARM,
        lambda ctx: events.append(f"JOINED:  {ctx.get('agent_name')}"),
    )
    swarm.events.on(
        Hook.AGENT_LEFT_SWARM,
        lambda ctx: events.append(f"LEFT:    {ctx.get('agent_name')} (${ctx.get('cost', 0):.4f})"),
    )
    swarm.events.on(Hook.SWARM_ENDED, lambda _ctx: events.append("SWARM_ENDED"))

    await swarm.run()
    for event in events:
        print(f"  {event}")


# ── Example 4: Graceful degradation — SKIP_AND_CONTINUE ──────────────────────
#
# In production, individual agents can fail — network timeouts, rate limits,
# model outages. SKIP_AND_CONTINUE collects results from all agents that
# succeeded and returns a partial result instead of aborting the entire run.
# The partial_results list lets callers distinguish complete from partial runs.


async def example_graceful_degradation() -> None:
    print("\n── Example 4: Graceful degradation (SKIP_AND_CONTINUE) ─────────")

    class ExternalDataAgent(Agent):
        """Calls a third-party data provider that is currently unreachable."""

        model = _MODEL
        system_prompt = "You fetch live pricing data from an external market feed."

        async def arun(self, input_text: str) -> None:  # type: ignore[override]
            # Simulates a real-world connection timeout from the external provider
            raise RuntimeError("503 Service Unavailable: market data feed is down")

    swarm = Swarm(
        agents=[MarketResearchAgent(), ExternalDataAgent()],
        goal="Fintech payments — live market snapshot",
        config=SwarmConfig(on_agent_failure=FallbackStrategy.SKIP_AND_CONTINUE),
    )
    result = await swarm.run()

    print(f"  Succeeded agents: {len(result.agent_results)}")
    print(f"  Partial results:  {len(result.partial_results)}")
    print(f"  Content snippet:  {result.content[:120]}...")


# ── Main ──────────────────────────────────────────────────────────────────────


async def main() -> None:
    await example_basic_parallel()
    await example_shared_budget()
    await example_lifecycle_hooks()
    await example_graceful_degradation()
    print("\nAll parallel swarm examples completed.")


if __name__ == "__main__":
    asyncio.run(main())
