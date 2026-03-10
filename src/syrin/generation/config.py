"""Declarative config for image and video generation.

ImageGenerator and VideoGenerator hold provider and options. Use standalone or
via Agent: set output_media={Media.IMAGE, Media.VIDEO} for defaults, or pass
image_generation=ImageGenerator(...) / video_generation=VideoGenerator(...) explicitly.

Static constructors (like Model.OpenAI):
    ImageGenerator.Gemini(api_key=...)  # Google Imagen
    ImageGenerator.DALLE(api_key=...)    # OpenAI DALL·E 3
    VideoGenerator.Gemini(api_key=...)   # Google Veo

Registered custom providers (ImageGenerator.Leonardo after register_image_provider):
    from syrin.generation import register_image_provider, ImageGenerator
    register_image_provider("leonardo", LeonardoImageProvider)
    gen = ImageGenerator.Leonardo(api_key=...)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

# Avoid circular import; protocols are used for type hints only
from typing import TYPE_CHECKING, Any, cast

from syrin.enums import AspectRatio, Hook, OutputMimeType
from syrin.generation._protocols import ImageGenerationProvider, VideoGenerationProvider
from syrin.generation._result import GenerationResult

if TYPE_CHECKING:
    pass


def _image_provider_factory(provider_name: str) -> Callable[..., ImageGenerator]:
    """Return a callable that creates ImageGenerator with the given provider."""

    def _create(
        *,
        api_key: str | None = None,
        model: str | None = None,
        aspect_ratio: AspectRatio = AspectRatio.ONE_TO_ONE,
        number_of_images: int = 1,
        output_mime_type: OutputMimeType = OutputMimeType.IMAGE_PNG,
        **kwargs: Any,
    ) -> ImageGenerator:
        from syrin.generation._registry import get_image_provider

        prov = get_image_provider(provider_name, api_key=api_key, **kwargs)
        _default_model: str = "default"
        if provider_name == "gemini":
            _default_model = "imagen-4.0-generate-001"
        elif provider_name == "dalle":
            _default_model = "dall-e-3"
        return ImageGenerator(
            provider=prov,
            image_model=model or _default_model,
            aspect_ratio=aspect_ratio,
            number_of_images=number_of_images,
            output_mime_type=output_mime_type,
        )

    return _create


def _video_provider_factory(provider_name: str) -> Callable[..., VideoGenerator]:
    """Return a callable that creates VideoGenerator with the given provider."""

    def _create(
        *,
        api_key: str | None = None,
        model: str | None = None,
        aspect_ratio: AspectRatio = AspectRatio.SIXTEEN_NINE,
        poll_interval_seconds: float = 10.0,
        poll_timeout_seconds: float = 300.0,
        **kwargs: Any,
    ) -> VideoGenerator:
        from syrin.generation._registry import get_video_provider

        prov = get_video_provider(provider_name, api_key=api_key, **kwargs)
        _default_model: str = "veo-2.0-generate-001" if provider_name == "gemini" else "default"
        return VideoGenerator(
            provider=prov,
            video_model=model or _default_model,
            aspect_ratio=aspect_ratio,
            poll_interval_seconds=poll_interval_seconds,
            poll_timeout_seconds=poll_timeout_seconds,
        )

    return _create


class _ImageGeneratorMeta(type):
    """Metaclass for dynamic provider namespaces: ImageGenerator.Leonardo() when registered."""

    def __getattr__(cls, name: str) -> Any:
        from syrin.generation._registry import is_image_provider_registered

        provider_name = name.lower()
        if is_image_provider_registered(provider_name):
            return _image_provider_factory(provider_name)
        raise AttributeError(
            f"type object {cls.__name__!r} has no attribute {name!r}. "
            f"Register with register_image_provider({provider_name!r}, YourProvider) to use {cls.__name__}.{name}()"
        )


class _VideoGeneratorMeta(type):
    """Metaclass for dynamic provider namespaces: VideoGenerator.Leonardo() when registered."""

    def __getattr__(cls, name: str) -> Any:
        from syrin.generation._registry import is_video_provider_registered

        provider_name = name.lower()
        if is_video_provider_registered(provider_name):
            return _video_provider_factory(provider_name)
        raise AttributeError(
            f"type object {cls.__name__!r} has no attribute {name!r}. "
            f"Register with register_video_provider({provider_name!r}, YourProvider) to use {cls.__name__}.{name}()"
        )


@dataclass
class ImageGenerator(metaclass=_ImageGeneratorMeta):
    """Declarative image generation. Configure once, call generate(prompt).

    Example::

        # Built-in: Google (Gemini), OpenAI DALL·E
        gen = ImageGenerator.Gemini(api_key="...")
        gen = ImageGenerator.DALLE(api_key="...")
        results = gen.generate("a sunset over mountains")

        # After register_image_provider("leonardo", LeonardoImageProvider):
        gen = ImageGenerator.Leonardo(api_key="...")

    Attributes:
        provider: Backend that implements ImageGenerationProvider (e.g. GeminiImagen).
        aspect_ratio: Default aspect ratio. Overridable per generate() call.
        image_model: Image model ID (e.g. imagen-4.0-generate-001). Overridable per call.
        number_of_images: Default 1. Overridable per call.
        output_mime_type: Default output MIME type.
    """

    provider: ImageGenerationProvider
    aspect_ratio: AspectRatio = AspectRatio.ONE_TO_ONE
    image_model: str = "imagen-4.0-generate-001"
    number_of_images: int = 1
    output_mime_type: OutputMimeType = OutputMimeType.IMAGE_PNG

    @classmethod
    def from_provider(
        cls,
        name: str,
        *,
        api_key: str | None = None,
        model: str | None = None,
        aspect_ratio: AspectRatio = AspectRatio.ONE_TO_ONE,
        number_of_images: int = 1,
        output_mime_type: OutputMimeType = OutputMimeType.IMAGE_PNG,
        **kwargs: Any,
    ) -> ImageGenerator:
        """Create ImageGenerator from a registered provider by name.

        Use when the provider name is dynamic (e.g. from config).
        For static names use ImageGenerator.Gemini() or ImageGenerator.Leonardo().
        """
        result: ImageGenerator = _image_provider_factory(name.lower())(
            api_key=api_key,
            model=model,
            aspect_ratio=aspect_ratio,
            number_of_images=number_of_images,
            output_mime_type=output_mime_type,
            **kwargs,
        )
        return result

    def generate(
        self,
        prompt: str,
        *,
        aspect_ratio: AspectRatio | None = None,
        model: str | None = None,
        number_of_images: int | None = None,
        output_mime_type: OutputMimeType | None = None,
        emit: Callable[[str, dict[str, Any]], None] | None = None,
        **kwargs: Any,
    ) -> list[GenerationResult]:
        """Generate image(s) from a text prompt.

        Args:
            prompt: Text description of the image.
            aspect_ratio: Override default. None = use self.aspect_ratio.
            model: Override default image_model (for per-call override).
            number_of_images: Override default (1–4).
            output_mime_type: Override default MIME type.
            emit: Optional (hook_name, ctx) callback. Standalone use only; when generation
                runs via Agent tools, use agent.events.on(Hook.GENERATION_IMAGE_END, handler) instead.
            **kwargs: Passed to provider.

        Returns:
            List of GenerationResult (one per image). Never single result; list for consistent API.
        """
        ar = (aspect_ratio or self.aspect_ratio).value
        m = model or self.image_model
        n = number_of_images if number_of_images is not None else self.number_of_images
        mime = (output_mime_type or self.output_mime_type).value
        ctx: dict[str, Any] = {
            "prompt": prompt,
            "aspect_ratio": ar,
            "model": m,
            "number_of_images": n,
        }
        if emit:
            emit(Hook.GENERATION_IMAGE_START, ctx)
        try:
            results = self.provider.generate(
                prompt,
                aspect_ratio=ar,
                number_of_images=n,
                output_mime_type=mime,
                model=m,
                **kwargs,
            )
            if emit:
                emit(
                    Hook.GENERATION_IMAGE_END,
                    {**ctx, "results": results, "count": len(results)},
                )
            return results
        except Exception as e:
            if emit:
                emit(Hook.GENERATION_IMAGE_ERROR, {**ctx, "error": str(e)})
            return [GenerationResult(success=False, error=str(e))]


@dataclass
class VideoGenerator(metaclass=_VideoGeneratorMeta):
    """Declarative video generation. Configure once, call generate(prompt).

    Example::

        gen = VideoGenerator.Gemini(api_key="...")
        result = gen.generate("a dog running on the beach")

    Instantiate for standalone use or use get_default_video_generator(); Agent
    creates one when output_media includes Media.VIDEO.

    Attributes:
        provider: Backend that implements VideoGenerationProvider (e.g. GeminiVeo).
        aspect_ratio: Default aspect ratio.
        video_model: Video model ID (e.g. veo-2.0-generate-001).
        poll_interval_seconds: Seconds between status polls.
        poll_timeout_seconds: Max wait for completion.
    """

    provider: VideoGenerationProvider
    aspect_ratio: AspectRatio = AspectRatio.SIXTEEN_NINE
    video_model: str = "veo-2.0-generate-001"
    poll_interval_seconds: float = 10.0
    poll_timeout_seconds: float = 300.0

    @classmethod
    def from_provider(
        cls,
        name: str,
        *,
        api_key: str | None = None,
        model: str | None = None,
        aspect_ratio: AspectRatio = AspectRatio.SIXTEEN_NINE,
        poll_interval_seconds: float = 10.0,
        poll_timeout_seconds: float = 300.0,
        **kwargs: Any,
    ) -> VideoGenerator:
        """Create VideoGenerator from a registered provider by name.

        Use when the provider name is dynamic (e.g. from config).
        For static names use VideoGenerator.Gemini() or VideoGenerator.Leonardo().
        """
        result: VideoGenerator = _video_provider_factory(name.lower())(
            api_key=api_key,
            model=model,
            aspect_ratio=aspect_ratio,
            poll_interval_seconds=poll_interval_seconds,
            poll_timeout_seconds=poll_timeout_seconds,
            **kwargs,
        )
        return result

    def generate(
        self,
        prompt: str,
        *,
        aspect_ratio: AspectRatio | None = None,
        model: str | None = None,
        poll_interval_seconds: float | None = None,
        poll_timeout_seconds: float | None = None,
        emit: Callable[[str, dict[str, Any]], None] | None = None,
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate a short video from a text prompt.

        Args:
            prompt: Text description of the video.
            aspect_ratio: Override default.
            model: Override default video_model (for per-call override).
            poll_interval_seconds: Override default poll interval.
            poll_timeout_seconds: Override default timeout.
            emit: Optional (hook_name, ctx) callback. Standalone use only; when generation
                runs via Agent tools, use agent.events.on(Hook.GENERATION_VIDEO_END, handler) instead.
            **kwargs: Passed to provider.

        Returns:
            GenerationResult with url or content_bytes.
        """
        ar = (aspect_ratio or self.aspect_ratio).value
        m = model or self.video_model
        pi = (
            poll_interval_seconds
            if poll_interval_seconds is not None
            else self.poll_interval_seconds
        )
        pt = poll_timeout_seconds if poll_timeout_seconds is not None else self.poll_timeout_seconds
        ctx: dict[str, Any] = {
            "prompt": prompt,
            "aspect_ratio": ar,
            "model": m,
        }
        if emit:
            emit(Hook.GENERATION_VIDEO_START, ctx)
        try:
            result = self.provider.generate(
                prompt,
                aspect_ratio=ar,
                model=m,
                poll_interval_seconds=pi,
                poll_timeout_seconds=pt,
                **kwargs,
            )
            if emit:
                emit(Hook.GENERATION_VIDEO_END, {**ctx, "result": result})
            return result
        except Exception as e:
            if emit:
                emit(Hook.GENERATION_VIDEO_ERROR, {**ctx, "error": str(e)})
            return GenerationResult(success=False, error=str(e))

    async def generate_async(
        self,
        prompt: str,
        *,
        aspect_ratio: AspectRatio | None = None,
        model: str | None = None,
        poll_interval_seconds: float | None = None,
        poll_timeout_seconds: float | None = None,
        emit: Callable[[str, dict[str, Any]], None] | None = None,
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate video asynchronously. Uses asyncio.sleep — does not block event loop."""
        ar = (aspect_ratio or self.aspect_ratio).value
        m = model or self.video_model
        pi = (
            poll_interval_seconds
            if poll_interval_seconds is not None
            else self.poll_interval_seconds
        )
        pt = poll_timeout_seconds if poll_timeout_seconds is not None else self.poll_timeout_seconds
        ctx: dict[str, Any] = {"prompt": prompt, "aspect_ratio": ar, "model": m}
        if emit:
            emit(Hook.GENERATION_VIDEO_START, ctx)
        try:
            gen_async = getattr(self.provider, "generate_async", None)
            if gen_async is not None:
                result = await gen_async(
                    prompt,
                    aspect_ratio=ar,
                    model=m,
                    poll_interval_seconds=pi,
                    poll_timeout_seconds=pt,
                    **kwargs,
                )
            else:
                import asyncio

                result = await asyncio.to_thread(
                    self.provider.generate,
                    prompt,
                    aspect_ratio=ar,
                    model=m,
                    poll_interval_seconds=pi,
                    poll_timeout_seconds=pt,
                    **kwargs,
                )
            if emit:
                emit(Hook.GENERATION_VIDEO_END, {**ctx, "result": result})
            return cast(GenerationResult, result)
        except Exception as e:
            if emit:
                emit(Hook.GENERATION_VIDEO_ERROR, {**ctx, "error": str(e)})
            return GenerationResult(success=False, error=str(e))
