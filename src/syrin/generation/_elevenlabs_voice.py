"""ElevenLabs TTS provider. Requires elevenlabs package.

Models: eleven_flash_v2_5 (fast), eleven_turbo_v2_5 (quality), eleven_multilingual_v2.
"""

from __future__ import annotations

import base64
from typing import Any

from syrin.cost import calculate_voice_cost
from syrin.generation._result import GenerationResult


class ElevenLabsVoiceProvider:
    """ElevenLabs TTS provider. Implements VoiceGenerationProvider.

    Requires: pip install syrin[voice] or pip install elevenlabs.
    Set ELEVENLABS_API_KEY or pass api_key=.
    """

    def __init__(
        self,
        api_key: str | None = None,
        voice_id: str = "JBFqnCBsd6RMkjVDRZzb",
        model: str = "eleven_flash_v2_5",
        **kwargs: Any,
    ) -> None:
        self.api_key = api_key
        self.voice_id = voice_id
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
            from elevenlabs.client import ElevenLabs  # type: ignore[import-not-found]
        except ImportError as e:
            return GenerationResult(
                success=False,
                error=f"ElevenLabs TTS requires elevenlabs package. pip install syrin[voice]. {e!s}",
            )
        import os

        key = self.api_key or os.environ.get("ELEVENLABS_API_KEY")
        if not key or not str(key).strip():
            return GenerationResult(
                success=False,
                error="ElevenLabs TTS requires ELEVENLABS_API_KEY or api_key=.",
            )
        vid = voice_id if voice_id != "default" else self.voice_id
        model_id = kwargs.get("model") or self.model
        fmt = "mp3_44100_128" if output_format == "mp3" else f"{output_format}_44100_128"
        try:
            client = ElevenLabs(api_key=key)
            audio = client.text_to_speech.convert(
                text=text,
                voice_id=vid,
                model_id=model_id,
                output_format=fmt,
                **{**self._kwargs, **{k: v for k, v in kwargs.items() if k != "model"}},
            )
            content_bytes = audio if isinstance(audio, bytes) else bytes(audio)
            if not content_bytes:
                return GenerationResult(success=False, error="No audio in response")
            mime = "audio/mpeg"
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
