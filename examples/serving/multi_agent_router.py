"""Multi-Agent HTTP Router Example.

Demonstrates:
- AgentRouter(agents=[...]) — multiple agents on one server
- Routes: /agent/{name}/chat, /agent/{name}/health, etc.
- Mount on existing FastAPI app

Requires: uv pip install syrin[serve]

Run: python -m examples.serving.multi_agent_router
"""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent
from syrin.serve import AgentRouter

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Researcher(Agent):
    name = "researcher"
    description = "Researches topics and summarizes findings"
    model = almock
    system_prompt = "You are a researcher. Be thorough but concise."


class Writer(Agent):
    name = "writer"
    description = "Writes content in a professional style"
    model = almock
    system_prompt = "You are a writer. Be clear and engaging."


if __name__ == "__main__":
    router = AgentRouter(agents=[Researcher(), Writer()])
    # Run on port 8000
    # Visit /agent/researcher/health, /agent/writer/chat, etc.
    router.serve(port=8000)
