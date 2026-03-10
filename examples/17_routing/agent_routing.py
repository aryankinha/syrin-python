"""Agent with Model Routing — model list, RoutingConfig, ROUTING_DECISION hook.

Uses Almock so no API key is required. Replace with real models for production.

Run: python -m examples.17_routing.agent_routing
Run with traces: python -m examples.17_routing.agent_routing --trace
"""

from __future__ import annotations

import sys

from syrin import Agent, Budget, Hook
from syrin.model import Model
from syrin.router import (
    ModelRouter,
    RoutingConfig,
    RoutingMode,
    TaskType,
)


def main() -> None:
    # Almock models with distinct strengths for routing demo
    general_m = Model.Almock(
        context_window=4096,
        latency_min=0,
        latency_max=0,
        profile_name="general",
        strengths=[TaskType.GENERAL, TaskType.CREATIVE],
        priority=90,
    )
    code_m = Model.Almock(
        context_window=8192,
        latency_min=0,
        latency_max=0,
        profile_name="code",
        strengths=[TaskType.CODE, TaskType.REASONING],
        priority=100,
    )

    models_list = [general_m, code_m]
    router = ModelRouter(models=models_list, routing_mode=RoutingMode.AUTO)

    use_trace = "--trace" in sys.argv
    agent = Agent(
        model=models_list,
        model_router=RoutingConfig(router=router),
        system_prompt="You are helpful.",
        budget=Budget(run=1.0),
        debug=use_trace,
    )

    # Track routing decisions via hook
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

    # Route by task_override (no classifier needed)
    prompts = [
        ("hello, how are you?", TaskType.GENERAL),
        ("write a function to sort a list", TaskType.CODE),
    ]
    for prompt, task in prompts:
        r = agent.response(prompt, task_type=task)
        print(f"  {prompt!r}")
        print(
            f"    -> {r.routing_reason.selected_model if r.routing_reason else 'N/A'} | {r.routing_reason.reason if r.routing_reason else 'N/A'}"
        )
        print(f"    content: {r.content[:60]}...")

    print(f"\nHook fired {len(decisions)} times: {decisions}")


if __name__ == "__main__":
    main()
