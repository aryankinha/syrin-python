"""OpenAI TTS provider. Requires openai package.

Models: tts-1 (fast), tts-1-hd (higher quality).
Voices: alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer.
"""

from __future__ import annotations

import base64
from typing import Any

from syrin.cost import calculate_voice_cost
from syrin.generation._result import GenerationResult

_OPENAI_VOICES: frozenset[str] = frozenset(
    {"alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer"}
)


class OpenAIVoiceProvider:
    """OpenAI TTS provider. Implements VoiceGenerationProvider.

    Requires: pip install syrin[openai] or pip install openai.
    Set OPENAI_API_KEY or pass api_key=.
    """

    def __init__(
        self,
        api_key: str | None = None,
        voice: str = "alloy",
        model: str = "tts-1",
        **kwargs: Any,
    ) -> None:
        self.api_key = api_key
        self.voice = voice if voice in _OPENAI_VOICES else "alloy"
        self.model = model
        self._kwargs = kwargs

    def generate(
        self,
        text: str,
        *,
        voice_id: str = "default",
        speed: float = 1.0,
        language: str = "en",
        output_format: str = "mp3",
        **kwargs: Any,
    ) -> GenerationResult:
        try:
            from openai import OpenAI
        except ImportError as e:
            return GenerationResult(
                success=False,
                error=f"OpenAI TTS requires openai package. pip install syrin[openai]. {e!s}",
            )
        import os

        key = self.api_key or os.environ.get("OPENAI_API_KEY")
        if not key or not str(key).strip():
            return GenerationResult(
                success=False,
                error="OpenAI TTS requires OPENAI_API_KEY or api_key=.",
            )
        voice_name = voice_id if voice_id != "default" else self.voice
        model_id = kwargs.get("model") or self.model
        try:
            client = OpenAI(api_key=key)
            resp = client.audio.speech.create(
                model=model_id,
                voice=voice_name,
                input=text,
                speed=speed,
                response_format=output_format,  # type: ignore[arg-type]
                **{**self._kwargs, **{k: v for k, v in kwargs.items() if k != "model"}},
            )
            content_bytes = resp.content
            if not content_bytes:
                return GenerationResult(success=False, error="No audio in response")
            mime = f"audio/{output_format}" if output_format != "mp3" else "audio/mpeg"
            b64 = base64.b64encode(content_bytes).decode("ascii")
            url = f"data:{mime};base64,{b64}"
            cost_usd = calculate_voice_cost(model_id, len(text))
            return GenerationResult(
                success=True,
                url=url,
                content_type=mime,
                content_bytes=content_bytes,
                metadata={"cost_usd": cost_usd, "model_name": model_id},
            )
        except Exception as e:
            return GenerationResult(success=False, error=str(e))

    async def generate_async(
        self,
        text: str,
        *,
        voice_id: str = "default",
        speed: float = 1.0,
        language: str = "en",
        **kwargs: Any,
    ) -> GenerationResult:
        import asyncio

        return await asyncio.to_thread(
            self.generate,
            text,
            voice_id=voice_id,
            speed=speed,
            language=language,
            **kwargs,
        )
