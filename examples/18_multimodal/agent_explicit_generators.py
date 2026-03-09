"""Agent with explicit image_generation and video_generation params.

Use static constructors:
  Image: ImageGenerator.Gemini() (Google), .DALLE() (OpenAI)
  Video: VideoGenerator.Gemini() (Google)

Budget: When a budget is set, image and video generation cost is automatically
recorded (built-in providers populate metadata). Response.cost includes both
LLM tokens and generation.

Run:
    python -m examples.18_multimodal.agent_explicit_generators

Requires: OPENAI_API_KEY for chat; GOOGLE_API_KEY for image/video (or OPENAI_API_KEY for DALL·E).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from syrin import Agent, Budget, ImageGenerator, Model, VideoGenerator


def main() -> None:
    api_key = (
        os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or ""
    ).strip() or None

    # Static constructors: ImageGenerator.Gemini(), VideoGenerator.Gemini()
    img_gen = ImageGenerator.Gemini(api_key=api_key) if api_key else None
    vid_gen = VideoGenerator.Gemini(api_key=api_key) if api_key else None

    agent = Agent(
        model=Model.OpenAI("gpt-4o-mini") if os.getenv("OPENAI_API_KEY") else Model.Almock(),
        system_prompt=(
            "You are helpful. When the user asks for an image, use generate_image. "
            "When they ask for a video, use generate_video."
        ),
        image_generation=img_gen,
        video_generation=vid_gen,
        budget=Budget(run=5.0),  # Image/video generation cost is recorded automatically
    )

    tool_names = [t.name for t in agent._tools]
    print("Agent tools:", tool_names)
    print("  image_generation:", "set" if agent._image_generator else "None")
    print("  video_generation:", "set" if agent._video_generator else "None")

    if "generate_image" in tool_names:
        r = agent.response("Create a simple image of a blue square.")
        print("Image response:", (r.content or "")[:150])
        print("Cost (includes LLM + image generation):", r.cost)
    else:
        print("No image/video tools (set GOOGLE_API_KEY for Gemini)")


if __name__ == "__main__":
    main()
