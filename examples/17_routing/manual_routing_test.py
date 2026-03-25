"""Manual routing test with 5 real models across providers.

Tests routing + fallback when one provider (e.g. Anthropic) has no budget.

Setup: Add API keys to examples/.env:
  OPENAI_API_KEY, GOOGLE_API_KEY, ANTHROPIC_API_KEY, DEEPSEEK_API_KEY

Run: python -m examples.17_routing.manual_routing_test

Note: Routing selects a model BEFORE the LLM call. If the selected model's API
fails (e.g. Anthropic 402 out of budget), model-level fallback (.with_fallback)
is used — Claude falls back to gpt-4o-mini. The router does NOT re-route on failure.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from syrin import Agent, Budget, Hook
from syrin.model import Model
from syrin.router import (
    ModelRouter,
    RoutingConfig,
    RoutingMode,
    TaskType,
)

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# 5 models from different providers
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")


def build_models() -> tuple[Model, Model, Model, Model, Model]:
    """Build 5 models. Claude gets fallback to gpt-4o-mini when Anthropic is out of budget."""
    gpt_mini = Model.OpenAI("gpt-4o-mini", api_key=OPENAI_KEY)
    gpt4o = Model.OpenAI("gpt-4o", api_key=OPENAI_KEY)
    gemini = Model.Google("gemini-2.0-flash", api_key=GOOGLE_KEY)
    claude = Model.Anthropic("claude-sonnet-4-5", api_key=ANTHROPIC_KEY)
    deepseek = Model.Custom(
        "deepseek-chat",
        api_base="https://api.deepseek.com/v1",
        api_key=DEEPSEEK_KEY,
        context_window=128_000,
    )
    # When Anthropic is out of budget (402), fall back to OpenAI
    claude_with_fallback = claude.with_fallback(gpt_mini)
    return gpt_mini, gpt4o, gemini, claude_with_fallback, deepseek


def main() -> None:
    gpt_mini, gpt4o, gemini, claude, deepseek = build_models()

    models_list = [
        gpt_mini.with_routing(
            profile_name="gpt-4o-mini", strengths=[TaskType.GENERAL, TaskType.CREATIVE], priority=85
        ),
        gpt4o.with_routing(
            profile_name="gpt-4o", strengths=[TaskType.CODE, TaskType.REASONING], priority=95
        ),
        gemini.with_routing(
            profile_name="gemini",
            strengths=[TaskType.GENERAL, TaskType.REASONING, TaskType.VISION],
            priority=90,
        ),
        claude.with_routing(
            profile_name="claude-sonnet",
            strengths=[TaskType.CODE, TaskType.REASONING, TaskType.PLANNING],
            priority=100,
        ),
        deepseek.with_routing(
            profile_name="deepseek", strengths=[TaskType.CODE, TaskType.GENERAL], priority=80
        ),
    ]

    router = ModelRouter(models=models_list, routing_mode=RoutingMode.AUTO)
    agent = Agent(
        model=models_list,
        model_router=RoutingConfig(router=router),
        system_prompt="You are helpful. Be concise.",
        budget=Budget(max_cost=2.0),
    )

    decisions: list[dict] = []

    def on_routing(ctx: dict) -> None:
        reason = ctx.get("routing_reason")
        decisions.append(
            {
                "model": ctx.get("model"),
                "task_type": reason.task_type.value if reason else None,
                "reason": reason.reason if reason else None,
            }
        )

    agent.events.on(Hook.ROUTING_DECISION, on_routing)

    prompts = [
        ("Say hello in one sentence.", TaskType.GENERAL),
        ("Write a one-line Python function to reverse a string.", TaskType.CODE),
        ("What is 2+2? Answer in one word.", TaskType.REASONING),
    ]

    print("Manual routing test — 5 models (OpenAI x2, Google, Anthropic, DeepSeek)")
    print("If Anthropic is out of budget and router picks Claude, fallback → gpt-4o-mini\n")

    for prompt, task in prompts:
        try:
            r = agent.run(prompt, task_type=task)
            model_used = r.model_used or r.model or "N/A"
            reason = r.routing_reason
            sel = reason.selected_model if reason else "N/A"
            reas = reason.reason if reason else "N/A"
            print(f"  {prompt!r}")
            print(f"    routed -> {sel} | {reas}")
            print(f"    model_used -> {model_used}")
            print(f"    content: {r.content[:80]}...")
        except Exception as e:
            print(f"  {prompt!r}")
            print(f"    ERROR: {e}")
        print()

    print(f"ROUTING_DECISION hook fired {len(decisions)} times:")
    for i, d in enumerate(decisions, 1):
        print(f"  {i}. {d}")


if __name__ == "__main__":
    main()
