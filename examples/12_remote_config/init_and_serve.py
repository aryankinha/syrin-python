"""Remote config: syrin.init() (optional) + agent with budget, served with config routes.

Run: PYTHONPATH=. python examples/12_remote_config/init_and_serve.py

Then:
  curl -s http://localhost:8000/config | jq .
  curl -s -X PATCH http://localhost:8000/config -H "Content-Type: application/json" \
    -d '{"agent_id":"<agent_id from GET>","version":1,"overrides":[{"path":"budget.max_cost","value":2.0}]}'
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

import syrin
from syrin import Agent, Budget, Model

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Optional: enable cloud so agents register with Syrin Cloud and receive overrides via SSE.
# Without this, agents run with local config only; config routes still work when serving.
if os.getenv("SYRIN_API_KEY"):
    syrin.init()

# Agent with budget so we can override budget.max_cost via PATCH /config
agent = Agent(
    model=Model.Almock(),
    name="my_agent",
    budget=Budget(max_cost=1.0),
    system_prompt="You are a helpful assistant.",
)

if __name__ == "__main__":
    from syrin.serve.config import ServeConfig

    print("Serving at http://localhost:8000")
    print("  GET  /config        — schema + current values")
    print("  PATCH /config       — apply overrides (body: OverridePayload)")
    print("  GET  /config/stream — SSE stream for live updates")
    agent.serve(port=8000, config=ServeConfig(enable_discovery=True))
