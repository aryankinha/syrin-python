"""Use get_default_profiles() — built-in claude-code, gpt-general, gemini-vision.

Pass API keys when creating Agent (keys injected into profiles).
Uses Almock here so it runs without keys; swap to real models for production.
"""

from __future__ import annotations

from syrin import Agent
from syrin.enums import Media
from syrin.model import Model
from syrin.router import (
    ModelRouter,
    RoutingConfig,
    RoutingMode,
    TaskType,
)


def main() -> None:
    # Mirror get_default_profiles structure with Almock (no keys)
    m = Model.Almock(latency_min=0, latency_max=0)
    models_list = [
        m.with_routing(
            profile_name="claude-code",
            strengths=[TaskType.CODE, TaskType.REASONING, TaskType.PLANNING],
            priority=100,
        ),
        m.with_routing(
            profile_name="gpt-general",
            strengths=[TaskType.GENERAL, TaskType.CREATIVE, TaskType.TRANSLATION],
            priority=90,
        ),
        m.with_routing(
            profile_name="gemini-vision",
            strengths=[TaskType.VISION, TaskType.VIDEO],
            input_media={Media.TEXT, Media.IMAGE},
            output_media={Media.TEXT},
            priority=80,
        ),
    ]

    # To use real defaults: models_list = list(get_default_profiles().values())
    # and pass API keys to Model.Anthropic/OpenAI/Google when creating models.

    router = ModelRouter(models=models_list, routing_mode=RoutingMode.AUTO)
    agent = Agent(
        model=models_list,
        model_router=RoutingConfig(router=router),
        system_prompt="You are helpful.",
    )

    r = agent.response("write a python function", task_type=TaskType.CODE)
    print(f"CODE -> {r.routing_reason.selected_model}")

    r = agent.response("hello", task_type=TaskType.GENERAL)
    print(f"GENERAL -> {r.routing_reason.selected_model}")


if __name__ == "__main__":
    main()
