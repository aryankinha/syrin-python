"""Dynamic Pipeline — 5+ agents with clear roles and when-to-use instructions.

Demonstrates:
- 5 specialized agents: Researcher, Analyst, Writer, FactChecker, Summarizer
- Orchestrator prompt that says when to use which agent
- DynamicPipeline.run() — LLM plans and spawns agents
- Full observability (run with --trace or attach debugger)

Run from repo root:
  python -m examples.07_multi_agent.dynamic_pipeline_5agents
Visit: http://localhost:8000/playground
Requires: uv pip install syrin[serve]
"""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from dotenv import load_dotenv

from examples.models.models import (
    almock_analyst,
    almock_fact_checker,
    almock_orchestrator,
    almock_researcher,
    almock_summarizer,
    almock_writer,
)
from syrin import Agent, Budget
from syrin.agent.multi_agent import DynamicPipeline
from syrin.enums import Hook

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


# -----------------------------------------------------------------------------
# Agent roles — each has a clear purpose. The orchestrator prompt below
# describes when to use which agent.
# -----------------------------------------------------------------------------


# Use for: finding information, web search, gathering data, investigating topics
class ResearcherAgent(Agent):
    _agent_name = "researcher"
    _agent_description = "Researches topics and gathers information"
    model = almock_researcher
    system_prompt = (
        "You research topics and gather information. Use for: finding facts, "
        "searching for data, investigating questions. Be thorough and cite sources."
    )


# Use for: analyzing data, comparing options, evaluating pros/cons, structured reasoning
class AnalystAgent(Agent):
    _agent_name = "analyst"
    _agent_description = "Analyzes data and provides structured reasoning"
    model = almock_analyst
    system_prompt = (
        "You analyze data and provide structured reasoning. Use for: comparing "
        "options, pros/cons, evaluation, logical breakdown. Be clear and objective."
    )


# Use for: writing content, drafting text, creative writing, formatting
class WriterAgent(Agent):
    _agent_name = "writer"
    _agent_description = "Writes content in clear, engaging style"
    model = almock_writer
    system_prompt = (
        "You write content in a clear, engaging style. Use for: drafting text, "
        "creative writing, formatting, structuring prose. Be concise and readable."
    )


# Use for: fact-checking, verifying claims, validating accuracy
class FactCheckerAgent(Agent):
    _agent_name = "fact_checker"
    _agent_description = "Fact-checks and verifies claims"
    model = almock_fact_checker
    system_prompt = (
        "You fact-check and verify claims. Use for: validating accuracy, "
        "spotting inconsistencies, confirming sources. Be precise and skeptical."
    )


# Use for: summarizing long content, condensing, executive summaries
class SummarizerAgent(Agent):
    _agent_name = "summarizer"
    _agent_description = "Synthesizes and summarizes content"
    model = almock_summarizer
    system_prompt = (
        "You synthesize and summarize content. Use for: executive summaries, "
        "condensing long text, key takeaways. Be accurate and concise."
    )


# The DynamicPipeline orchestrator uses each agent's system_prompt as the description
# shown to the LLM. Each agent above has "Use for: ..." in its prompt so the LLM
# knows when to spawn which agent.


def main() -> None:
    budget = Budget(max_cost=2.0)
    pipeline = DynamicPipeline(
        agents=[
            ResearcherAgent,
            AnalystAgent,
            WriterAgent,
            FactCheckerAgent,
            SummarizerAgent,
        ],
        model=almock_orchestrator,
        budget=budget,
        max_parallel=5,
        debug=True,
    )

    # Optional: attach event handlers for observability
    def on_spawn(ctx: dict) -> None:
        agent = ctx.get("agent_type", "?")
        task = str(ctx.get("task", ""))[:60]
        print(f"  → Spawned {agent}: {task}...")

    pipeline.events.on(Hook.DYNAMIC_PIPELINE_AGENT_SPAWN, on_spawn)

    task = (
        "Compare Python and Rust for building CLI tools. "
        "Have the analyst evaluate pros/cons, then the writer draft a short summary."
    )
    result = pipeline.run(task, mode="parallel")

    print("\n--- Result ---")
    print(result.content[:500] + "..." if len(result.content) > 500 else result.content)
    print(f"\nCost: ${result.cost:.4f}")


if __name__ == "__main__":
    main()
    budget = Budget(max_cost=2.0)
    serve_pipeline = DynamicPipeline(
        agents=[
            ResearcherAgent,
            AnalystAgent,
            WriterAgent,
            FactCheckerAgent,
            SummarizerAgent,
        ],
        model=almock_orchestrator,
        budget=budget,
        max_parallel=5,
        debug=True,
    )
    print("Serving at http://localhost:8000/playground")
    serve_pipeline.serve(port=8000, enable_playground=True, debug=True)
