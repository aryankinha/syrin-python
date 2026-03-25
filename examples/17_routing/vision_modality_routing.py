"""Vision/media routing — ModalityDetector routes image prompts to vision models.

When messages contain images (base64 data URLs), router picks profiles with
input_media including IMAGE. Text-only profiles excluded.
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
    # Almock (no real vision; for structure demo)
    text_model = Model.Almock(
        latency_min=0,
        latency_max=0,
        profile_name="text-only",
        strengths=[TaskType.GENERAL, TaskType.CODE],
        input_media={Media.TEXT},
        output_media={Media.TEXT},
        priority=90,
    )
    vision_model = Model.Almock(
        latency_min=0,
        latency_max=0,
        profile_name="vision",
        strengths=[TaskType.VISION, TaskType.GENERAL],
        input_media={Media.TEXT, Media.IMAGE},
        output_media={Media.TEXT},
        priority=85,
    )

    models_list = [text_model, vision_model]
    router = ModelRouter(models=models_list, routing_mode=RoutingMode.AUTO)

    agent = Agent(
        model=models_list,
        model_router=RoutingConfig(router=router),
        system_prompt="You are helpful.",
    )

    # Text prompt -> text-only (higher priority for GENERAL)
    r = agent.run("Describe this", task_type=TaskType.GENERAL)
    print(f"Text prompt -> {r.routing_reason.selected_model}")

    # Vision task -> vision profile (only vision supports VISION)
    r2 = agent.run("What's in this image?", task_type=TaskType.VISION)
    print(f"Vision task -> {r2.routing_reason.selected_model}")


if __name__ == "__main__":
    main()
