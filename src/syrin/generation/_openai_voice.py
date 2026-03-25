"""OpenAI TTS provider. Requires openai package.

Models: tts-1 (fast), tts-1-hd (higher quality).
Voices: alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer.
"""

from __future__ import annotations

from syrin.generation._base_voice import BaseVoiceProvider

_OPENAI_VOICES: frozenset[str] = frozenset(
    {"alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer"}
)


class OpenAIVoiceProvider(BaseVoiceProvider):
    """OpenAI TTS provider. Implements VoiceGenerationProvider.

    Requires: pip install syrin[openai] or pip install openai.
    Set OPENAI_API_KEY or pass api_key=.
    """

    def __init__(
        self,
        api_key: str | None = None,
        voice: str = "alloy",
        model: str = "tts-1",
        **kwargs: object,
    ) -> None:
        super().__init__(api_key=api_key, model=model, **kwargs)
        self.voice = voice if voice in _OPENAI_VOICES else "alloy"

    def _get_api_key_env(self) -> str:
        return "OPENAI_API_KEY"

    def _get_package_name(self) -> str:
        return "syrin[openai]"

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
        **kwargs: object,
    ) -> tuple[bytes, str, str]:
        from openai import OpenAI

        voice_name = voice_id if voice_id != "default" else self.voice
        client = OpenAI(api_key=api_key)
        resp = client.audio.speech.create(
            model=model_id,
            voice=voice_name,
            input=text,
            speed=speed,
            response_format=output_format,  # type: ignore[arg-type]
            **{**self._kwargs, **kwargs},  # type: ignore[arg-type]
        )
        mime = "audio/mpeg" if output_format == "mp3" else f"audio/{output_format}"
        return resp.content, model_id, mime

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
        **kwargs: object,
    ) -> tuple[bytes, str, str]:
        from openai import AsyncOpenAI

        voice_name = voice_id if voice_id != "default" else self.voice
        client = AsyncOpenAI(api_key=api_key)
        resp = await client.audio.speech.create(
            model=model_id,
            voice=voice_name,
            input=text,
            speed=speed,
            response_format=output_format,  # type: ignore[arg-type]
            **{**self._kwargs, **kwargs},  # type: ignore[arg-type]
        )
        mime = "audio/mpeg" if output_format == "mp3" else f"audio/{output_format}"
        return resp.content, model_id, mime
