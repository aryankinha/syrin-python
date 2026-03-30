"""Dynamic Pipeline Debug — Watch LLM-planned agent orchestration.

Demonstrates:
- DynamicPipeline where the LLM plans which agents to run
- Pry watching all pipeline events
- Checkpoints before/after pipeline for inspection
- In the [a] agents tab you see PIPELINE_AGENT_START / COMPLETE events
- In the [d] debug tab you see checkpoints as named stops

Run:
    python examples/21_debug_multiagent/dynamic_pipeline_debug.py --debug
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from examples.models.models import almock_orchestrator, gpt4_mini  # noqa: E402
from syrin import Agent, tool  # noqa: E402
from syrin.agent.multi_agent import DynamicPipeline  # noqa: E402
from syrin.debug import Pry  # noqa: E402

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@tool
def web_search(query: str) -> str:
    """Mock web search for a query."""
    return f"[mock results for '{query}'] Market size $42B, 18% YoY growth, key players: X, Y, Z"


@tool
def fact_check(claim: str) -> str:
    """Mock fact-checking of a claim."""
    return f"[mock fact-check] '{claim[:50]}...' — VERIFIED (high confidence, 3 sources)"


# ---------------------------------------------------------------------------
# Agent types — the LLM orchestrator picks which to spawn
# ---------------------------------------------------------------------------


class ResearcherAgent(Agent):
    _agent_name = "researcher"
    _agent_description = "Researches a topic using web search"
    model = gpt4_mini
    system_prompt = "You research topics. Use web_search to find information."
    tools = [web_search]


class FactCheckerAgent(Agent):
    _agent_name = "fact_checker"
    _agent_description = "Verifies claims and facts"
    model = gpt4_mini
    system_prompt = "You verify facts. Use fact_check to validate each claim."
    tools = [fact_check]


class WriterAgent(Agent):
    _agent_name = "writer"
    _agent_description = "Writes clear summaries from research"
    model = gpt4_mini
    system_prompt = "You write clear, engaging summaries from research data."


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pry = Pry()

    # DynamicPipeline uses almock_orchestrator which returns a valid JSON plan:
    # [{"type":"researcher","task":"..."}, {"type":"fact_checker","task":"..."}]
    pipeline = DynamicPipeline(
        agents=[ResearcherAgent, FactCheckerAgent, WriterAgent],
        model=almock_orchestrator,
        max_parallel=2,
    )

    # Attach UI to the pipeline (registers hooks on all internal agents)
    pry.attach(pipeline)

    def _run() -> None:
        # ── Checkpoint before pipeline ───────────────────────────────────────
        # The LLM orchestrator hasn't run yet. In the TUI:
        #   [a] agents tab is empty — no agents have been spawned
        #   [d] debug tab shows this checkpoint
        pry.debugpoint("before pipeline — LLM will plan which agents to spawn")

        # Run the pipeline — the orchestrator LLM decides which agents to run
        # and in which order. Watch the [a] tab to see each agent spawn.
        result = pipeline.run(
            "Research and write a briefing on quantum computing applications in finance.",
            mode="sequential",
        )

        # ── Checkpoint after pipeline ────────────────────────────────────────
        # In the TUI:
        #   [a] shows PIPELINE_AGENT_START / COMPLETE for each spawned agent
        #   [t] shows web_search and fact_check tool calls
        #   [e] detail of the final result event
        pry.debugpoint(f"pipeline done — cost ${result.cost:.4f}")

    with pry:
        t = pry.run(_run)
        t.join()
        pry.wait()
