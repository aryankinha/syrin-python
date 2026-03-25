"""Tracing Example — Debug mode and manual spans.

Demonstrates:
- Agent(debug=True) for automatic tracing
- Manual span creation with syrin.observability
- Console output for trace visibility

Run: python -m examples.10_observability.tracing
Visit: http://localhost:8000/playground
Requires: uv pip install syrin[serve]
"""

from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class TracingAgent(Agent):
    _agent_name = "tracing-agent"
    _agent_description = "Agent with debug tracing enabled"
    model = almock
    system_prompt = "You are helpful."
    debug = True


if __name__ == "__main__":
    agent = TracingAgent()
    result = agent.run("What is AI?")
    print(f"Response: {result.content[:80]}...")
    print("Serving at http://localhost:8000/playground")
    agent.serve(port=8000, enable_playground=True, debug=True)
