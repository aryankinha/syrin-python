"""Agent with voice generation (TTS) via voice_generation.

Pass voice_generation=VoiceGenerator.OpenAI() or ElevenLabs() and
output_media={Media.AUDIO} to add the generate_voice tool.
Voice cost is recorded into the budget when available.

Run:
    python -m examples.18_multimodal.agent_voice_generation

Requires: OPENAI_API_KEY for both chat and TTS, or ELEVENLABS_API_KEY for ElevenLabs.
"""

from __future__ import annotations

import os

from syrin import Agent, Budget, Model, VoiceGenerator
from syrin.enums import Media


def main() -> None:
    # Voice: OpenAI TTS (requires openai) or ElevenLabs (requires elevenlabs)
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    eleven_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()

    if openai_key:
        voice_gen = VoiceGenerator.OpenAI(api_key=openai_key)
    elif eleven_key:
        voice_gen = VoiceGenerator.ElevenLabs(api_key=eleven_key)
    else:
        voice_gen = None

    model = (
        Model.OpenAI("gpt-4o-mini", api_key=openai_key)
        if openai_key
        else Model.mock(latency_min=0, latency_max=0)
    )

    agent = Agent(
        model=model,
        output_media={Media.TEXT, Media.AUDIO},
        voice_generation=voice_gen,
        budget=Budget(max_cost=5.0),
        system_prompt=(
            "You are helpful. When the user asks you to speak, say something aloud, "
            "or produce audio, use the generate_voice tool to create speech."
        ),
    )

    tool_names = [t.name for t in agent._tools]
    print("Agent tools:", tool_names)
    if "generate_voice" in tool_names:
        print("  generate_voice: available")
        r = agent.run("Say 'Hello, welcome to Syrin' in a friendly tone.")
        print("Voice request response:", (r.content or "")[:200])
        print("Cost (LLM + voice):", r.cost)
    else:
        print("  generate_voice: not added (set OPENAI_API_KEY or ELEVENLABS_API_KEY)")


if __name__ == "__main__":
    main()
