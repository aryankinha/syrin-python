"""Tools-aware routing — supports_tools excludes models without tool support.

When Agent has tools, only profiles with supports_tools=True are considered.
"""

from __future__ import annotations

from syrin import Agent, tool
from syrin.model import Model
from syrin.router import (
    ModelRouter,
    RoutingConfig,
    RoutingMode,
    TaskType,
)


@tool
def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"Weather in {city}: 72°F, sunny"


def main() -> None:
    text_only = Model.Almock(
        latency_min=0,
        latency_max=0,
        profile_name="text-only",
        strengths=[TaskType.GENERAL],
        supports_tools=False,
        priority=90,
    )
    with_tools = Model.Almock(
        latency_min=0,
        latency_max=0,
        profile_name="with-tools",
        strengths=[TaskType.GENERAL],
        supports_tools=True,
        priority=80,
    )

    models_list = [text_only, with_tools]
    router = ModelRouter(models=models_list, routing_mode=RoutingMode.AUTO)

    agent = Agent(
        model=models_list,
        model_router=RoutingConfig(router=router),
        system_prompt="You are helpful.",
        tools=[get_weather],
    )

    # Agent has tools -> text-only excluded; routes to with-tools
    r = agent.run("What's the weather in NYC?")
    print(f"With tools -> {r.routing_reason.selected_model}")


if __name__ == "__main__":
    main()
