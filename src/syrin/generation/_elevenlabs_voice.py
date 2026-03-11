"""ElevenLabs TTS provider. Requires elevenlabs package.

Models: eleven_flash_v2_5 (fast), eleven_turbo_v2_5 (quality), eleven_multilingual_v2.
"""

from __future__ import annotations

from typing import Any

from syrin.generation._base_voice import BaseVoiceProvider


class ElevenLabsVoiceProvider(BaseVoiceProvider):
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
        super().__init__(api_key=api_key, model=model, **kwargs)
        self.voice_id = voice_id

    def _get_api_key_env(self) -> str:
        return "ELEVENLABS_API_KEY"

    def _get_package_name(self) -> str:
        return "syrin[voice]"

    def _synthesize(
        self,
        text: str,
        *,
        api_key: str,
        voice_id: str,
        speed: float,
        language: str,
        output_format: str,
        model_id: str,
        **kwargs: Any,
    ) -> tuple[bytes, str, str]:
        from elevenlabs.client import ElevenLabs  # type: ignore[import-not-found]

        vid = voice_id if voice_id != "default" else self.voice_id
        fmt = "mp3_44100_128" if output_format == "mp3" else f"{output_format}_44100_128"
        client = ElevenLabs(api_key=api_key)
        audio = client.text_to_speech.convert(
            text=text,
            voice_id=vid,
            model_id=model_id,
            output_format=fmt,
            **{**self._kwargs, **kwargs},
        )
        content_bytes = audio if isinstance(audio, bytes) else bytes(audio)
        return content_bytes, model_id, "audio/mpeg"

    async def _asynthesize(
        self,
        text: str,
        *,
        api_key: str,
        voice_id: str,
        speed: float,
        language: str,
        output_format: str,
        model_id: str,
        **kwargs: Any,
    ) -> tuple[bytes, str, str]:
        from elevenlabs.client import AsyncElevenLabs

        vid = voice_id if voice_id != "default" else self.voice_id
        fmt = "mp3_44100_128" if output_format == "mp3" else f"{output_format}_44100_128"
        client = AsyncElevenLabs(api_key=api_key)
        audio = await client.text_to_speech.convert(
            text=text,
            voice_id=vid,
            model_id=model_id,
            output_format=fmt,
            **{**self._kwargs, **kwargs},
        )
        content_bytes = audio if isinstance(audio, bytes) else bytes(audio)
        return content_bytes, model_id, "audio/mpeg"
