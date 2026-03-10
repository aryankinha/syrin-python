"""Cartesia Sonic TTS provider. Requires cartesia package.

Ultra-low latency (~90ms TTFB). Best for real-time voice agents.
"""

from __future__ import annotations

import base64
from typing import Any

from syrin.cost import calculate_voice_cost
from syrin.generation._result import GenerationResult


class CartesiaVoiceProvider:
    """Cartesia Sonic TTS provider. Implements VoiceGenerationProvider.

    Requires: pip install syrin[voice] or pip install cartesia.
    Set CARTESIA_API_KEY or pass api_key=.
    """

    def __init__(
        self,
        api_key: str | None = None,
        voice_id: str = "default",
        model: str = "sonic-3",
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
            from cartesia import Cartesia  # type: ignore[import-not-found]
        except ImportError as e:
            return GenerationResult(
                success=False,
                error=f"Cartesia TTS requires cartesia package. pip install syrin[voice]. {e!s}",
            )
        import os

        key = self.api_key or os.environ.get("CARTESIA_API_KEY")
        if not key or not str(key).strip():
            return GenerationResult(
                success=False,
                error="Cartesia TTS requires CARTESIA_API_KEY or api_key=.",
            )
        vid = voice_id if voice_id != "default" else self.voice_id
        model_id = kwargs.get("model") or self.model
        try:
            client = Cartesia(api_key=key)
            response = client.tts.generate(
                model_id=model_id,
                transcript=text,
                voice_id=vid,
                output_format=output_format,
                **{**self._kwargs, **{k: v for k, v in kwargs.items() if k != "model"}},
            )
            content_bytes = response if isinstance(response, bytes) else bytes(response)
            if not content_bytes:
                return GenerationResult(success=False, error="No audio in response")
            mime = "audio/mpeg" if output_format == "mp3" else f"audio/{output_format}"
            b64 = base64.b64encode(content_bytes).decode("ascii")
            url = f"data:{mime};base64,{b64}"
            cost_usd = calculate_voice_cost("sonic-3", len(text))
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
