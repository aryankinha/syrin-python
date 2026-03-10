"""Custom routing callback — route by prompt keywords, user tier, A/B test, etc.

routing_rule_callback(prompt, task_type, profile_names) -> preferred_profile_name | None.
Return None to use default routing.

Uses Almock (no API key).
"""

from __future__ import annotations

from syrin import Agent
from syrin.model import Model
from syrin.router import (
    ModelRouter,
    RoutingConfig,
    RoutingMode,
    TaskType,
)


def vip_routing_callback(
    prompt: str,
    task_type: TaskType,
    profile_names: list[str],
) -> str | None:
    """Route VIP prompts (containing 'priority' or 'urgent') to premium model."""
    if ("priority" in prompt.lower() or "urgent" in prompt.lower()) and "premium" in profile_names:
        return "premium"
    return None  # Use default routing


def main() -> None:
    standard = Model.Almock(
        latency_min=0,
        latency_max=0,
        profile_name="standard",
        strengths=[TaskType.GENERAL, TaskType.CODE],
        priority=90,
    )
    premium = Model.Almock(
        latency_min=0,
        latency_max=0,
        profile_name="premium",
        strengths=[TaskType.GENERAL, TaskType.CODE, TaskType.REASONING],
        priority=100,
    )

    models_list = [standard, premium]
    router = ModelRouter(
        models=models_list,
        routing_mode=RoutingMode.AUTO,
        routing_rule_callback=vip_routing_callback,
    )

    agent = Agent(
        model=models_list,
        model_router=RoutingConfig(router=router),
        system_prompt="You are helpful.",
    )

    r1 = agent.response("What is 2+2?", task_type=TaskType.GENERAL)
    print(f"Normal prompt -> {r1.routing_reason.selected_model}")

    r2 = agent.response("URGENT: Fix this bug now", task_type=TaskType.CODE)
    print(f"VIP prompt -> {r2.routing_reason.selected_model}")


if __name__ == "__main__":
    main()
