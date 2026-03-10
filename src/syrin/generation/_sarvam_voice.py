"""Sarvam AI TTS provider. Requires sarvam-ai package.

Specialized in Indian languages. 11 languages, Bulbul v3 model.
"""

from __future__ import annotations

import base64
from typing import Any

from syrin.cost import calculate_voice_cost
from syrin.generation._result import GenerationResult


class SarvamVoiceProvider:
    """Sarvam AI TTS provider. Implements VoiceGenerationProvider.

    Requires: pip install syrin[voice-sarvam] or pip install sarvam-ai.
    Set SARVAM_API_KEY or pass api_key=.
    """

    def __init__(
        self,
        api_key: str | None = None,
        voice: str = "meera",
        language: str = "en-IN",
        model: str = "bulbul:v3",
        **kwargs: Any,
    ) -> None:
        self.api_key = api_key
        self.voice = voice
        self.language = language
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
            from sarvam import Sarvam  # type: ignore[import-not-found]
        except ImportError as e:
            return GenerationResult(
                success=False,
                error=f"Sarvam TTS requires sarvam-ai package. pip install syrin[voice-sarvam]. {e!s}",
            )
        import os

        key = self.api_key or os.environ.get("SARVAM_API_KEY")
        if not key or not str(key).strip():
            return GenerationResult(
                success=False,
                error="Sarvam TTS requires SARVAM_API_KEY or api_key=.",
            )
        voice_name = voice_id if voice_id != "default" else self.voice
        lang = language if language != "en" else self.language
        model_id = kwargs.get("model") or self.model
        try:
            client = Sarvam(api_key=key)
            response = client.tts.generate(
                text=text,
                voice=voice_name,
                language=lang,
                model=model_id,
                **{**self._kwargs, **{k: v for k, v in kwargs.items() if k != "model"}},
            )
            content_bytes = response if isinstance(response, bytes) else bytes(response)
            if not content_bytes:
                return GenerationResult(success=False, error="No audio in response")
            mime = "audio/mpeg"
            b64 = base64.b64encode(content_bytes).decode("ascii")
            url = f"data:{mime};base64,{b64}"
            cost_usd = calculate_voice_cost("bulbul:v3", len(text))
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
