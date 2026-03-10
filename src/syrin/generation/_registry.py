"""Provider registry for image, video, and voice generation.

Holds _IMAGE_PROVIDERS, _VIDEO_PROVIDERS, _VOICE_PROVIDERS so config classes
can access them without circular imports.
"""

from __future__ import annotations

from typing import Any

from syrin.generation._cartesia_voice import CartesiaVoiceProvider
from syrin.generation._deepgram_voice import DeepgramVoiceProvider
from syrin.generation._elevenlabs_voice import ElevenLabsVoiceProvider
from syrin.generation._gemini import GeminiImageProvider, GeminiVideoProvider
from syrin.generation._openai import DalleImageProvider
from syrin.generation._openai_voice import OpenAIVoiceProvider
from syrin.generation._protocols import (
    ImageGenerationProvider,
    VideoGenerationProvider,
    VoiceGenerationProvider,
)
from syrin.generation._sarvam_voice import SarvamVoiceProvider

_IMAGE_PROVIDERS: dict[str, type[ImageGenerationProvider]] = {
    "gemini": GeminiImageProvider,
    "dalle": DalleImageProvider,
}
_VIDEO_PROVIDERS: dict[str, type[VideoGenerationProvider]] = {
    "gemini": GeminiVideoProvider,
}


def register_image_provider(name: str, cls: type[ImageGenerationProvider]) -> None:
    """Register an image generation provider. After registration, use ImageGenerator.Leonardo() etc."""
    _IMAGE_PROVIDERS[name.lower()] = cls


def register_video_provider(name: str, cls: type[VideoGenerationProvider]) -> None:
    """Register a video generation provider. After registration, use VideoGenerator.Leonardo() etc."""
    _VIDEO_PROVIDERS[name.lower()] = cls


def get_image_provider(
    name: str = "gemini",
    **kwargs: Any,
) -> ImageGenerationProvider:
    """Create an image provider instance by registered name."""
    cls = _IMAGE_PROVIDERS.get(name.lower())
    if cls is None:
        raise ValueError(
            f"Unknown image provider: {name!r}. Registered: {sorted(_IMAGE_PROVIDERS)}. "
            "Use register_image_provider() to add custom providers."
        )
    return cls(**kwargs)


def get_video_provider(
    name: str = "gemini",
    **kwargs: Any,
) -> VideoGenerationProvider:
    """Create a video provider instance by registered name."""
    cls = _VIDEO_PROVIDERS.get(name.lower())
    if cls is None:
        raise ValueError(
            f"Unknown video provider: {name!r}. Registered: {sorted(_VIDEO_PROVIDERS)}. "
            "Use register_video_provider() to add custom providers."
        )
    return cls(**kwargs)


def is_image_provider_registered(name: str) -> bool:
    """Return True if an image provider is registered under this name."""
    return name.lower() in _IMAGE_PROVIDERS


def is_video_provider_registered(name: str) -> bool:
    """Return True if a video provider is registered under this name."""
    return name.lower() in _VIDEO_PROVIDERS


_VOICE_PROVIDERS: dict[str, type[VoiceGenerationProvider]] = {
    "openai": OpenAIVoiceProvider,
    "elevenlabs": ElevenLabsVoiceProvider,
    "deepgram": DeepgramVoiceProvider,
    "cartesia": CartesiaVoiceProvider,
    "sarvam": SarvamVoiceProvider,
}


def register_voice_provider(name: str, cls: type[VoiceGenerationProvider]) -> None:
    """Register a voice generation provider. Use VoiceGenerator.Custom() after."""
    _VOICE_PROVIDERS[name.lower()] = cls


def get_voice_provider(
    name: str = "openai",
    **kwargs: Any,
) -> VoiceGenerationProvider:
    """Create a voice provider instance by registered name."""
    cls = _VOICE_PROVIDERS.get(name.lower())
    if cls is None:
        raise ValueError(
            f"Unknown voice provider: {name!r}. Registered: {sorted(_VOICE_PROVIDERS)}. "
            "Use register_voice_provider() to add custom providers."
        )
    return cls(**kwargs)


def is_voice_provider_registered(name: str) -> bool:
    """Return True if a voice provider is registered under this name."""
    return name.lower() in _VOICE_PROVIDERS
