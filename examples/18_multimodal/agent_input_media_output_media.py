"""Declare agent capabilities: input_media and output_media.

Shows how to set input_media (what the agent accepts) and output_media (what it
can produce). Capabilities are discoverable via agent._input_media and
agent._output_media. When using a router, profiles must support these media types.

Run:
    python -m examples.18_multimodal.agent_input_media_output_media

Covers: Media enum, input_media, output_media, capability discovery.
"""

from __future__ import annotations

from syrin import Agent, Model
from syrin.enums import Media


def main() -> None:
    # Text-only agent (default)
    text_agent = Agent(
        model=Model.mock(latency_min=0, latency_max=0),
        system_prompt="You are a text-only assistant.",
    )
    print("Text-only agent:")
    print("  input_media:", sorted(m.value for m in text_agent._input_media))
    print("  output_media:", sorted(m.value for m in text_agent._output_media))

    # Agent that accepts text + images and can produce text
    vision_agent = Agent(
        model=Model.mock(latency_min=0, latency_max=0),
        system_prompt="You can see images and answer questions about them.",
        input_media={Media.TEXT, Media.IMAGE},
        output_media={Media.TEXT},
    )
    print("\nVision-capable agent (accepts image + text, outputs text):")
    print("  input_media:", sorted(m.value for m in vision_agent._input_media))
    print("  output_media:", sorted(m.value for m in vision_agent._output_media))

    # Agent that can also produce images (generation tools when GOOGLE_API_KEY set)
    full_agent = Agent(
        model=Model.mock(latency_min=0, latency_max=0),
        system_prompt="You can chat, see images, and generate images/videos when asked.",
        input_media={Media.TEXT, Media.IMAGE},
        output_media={Media.TEXT, Media.IMAGE, Media.VIDEO},
    )
    print("\nFull multimodal agent (in: text+image, out: text+image+video):")
    print("  input_media:", sorted(m.value for m in full_agent._input_media))
    print("  output_media:", sorted(m.value for m in full_agent._output_media))
    print("  tools:", [t.name for t in full_agent._tools])


if __name__ == "__main__":
    main()
