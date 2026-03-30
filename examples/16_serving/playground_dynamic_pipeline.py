"""Playground: Dynamic Pipeline — 5+ agents with observability.

Demonstrates:
- DynamicPipeline served directly (no wrapper agent needed)
- 5 specialized agents: Researcher, Analyst, Writer, FactChecker, Summarizer
- Almock custom replies so orchestrator returns valid JSON plan and agents spawn
- Full observability: hooks emitted to playground trace sidebar
- Visit http://localhost:8000/playground

Run: python -m examples.16_serving.playground_dynamic_pipeline
"""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from dotenv import load_dotenv

from examples.models.models import gpt4_mini
from syrin import Agent, Budget
from syrin.agent.multi_agent import DynamicPipeline
from syrin.enums import ServeProtocol

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


# -----------------------------------------------------------------------------
# 5 specialized agents — each uses Almock with custom reply for demo
# -----------------------------------------------------------------------------


class ResearcherAgent(Agent):
    _agent_name = "researcher"
    model = gpt4_mini
    system_prompt = (
        "You research topics and gather information. Use for: finding facts, "
        "searching for data, investigating questions. Be thorough and cite sources."
    )


class AnalystAgent(Agent):
    _agent_name = "analyst"
    model = gpt4_mini
    system_prompt = (
        "You analyze data and provide structured reasoning. Use for: comparing "
        "options, pros/cons, evaluation, logical breakdown. Be clear and objective."
    )


class WriterAgent(Agent):
    _agent_name = "writer"
    model = gpt4_mini
    system_prompt = (
        "You write content in a clear, engaging style. Use for: drafting text, "
        "creative writing, formatting, structuring prose. Be concise and readable."
    )


class FactCheckerAgent(Agent):
    _agent_name = "fact_checker"
    model = gpt4_mini
    system_prompt = (
        "You fact-check and verify claims. Use for: validating accuracy, "
        "spotting inconsistencies, confirming sources. Be precise and skeptical."
    )


class SummarizerAgent(Agent):
    _agent_name = "summarizer"
    model = gpt4_mini
    system_prompt = (
        "You synthesize and summarize content. Use for: executive summaries, "
        "condensing long text, key takeaways. Be accurate and concise."
    )


# -----------------------------------------------------------------------------
# Serve — pipeline.serve() directly (no wrapper agent needed)
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    budget = Budget(max_cost=2.0)
    pipeline = DynamicPipeline(
        agents=[
            ResearcherAgent,
            AnalystAgent,
            WriterAgent,
            FactCheckerAgent,
            SummarizerAgent,
        ],
        model=gpt4_mini,
        budget=budget,
        max_parallel=5,
        debug=True,
    )
    pipeline.serve(protocol=ServeProtocol.CLI, enable_playground=True, debug=True)
