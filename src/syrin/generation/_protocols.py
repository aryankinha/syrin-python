"""Protocols for image, video, and voice generation providers.

Implement these to plug in different backends (Gemini, DALL·E, ElevenLabs, etc.).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from syrin.generation import GenerationResult


class ImageGenerationProvider(Protocol):
    """Protocol for image generation. Implement to add a new backend (e.g. Gemini, DALL·E)."""

    def generate(
        self,
        prompt: str,
        *,
        aspect_ratio: str = "1:1",
        number_of_images: int = 1,
        output_mime_type: str = "image/png",
        model: str | None = None,
        **kwargs: object,
    ) -> list[GenerationResult]:
        """Generate image(s) from a text prompt.

        Args:
            prompt: Text description of the image.
            aspect_ratio: Aspect ratio string (e.g. 1:1, 16:9).
            number_of_images: Number of images to generate (1–4).
            output_mime_type: MIME type for output (e.g. image/png).
            model: Optional model override.
            **kwargs: Provider-specific options.

        Returns:
            List of GenerationResult (one per image). Empty list on failure.
        """
        ...


class VideoGenerationProvider(Protocol):
    """Protocol for video generation. Implement to add a new backend (e.g. Gemini Veo).

    Polling params (poll_interval_seconds, poll_timeout_seconds) are Gemini-specific.
    Pass via **kwargs if your provider needs them.
    """

    def generate(
        self,
        prompt: str,
        *,
        aspect_ratio: str = "16:9",
        model: str | None = None,
        **kwargs: object,
    ) -> GenerationResult:
        """Generate a short video from a text prompt.

        Args:
            prompt: Text description of the video.
            aspect_ratio: Aspect ratio string (16:9 or 9:16).
            model: Optional model override.
            **kwargs: Provider-specific options (e.g. poll_interval_seconds for async).

        Returns:
            GenerationResult with url or content_bytes.
        """
        ...


class VoiceGenerationProvider(Protocol):
    """Protocol for text-to-speech providers. Implement for ElevenLabs, OpenAI, etc."""

    def generate(
        self,
        text: str,
        *,
        voice_id: str = "default",
        speed: float = 1.0,
        language: str = "en",
        **kwargs: object,
    ) -> GenerationResult:
        """Generate speech audio from text.

        Args:
            text: Text to speak.
            voice_id: Voice identifier (provider-specific).
            speed: Speech rate (e.g. 0.5–2.0).
            language: Language code (e.g. en, hi).
            **kwargs: Provider-specific options (output_format, etc.).

        Returns:
            GenerationResult with url (data URL) or content_bytes.
        """
        ...

    async def generate_async(
        self,
        text: str,
        *,
        voice_id: str = "default",
        speed: float = 1.0,
        language: str = "en",
        **kwargs: object,
    ) -> GenerationResult:
        """Async variant of generate."""
        ...
