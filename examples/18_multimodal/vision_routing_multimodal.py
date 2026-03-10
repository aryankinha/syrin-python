"""Vision routing: router picks vision-capable model when message contains images.

Use a model list + RoutingConfig with one text-only profile and one profile that
has input_media={Media.TEXT, Media.IMAGE}. ModalityDetector.detect(messages)
returns set[Media]; the router filters profiles by input_media. So when the user
sends content parts with an image, the vision profile is selected.

Run:
    python -m examples.18_multimodal.vision_routing_multimodal

Requires: OPENAI_API_KEY for real models. Without it, uses Almock (same routing logic).
Covers: Model input_media, ModalityDetector, routing by message content.
"""

from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from syrin import Agent, Model
from syrin.enums import Media
from syrin.multimodal import file_to_message
from syrin.router import (
    ModelRouter,
    RoutingConfig,
    RoutingMode,
    TaskType,
)


def main() -> None:
    if os.getenv("OPENAI_API_KEY"):
        text_model = Model.OpenAI(
            "gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
            profile_name="text-only",
            strengths=[TaskType.GENERAL, TaskType.CODE],
            input_media={Media.TEXT},
            output_media={Media.TEXT},
            priority=80,
        )
        vision_model = Model.OpenAI(
            "gpt-4o",
            api_key=os.getenv("OPENAI_API_KEY"),
            profile_name="vision",
            strengths=[TaskType.VISION, TaskType.GENERAL],
            input_media={Media.TEXT, Media.IMAGE},
            output_media={Media.TEXT},
            priority=90,
        )
    else:
        text_model = Model.Almock(
            latency_min=0,
            latency_max=0,
            profile_name="text-only",
            strengths=[TaskType.GENERAL, TaskType.CODE],
            input_media={Media.TEXT},
            output_media={Media.TEXT},
            priority=80,
        )
        vision_model = Model.Almock(
            latency_min=0,
            latency_max=0,
            profile_name="vision",
            strengths=[TaskType.VISION, TaskType.GENERAL],
            input_media={Media.TEXT, Media.IMAGE},
            output_media={Media.TEXT},
            priority=90,
        )

    models_list = [text_model, vision_model]
    router = ModelRouter(models=models_list, routing_mode=RoutingMode.AUTO)
    agent = Agent(
        model=models_list,
        model_router=RoutingConfig(router=router),
        system_prompt="You are helpful. Describe images when given one.",
        input_media={Media.TEXT, Media.IMAGE},
    )

    # Text-only message -> router can pick text-only or vision (both support TEXT)
    r1 = agent.response("What is the capital of France?")
    print(
        "Text-only prompt -> selected:",
        r1.routing_reason.selected_model if r1.routing_reason else "N/A",
    )

    # Message with image -> router must pick vision (text-only doesn't support IMAGE)
    minimal_png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    data_url = file_to_message(minimal_png, "image/png")
    content_parts = [
        {"type": "text", "text": "What do you see in this image?"},
        {"type": "image_url", "image_url": {"url": data_url}},
    ]
    r2 = agent.response(content_parts)
    print(
        "Image + text prompt -> selected:",
        r2.routing_reason.selected_model if r2.routing_reason else "N/A",
    )
    print("  (vision profile required because message contains image)")


if __name__ == "__main__":
    main()
