"""Parallel Spawn Debug — Observe agents spawned in parallel.

Demonstrates:
- spawn_parallel() launching 3 sub-agents simultaneously
- Pry attached to the parent + all spawned children
- Checkpoints before and after parallel spawn
- In the [a] agents tab you see SPAWN_START events with child_agent/source_agent
- In the [t] tools tab you see tool calls across all parallel agents
- In the [r] errors tab you see any failures clearly

Run:
    python examples/21_debug_multiagent/parallel_spawn_debug.py          # without TUI (JSON)
    python examples/21_debug_multiagent/parallel_spawn_debug.py --debug # with TUI
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from examples.models.models import gpt4_mini  # noqa: E402
from syrin import Agent, tool  # noqa: E402
from syrin.debug import Pry  # noqa: E402

_PRY = Pry.from_debug_flag()
_DEBUG = _PRY is not None

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@tool
def fetch_market_data(sector: str) -> str:
    """Fetch market data for a given sector (mock)."""
    return f"[mock] {sector}: revenue +12%, growth rate 8%, key players: Alpha, Beta, Gamma"


@tool
def analyze_risks(data: str) -> str:
    """Identify key risks from market data."""
    return f"Risks identified in: {data[:60]}... — regulatory, competition, supply chain"


# ---------------------------------------------------------------------------
# Agent types for parallel spawn
# ---------------------------------------------------------------------------


class TechAnalyst(Agent):
    name = "tech_analyst"
    description = "Analyzes technology sector"
    model = gpt4_mini
    system_prompt = "Analyze the technology sector."
    tools = [fetch_market_data, analyze_risks]


class FinanceAnalyst(Agent):
    name = "finance_analyst"
    description = "Analyzes financial markets"
    model = gpt4_mini
    system_prompt = "Analyze the financial sector."
    tools = [fetch_market_data]


class HealthAnalyst(Agent):
    name = "health_analyst"
    description = "Analyzes healthcare sector"
    model = gpt4_mini
    system_prompt = "Analyze the healthcare sector."
    tools = [fetch_market_data, analyze_risks]


class OrchestratorAgent(Agent):
    name = "orchestrator"
    description = "Spawns sector analysts in parallel and synthesizes results"
    model = gpt4_mini
    system_prompt = "You orchestrate sector analysis. Spawn analysts and synthesize their reports."


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    orchestrator = OrchestratorAgent()

    def _run(pry_instance: Pry | None = None) -> None:
        # Warm-up run so the agents tab has a run record
        orchestrator.run("Preparing sector analysis across 3 verticals...")

        if pry_instance is not None:
            # ── Checkpoint before spawn ──────────────────────────────────────────
            # In the TUI: [a] shows the completed run
            # Press [p] to continue to the parallel spawn
            pry_instance.debugpoint("before parallel spawn — 3 agents will launch simultaneously")

        # Spawn 3 agents in parallel.  Each fires SPAWN_START with:
        #   child_agent, source_agent, input_preview
        # All three run concurrently; the orchestrator blocks until all finish.
        results = orchestrator.spawn_parallel(
            [
                (TechAnalyst, "Analyze the AI/tech sector trends for Q4"),
                (FinanceAnalyst, "Analyze fintech and payments market outlook"),
                (HealthAnalyst, "Analyze digital health and biotech sector"),
            ]
        )

        if pry_instance is not None:
            # ── Checkpoint after all parallel agents complete ────────────────────
            # In the TUI: [a] shows 3 SPAWN_START + SPAWN_END events
            # [t] shows tool calls from all 3 agents
            pry_instance.debugpoint("parallel spawn complete — all 3 agents finished")

        # Final synthesis
        combined = "\n\n".join(r.content or "" for r in results)
        orchestrator.run(
            f"Synthesize these sector reports into an executive summary:\n{combined[:600]}"
        )

    if _DEBUG:
        pry = _PRY or Pry()
        pry.attach(orchestrator)

        with pry:
            t = pry.run(_run, pry)
            t.join()
            pry.wait()
    else:
        _run()
