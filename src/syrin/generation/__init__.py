"""Public generation package facade.

This package exposes image, video, and voice generation helpers, provider
registries, and generator types. Import from ``syrin.generation`` for the
public multimodal generation API.
"""

from syrin.generation._core import (
    AspectRatio,
    DalleImageProvider,
    GeminiImageProvider,
    GeminiVideoProvider,
    GenerationResult,
    ImageGenerator,
    OutputMimeType,
    VideoGenerator,
    VoiceGenerator,
    VoiceOutputFormat,
    generate_image,
    generate_video,
    generate_video_async,
    get_default_image_generator,
    get_default_video_generator,
    get_image_provider,
    get_video_provider,
    get_voice_provider,
    is_voice_provider_registered,
    register_image_provider,
    register_video_provider,
    register_voice_provider,
)

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
