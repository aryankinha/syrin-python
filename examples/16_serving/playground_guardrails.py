"""Playground: Agent with Guardrails Example.

Demonstrates:
- Agent with ContentFilter guardrail
- Blocked words: spam, scam
- Visit http://localhost:8000/playground — try messages with/without blocked words

Run: python -m examples.serving.playground_guardrails
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
from syrin.guardrails import ContentFilter, GuardrailChain

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


chain = GuardrailChain(
    [
        ContentFilter(blocked_words=["spam", "scam"], name="NoSpam"),
    ]
)


class GuardedAssistant(Agent):
    name = "guarded"
    description = "Assistant with content filter (blocks spam, scam)"
    model = almock
    system_prompt = "You are a helpful assistant."
    guardrails = chain


if __name__ == "__main__":
    agent = GuardedAssistant()
    agent.serve(port=8000, enable_playground=True, debug=True)
