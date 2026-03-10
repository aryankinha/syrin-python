"""Deepgram Aura TTS provider. Requires deepgram-sdk package."""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path
from typing import Any

from syrin.cost import calculate_voice_cost
from syrin.generation._result import GenerationResult


class DeepgramVoiceProvider:
    """Deepgram Aura TTS provider. Implements VoiceGenerationProvider.

    Requires: pip install syrin[voice] or pip install deepgram-sdk.
    Set DEEPGRAM_API_KEY or pass api_key=.
    """

    def __init__(
        self,
        api_key: str | None = None,
        voice: str = "aura-asteria-en",
        model: str = "aura-asteria-en",
        **kwargs: Any,
    ) -> None:
        self.api_key = api_key
        self.voice = voice
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
            from deepgram import DeepgramClient, SpeakOptions  # type: ignore[import-not-found]
        except ImportError as e:
            return GenerationResult(
                success=False,
                error=f"Deepgram TTS requires deepgram-sdk. pip install syrin[voice]. {e!s}",
            )
        import os

        key = self.api_key or os.environ.get("DEEPGRAM_API_KEY")
        if not key or not str(key).strip():
            return GenerationResult(
                success=False,
                error="Deepgram TTS requires DEEPGRAM_API_KEY or api_key=.",
            )
        model_id = kwargs.get("model") or self.model
        try:
            client = DeepgramClient(api_key=key)
            opts = SpeakOptions(model=model_id)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp = Path(f.name)
            try:
                client.speak.rest.v("1").save(str(tmp), {"text": text}, opts)
                content_bytes = tmp.read_bytes()
            finally:
                tmp.unlink(missing_ok=True)
            if not content_bytes:
                return GenerationResult(success=False, error="No audio in response")
            mime = "audio/mpeg"
            b64 = base64.b64encode(content_bytes).decode("ascii")
            url = f"data:{mime};base64,{b64}"
            cost_usd = calculate_voice_cost("aura", len(text))
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
