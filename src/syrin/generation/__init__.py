"""Image and video generation via Google Gemini (Imagen, Veo).

Uses the Gemini API (google-genai SDK). Set GOOGLE_API_KEY or pass api_key.

Optional dependency: pip install syrin[generation] or pip install google-genai

Declarative usage with Agent: set output_media to include Media.IMAGE and/or Media.VIDEO.
The agent adds generate_image/generate_video tools when GOOGLE_API_KEY (or a Google model key) is available.
Standalone: use generate_image(), generate_video(), or ImageGenerator/VideoGenerator directly.

Provider registry: register_image_provider(), register_video_provider() for DALL·E, Stability, etc.
"""

from __future__ import annotations

from typing import Any

from syrin.enums import AspectRatio, OutputMimeType, VoiceOutputFormat
from syrin.generation._gemini import GeminiImageProvider, GeminiVideoProvider
from syrin.generation._openai import DalleImageProvider
from syrin.generation._registry import (
    get_image_provider,
    get_video_provider,
    get_voice_provider,
    is_voice_provider_registered,
    register_image_provider,
    register_video_provider,
    register_voice_provider,
)
from syrin.generation._result import GenerationResult
from syrin.generation.config import ImageGenerator, VideoGenerator, VoiceGenerator

__all__ = [
    "AspectRatio",
    "DalleImageProvider",
    "GenerationResult",
    "GeminiImageProvider",
    "GeminiVideoProvider",
    "ImageGenerator",
    "OutputMimeType",
    "VideoGenerator",
    "generate_image",
    "generate_video",
    "generate_video_async",
    "get_default_image_generator",
    "get_default_video_generator",
    "get_image_provider",
    "get_video_provider",
    "register_image_provider",
    "register_video_provider",
    "VoiceGenerator",
    "get_voice_provider",
    "register_voice_provider",
    "is_voice_provider_registered",
    "VoiceOutputFormat",
]


def generate_image(
    prompt: str,
    *,
    api_key: str | None = None,
    model: str = "imagen-4.0-generate-001",
    number_of_images: int = 1,
    aspect_ratio: str = "1:1",
    output_mime_type: str = "image/png",
    **kwargs: Any,
) -> list[GenerationResult]:
    """Generate image(s) from a text prompt using Google Gemini (Imagen).

    Requires google-genai. Install with: pip install syrin[generation]

    Args:
        prompt: Text description of the image to generate.
        api_key: Gemini/Google API key. Defaults to GOOGLE_API_KEY.
        model: Imagen model (e.g. imagen-4.0-generate-001).
        number_of_images: Number of images to generate (1–4).
        aspect_ratio: 1:1, 3:4, 4:3, 9:16, 16:9.
        output_mime_type: image/png or image/jpeg.
        **kwargs: Passed to GenerateImagesConfig (e.g. negative_prompt).

    Returns:
        List of GenerationResult (one per image). Use results[0] for single image.
    """
    try:
        from syrin.generation._gemini import _generate_images_impl
    except ImportError as e:
        return [
            GenerationResult(
                success=False,
                error=f"Image generation requires google-genai. Install with: pip install syrin[generation]. {e!s}",
            )
        ]
    try:
        out = _generate_images_impl(
            prompt=prompt,
            api_key=api_key,
            model=model,
            number_of_images=number_of_images,
            aspect_ratio=aspect_ratio,
            output_mime_type=output_mime_type,
            **kwargs,
        )
        return out if isinstance(out, list) else [out]
    except ValueError as e:
        return [GenerationResult(success=False, error=str(e))]
    except ImportError as e:
        return [
            GenerationResult(
                success=False,
                error=f"Image generation requires google-genai. pip install syrin[generation]. {e!s}",
            )
        ]


def generate_video(
    prompt: str,
    *,
    api_key: str | None = None,
    model: str = "veo-2.0-generate-001",
    aspect_ratio: str = "16:9",
    poll_interval_seconds: float = 10.0,
    poll_timeout_seconds: float = 300.0,
    **kwargs: Any,
) -> GenerationResult:
    """Generate a short video from a text prompt using Google Gemini (Veo).

    Requires google-genai. Install with: pip install syrin[generation]

    Video generation is asynchronous; this function polls until complete or timeout.

    Args:
        prompt: Text description of the video to generate.
        api_key: Gemini/Google API key. Defaults to GOOGLE_API_KEY.
        model: Veo model (e.g. veo-2.0-generate-001).
        aspect_ratio: 16:9 or 9:16.
        poll_interval_seconds: Seconds between status polls.
        poll_timeout_seconds: Max wait time for completion.
        **kwargs: Passed to video generation config.

    Returns:
        GenerationResult with url (data URL) or content_bytes and content_type.
    """
    try:
        from syrin.generation._gemini import _generate_video_impl
    except ImportError as e:
        return GenerationResult(
            success=False,
            error=f"Video generation requires google-genai. Install with: pip install syrin[generation]. {e!s}",
        )
    try:
        return _generate_video_impl(
            prompt=prompt,
            api_key=api_key,
            model=model,
            aspect_ratio=aspect_ratio,
            poll_interval_seconds=poll_interval_seconds,
            poll_timeout_seconds=poll_timeout_seconds,
            **kwargs,
        )
    except ValueError as e:
        return GenerationResult(success=False, error=str(e))
    except ImportError as e:
        return GenerationResult(
            success=False,
            error=f"Video generation requires google-genai. pip install syrin[generation]. {e!s}",
        )


async def generate_video_async(
    prompt: str,
    *,
    api_key: str | None = None,
    model: str = "veo-2.0-generate-001",
    aspect_ratio: str = "16:9",
    poll_interval_seconds: float = 10.0,
    poll_timeout_seconds: float = 300.0,
    **kwargs: Any,
) -> GenerationResult:
    """Async video generation. Uses asyncio.sleep — does not block the event loop.

    Use from async code (e.g. FastAPI, async agents). The sync generate_video() blocks.
    """
    try:
        from syrin.generation._gemini import _generate_video_impl_async
    except ImportError as e:
        return GenerationResult(
            success=False,
            error=f"Video generation requires google-genai. Install with: pip install syrin[generation]. {e!s}",
        )
    try:
        return await _generate_video_impl_async(
            prompt=prompt,
            api_key=api_key,
            model=model,
            aspect_ratio=aspect_ratio,
            poll_interval_seconds=poll_interval_seconds,
            poll_timeout_seconds=poll_timeout_seconds,
            **kwargs,
        )
    except ValueError as e:
        return GenerationResult(success=False, error=str(e))


def get_default_image_generator(api_key: str | None = None) -> ImageGenerator | None:
    """Return a default ImageGenerator (Gemini Imagen).

    Use when generation=True on Agent (framework calls this) or for standalone use.
    Returns None if api_key is missing. The developer must pass api_key or set
    GOOGLE_API_KEY/GEMINI_API_KEY in the environment before calling.
    """
    import os

    raw = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    key = raw.strip() if isinstance(raw, str) else None
    if not key:
        return None
    return ImageGenerator(provider=GeminiImageProvider(api_key=key))


def get_default_video_generator(api_key: str | None = None) -> VideoGenerator | None:
    """Return a default VideoGenerator (Gemini Veo).

    Returns None if api_key is missing. The developer must pass api_key or set
    GOOGLE_API_KEY/GEMINI_API_KEY in the environment before calling.
    """
    import os

    raw = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    key = raw.strip() if isinstance(raw, str) else None
    if not key:
        return None
    return VideoGenerator(provider=GeminiVideoProvider(api_key=key))
