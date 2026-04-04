"""Agent with image/video generation tools via output_media.

When output_media includes Media.IMAGE and/or Media.VIDEO, the agent gets
generate_image and generate_video tools (when GOOGLE_API_KEY or a Google model
key is available). No separate generation=True; capabilities are declarative.

Run:
    python -m examples.18_multimodal.agent_with_generation_tools

Requires: OPENAI_API_KEY for chat model; GOOGLE_API_KEY for image/video tools.
Without GOOGLE_API_KEY the agent runs but has no image/video tools.
"""

from __future__ import annotations

import os

from syrin import Agent, Model
from syrin.enums import Media


def main() -> None:
    # Chat model (OpenAI or Almock); generation tools use Gemini when GOOGLE_API_KEY set
    if os.getenv("OPENAI_API_KEY"):
        model = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
    else:
        model = Model.mock(latency_min=0, latency_max=0)

    agent = Agent(
        model=model,
        output_media={Media.TEXT, Media.IMAGE, Media.VIDEO},
        system_prompt=(
            "You are helpful. When the user asks for an image, use the generate_image tool. "
            "When they ask for a video, use generate_video. Otherwise respond in text."
        ),
    )

    # Check which tools were added (depends on GOOGLE_API_KEY)
    tool_names = [t.name for t in agent._tools]
    print("Agent tools:", tool_names)
    if "generate_image" in tool_names:
        print("  generate_image: available (GOOGLE_API_KEY set)")
    else:
        print("  generate_image: not added (set GOOGLE_API_KEY for Gemini)")
    if "generate_video" in tool_names:
        print("  generate_video: available (GOOGLE_API_KEY set)")
    else:
        print("  generate_video: not added (set GOOGLE_API_KEY for Gemini)")

    # Text-only question
    r = agent.run("What is 2 + 2? Reply with just the number.")
    print("Q: What is 2 + 2?")
    print("A:", r.content[:200] if r.content else "(empty)")

    # If tools are available, the agent can be asked to generate an image
    if "generate_image" in tool_names:
        print("\nAsking agent to create an image...")
        r2 = agent.run("Create a simple image of a red circle on white background.")
        print("Image request response:", (r2.content or "")[:300])


if __name__ == "__main__":
    main()
