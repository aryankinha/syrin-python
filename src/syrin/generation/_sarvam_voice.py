"""Sarvam AI TTS provider. Requires sarvam-ai package.

Specialized in Indian languages. 11 languages, Bulbul v3 model.
"""

from __future__ import annotations

from syrin.generation._base_voice import BaseVoiceProvider


class SarvamVoiceProvider(BaseVoiceProvider):
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
        **kwargs: object,
    ) -> None:
        super().__init__(api_key=api_key, model=model, **kwargs)
        self.voice = voice
        self.language = language

    def _get_api_key_env(self) -> str:
        return "SARVAM_API_KEY"

    def _get_package_name(self) -> str:
        return "syrin[voice-sarvam]"

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
        from sarvam import Sarvam  # type: ignore[import-not-found]

        voice_name = voice_id if voice_id != "default" else self.voice
        lang = language if language != "en" else self.language
        client = Sarvam(api_key=api_key)
        response = client.tts.generate(
            text=text,
            voice=voice_name,
            language=lang,
            model=model_id,
            **{**self._kwargs, **kwargs},
        )
        content_bytes = response if isinstance(response, bytes) else bytes(response)
        return content_bytes, "bulbul:v3", "audio/mpeg"
