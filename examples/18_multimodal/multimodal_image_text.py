"""Multimodal input: image + text.

Shows how to pass content parts (text + image_url) to an agent.
Requires a vision-capable model (e.g. gpt-4o, claude-3-5-sonnet).

Run:
    python examples/18_multimodal/multimodal_image_text.py

Set OPENAI_API_KEY (or ANTHROPIC_API_KEY) for a real model.
Uses Almock for structure demo when no key is set.
"""

from __future__ import annotations

import base64
import os

from syrin import Agent
from syrin.model import Model
from syrin.multimodal import file_to_message


def main() -> None:
    # Use real vision model if key available; else Almock for demo
    if os.getenv("OPENAI_API_KEY"):
        model = Model.OpenAI("gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
    elif os.getenv("ANTHROPIC_API_KEY"):
        model = Model.Anthropic(
            "claude-3-5-sonnet-20241022",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )
    else:
        model = Model.mock(latency_min=0, latency_max=0)

    agent = Agent(
        model=model,
        system_prompt="You are helpful. When given an image, describe what you see.",
    )

    # 1x1 transparent PNG (minimal valid image for demo)
    minimal_png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    data_url = file_to_message(minimal_png, "image/png")

    content_parts = [
        {"type": "text", "text": "What's in this image? Describe it briefly."},
        {"type": "image_url", "image_url": {"url": data_url}},
    ]

    r = agent.run(content_parts)
    print("Response:", r.content)


if __name__ == "__main__":
    main()
