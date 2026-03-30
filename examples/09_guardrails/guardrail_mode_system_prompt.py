"""GuardrailMode.SYSTEM_PROMPT — inject instruction instead of extra LLM call.

Demonstrates:
- GuardrailMode.EVALUATE (default): calls evaluate() as a separate LLM check
- GuardrailMode.SYSTEM_PROMPT: injects system_prompt_instruction() into the
  agent's system prompt — saves 1 LLM call per request, less reliable
- When to use each:
  - EVALUATE: content moderation, PII detection, correctness checks
  - SYSTEM_PROMPT: tone enforcement, format instructions, behavioral rules

Run:
    python examples/09_guardrails/guardrail_mode_system_prompt.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from examples.models.models import almock, gpt4_mini  # noqa: E402
from syrin import Agent  # noqa: E402
from syrin.enums import GuardrailMode  # noqa: E402
from syrin.guardrails import Guardrail  # noqa: E402
from syrin.guardrails.context import GuardrailContext  # noqa: E402
from syrin.guardrails.decision import GuardrailDecision  # noqa: E402

# ---------------------------------------------------------------------------
# EVALUATE mode: runs evaluate() for each request — deterministic, testable
# ---------------------------------------------------------------------------


class ProfanityFilter(Guardrail):
    """Block profanity in user input (EVALUATE mode — default)."""

    def __init__(self) -> None:
        super().__init__(name="profanity_filter", mode=GuardrailMode.EVALUATE)

    async def evaluate(self, ctx: GuardrailContext) -> GuardrailDecision:
        blocked_words = ["badword", "offensive"]
        text = (ctx.text or "").lower()
        for word in blocked_words:
            if word in text:
                return GuardrailDecision(
                    passed=False,
                    reason=f"Profanity detected: '{word}'",
                )
        return GuardrailDecision(passed=True)


# ---------------------------------------------------------------------------
# SYSTEM_PROMPT mode: injects instruction — no extra LLM call
# ---------------------------------------------------------------------------


class FormalToneGuardrail(Guardrail):
    """Enforce formal tone via system prompt injection (SYSTEM_PROMPT mode).

    This does NOT call evaluate() on each request. Instead, it appends
    system_prompt_instruction() to the agent's system prompt at startup.
    One fewer LLM call, but less reliable (model may drift from instruction).
    Best for: tone, format, style — not content safety.
    """

    def __init__(self) -> None:
        super().__init__(name="formal_tone", mode=GuardrailMode.SYSTEM_PROMPT)

    def system_prompt_instruction(self) -> str:
        """Return instruction to inject into agent's system prompt."""
        return (
            "Always respond in a formal, professional tone. "
            "Avoid contractions, slang, and casual language. "
            "Use complete sentences."
        )

    async def evaluate(self, ctx: GuardrailContext) -> GuardrailDecision:
        # Not called when mode=SYSTEM_PROMPT
        return GuardrailDecision(passed=True)


class BriefResponseGuardrail(Guardrail):
    """Enforce brief responses via system prompt (SYSTEM_PROMPT mode)."""

    def __init__(self) -> None:
        super().__init__(name="brief_response", mode=GuardrailMode.SYSTEM_PROMPT)

    def system_prompt_instruction(self) -> str:
        return "Keep all responses under 3 sentences. Be concise."

    async def evaluate(self, ctx: GuardrailContext) -> GuardrailDecision:
        return GuardrailDecision(passed=True)


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


class AgentWithEvaluate(Agent):
    """Uses EVALUATE mode — separate LLM call checks each input."""

    model = gpt4_mini
    system_prompt = "You are a helpful assistant."
    guardrails = [ProfanityFilter()]
    debug = True


class AgentWithSystemPrompt(Agent):
    """Uses SYSTEM_PROMPT mode — no extra LLM call, instruction injected."""

    model = gpt4_mini
    system_prompt = "You are a helpful assistant."
    guardrails = [FormalToneGuardrail(), BriefResponseGuardrail()]
    debug = True


def main() -> None:
    print("=" * 60)
    print("GuardrailMode.EVALUATE — separate evaluation call")
    print("=" * 60)
    agent_eval = AgentWithEvaluate()

    # Clean input — passes
    r1 = agent_eval.run("What is the capital of France?")
    print(f"Clean input  → {r1.content[:100]}")
    print(
        f"Guardrails:    blocked={r1.report.guardrail.blocked}, passed={r1.report.guardrail.input_passed}"
    )

    # Blocked input
    r2 = agent_eval.run("Tell me a badword joke")
    if r2.report.guardrail.blocked:
        print(f"Blocked input → BLOCKED: {r2.report.guardrail.input_reason}")
    else:
        print(f"Blocked input → {r2.content[:60]}")

    print()
    print("=" * 60)
    print("GuardrailMode.SYSTEM_PROMPT — instruction in system prompt")
    print("=" * 60)
    agent_sp = AgentWithSystemPrompt()

    r3 = agent_sp.run("hey what's up?")
    print(f"Response: {r3.content[:200]}")
    print("(No separate guardrail evaluation calls — instruction was injected)")
    print()
    print("System prompt received by LLM includes:")
    print("  'Always respond in a formal, professional tone...'")
    print("  'Keep all responses under 3 sentences...'")


if __name__ == "__main__":
    main()
