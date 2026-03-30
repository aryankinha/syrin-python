"""Agent Discovery with Agent Card Override.

Demonstrates:
- agent_card = AgentCard(...) — Override auto-generated Agent Card fields
- Hook.DISCOVERY_REQUEST — Emitted when /.well-known/agent-card.json is requested

Requires: uv pip install syrin[serve]

Run: python -m examples.serving.discovery_override
Then: curl http://localhost:8000/.well-known/agent-card.json
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
from syrin.enums import Hook
from syrin.serve.discovery import AgentCard, AgentCardAuth, AgentCardProvider

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class CustomDiscoveryAgent(Agent):
    _agent_name = "custom-discovery-agent"
    _agent_description = "Agent with custom Agent Card (provider, auth)"
    model = almock
    system_prompt = "You are a helpful assistant."

    # Override auto-generated Agent Card fields
    agent_card = AgentCard(
        provider=AgentCardProvider(
            organization="MyCompany",
            url="https://mycompany.com",
        ),
        authentication=AgentCardAuth(
            schemes=["oauth2"],
            oauth_url="https://auth.mycompany.com/token",
        ),
    )


if __name__ == "__main__":
    agent = CustomDiscoveryAgent()

    # Log when discovery endpoint is hit
    agent.events.on(
        Hook.DISCOVERY_REQUEST,
        lambda ctx: print(f"  [Discovery] {ctx.agent_name} requested at {ctx.path}"),
    )

    print("Serving at http://localhost:8000")
    print("GET /.well-known/agent-card.json to see custom Agent Card")
    agent.serve(port=8000)
