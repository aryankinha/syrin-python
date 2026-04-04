"""Playground Serving Example.

Demonstrates:
- agent.serve(enable_playground=True, debug=True)
- Visit http://localhost:8000/playground for chat UI, cost, budget, observability

Requires: uv pip install syrin[serve]

Run: python -m examples.16_serving.playground_serve
Visit: http://localhost:8000/playground
"""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from dotenv import load_dotenv

from examples.models.models import gpt4_mini
from syrin import Agent, Budget, Context, Memory, MemoryBackend, RateLimit

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Assistant(Agent):
    name = "assistant"
    description = "Helpful assistant — playground demo"
    model = gpt4_mini
    system_prompt = "You are a helpful assistant. Be concise."
    budget = Budget(max_cost=0.5, rate_limits=RateLimit(hour=10, day=100, week=700))
    memory = Memory(backend=MemoryBackend.MEMORY, top_k=10)
    context = Context(max_tokens=1000)


if __name__ == "__main__":
    agent = Assistant()
    # enable_playground=True: serves GET /playground
    # debug=True: observability panel shows hook events
    agent.serve(port=8000, enable_playground=True, debug=True)
