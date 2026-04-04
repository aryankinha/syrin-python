"""Cost-first routing with budget thresholds.

When budget is low, router prefers cheaper models. When critical, forces cheapest.
Uses Almock (no API key). Replace with real models for production.

Features: RoutingMode.COST_FIRST, prefer_cheaper_below_budget_ratio, force_cheapest_below_budget_ratio, budget_optimisation.

Run: python -m examples.17_routing.cost_first_budget_agent
Run with traces: python -m examples.17_routing.cost_first_budget_agent --trace
"""

from __future__ import annotations

import sys

from syrin import Agent, Budget
from syrin.model import Model
from syrin.router import (
    ModelRouter,
    RoutingConfig,
    RoutingMode,
    TaskType,
)


def main() -> None:
    # Cheap vs expensive (Almock; in production use gpt-4o-mini vs gpt-4o)
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
        strengths=[TaskType.GENERAL, TaskType.CODE, TaskType.REASONING],
        priority=100,
    )

    models_list = [cheap, expensive]
    router = ModelRouter(
        models=models_list,
        routing_mode=RoutingMode.COST_FIRST,
        budget_optimisation=True,
        prefer_cheaper_below_budget_ratio=0.20,
        force_cheapest_below_budget_ratio=0.10,
    )

    use_trace = "--trace" in sys.argv
    agent = Agent(
        model=models_list,
        model_router=RoutingConfig(router=router),
        system_prompt="You are helpful. Be concise.",
        budget=Budget(max_cost=0.50),
        debug=use_trace,
    )

    # With full budget, COST_FIRST picks cheapest capable model
    r = agent.run("Say hi", task_type=TaskType.GENERAL)
    print(f"GENERAL (full budget) -> {r.routing_reason.selected_model}: {r.routing_reason.reason}")
    print(f"  cost_estimate=${r.routing_reason.cost_estimate:.6f}")

    # CODE: both capable; COST_FIRST picks cheap
    r = agent.run("Write one line of code", task_type=TaskType.CODE)
    print(f"CODE -> {r.routing_reason.selected_model}: {r.routing_reason.reason}")


if __name__ == "__main__":
    main()
