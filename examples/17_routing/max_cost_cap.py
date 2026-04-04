"""Cost comparison — COST_FIRST picks cheapest capable model.

Compare cost_estimate across profiles. Use for cost-sensitive routing.
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


def main() -> None:
    cheap = Model.mock(
        pricing_tier="low",
        latency_min=0,
        latency_max=0,
        profile_name="cheap",
        strengths=[TaskType.GENERAL, TaskType.CODE],
        priority=80,
    )
    expensive = Model.mock(
        pricing_tier="high",
        latency_min=0,
        latency_max=0,
        profile_name="expensive",
        strengths=[TaskType.GENERAL, TaskType.CODE],
        priority=100,
    )

    models_list = [cheap, expensive]
    router = ModelRouter(
        models=models_list,
        routing_mode=RoutingMode.COST_FIRST,
    )

    agent = Agent(
        model=models_list,
        model_router=RoutingConfig(router=router),
        system_prompt="You are helpful.",
    )

    r = agent.run("hi", task_type=TaskType.GENERAL)
    print(
        f"Routed to: {r.routing_reason.selected_model} | cost_estimate=${r.routing_reason.cost_estimate:.6f}"
    )
