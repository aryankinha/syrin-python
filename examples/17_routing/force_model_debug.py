"""Force a specific model — bypass routing for debugging or fixed model.

Use force_model to always use one model, regardless of task or cost.
Useful for: debug reproduction, A/B control, compliance (always use local model).
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
    a = Model.Almock(
        latency_min=0, latency_max=0, profile_name="a", strengths=[TaskType.GENERAL], priority=90
    )
    b = Model.Almock(
        latency_min=0, latency_max=0, profile_name="b", strengths=[TaskType.CODE], priority=100
    )
    forced = Model.Almock(latency_min=0, latency_max=0)

    models_list = [a, b]
    router = ModelRouter(
        models=models_list,
        routing_mode=RoutingMode.AUTO,
        force_model=forced,
    )

    agent = Agent(
        model=[*models_list, forced],
        model_router=RoutingConfig(router=router),
        system_prompt="You are helpful.",
    )

    # Routing bypassed; always uses force_model
    r = agent.run("write code", task_type=TaskType.CODE)
    print(f"routing_reason: {r.routing_reason.reason}")
    assert "force_model" in r.routing_reason.reason


if __name__ == "__main__":
    main()
