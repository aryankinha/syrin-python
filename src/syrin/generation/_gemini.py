"""Google Gemini (Imagen, Veo) implementation for image and video generation."""

from __future__ import annotations

import asyncio
import base64
import os
import time

from syrin.cost import calculate_image_cost, calculate_video_cost
from syrin.generation._result import GenerationResult


def _get_api_key(api_key: str | None = None) -> str:
    key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError(
            "Gemini API key required. Set GOOGLE_API_KEY or GEMINI_API_KEY, or pass api_key=..."
        )
    return key


def _get_client(api_key: str | None = None) -> object:
    from google import genai

    return genai.Client(api_key=_get_api_key(api_key))


def _image_to_data_url(image: object, mime: str = "image/png") -> tuple[str, bytes]:
    """Extract bytes from a generated image and return (data_url, bytes)."""
    raw: bytes
    if hasattr(image, "image_bytes") and image.image_bytes:
        raw = (
            image.image_bytes
            if isinstance(image.image_bytes, bytes)
            else base64.b64decode(image.image_bytes)
        )
    elif hasattr(image, "save"):
        import io

        buf = io.BytesIO()
        image.save(buf, format="PNG" if "png" in mime else "JPEG")
        raw = buf.getvalue()
    else:
        raw = getattr(image, "data", b"") or b""
    mime = getattr(image, "mime_type", None) or mime
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}", raw


def _generate_images_impl(
    prompt: str,
    *,
    api_key: str | None = None,
    model: str = "imagen-4.0-generate-001",
    number_of_images: int = 1,
    aspect_ratio: str = "1:1",
    output_mime_type: str = "image/png",
    **kwargs: object,
) -> GenerationResult | list[GenerationResult]:
    from google.genai import types

    client = _get_client(api_key)
    config = types.GenerateImagesConfig(
        number_of_images=number_of_images,
        aspect_ratio=aspect_ratio,
        output_mime_type=output_mime_type,
        **{  # type: ignore[arg-type]
            k: v
            for k, v in kwargs.items()
            if k in ("negative_prompt", "person_generation", "safety_filter_level")
        },
    )
    try:
        response = client.models.generate_images(  # type: ignore[attr-defined]
            model=model,
            prompt=prompt,
            config=config,
        )
    except Exception as e:
        return GenerationResult(success=False, error=str(e))

    results: list[GenerationResult] = []
    for gen in getattr(response, "generated_images", []) or []:
        img = getattr(gen, "image", None)
        if img is None:
            results.append(GenerationResult(success=False, error="No image in response"))
            continue
        try:
            mime = getattr(img, "mime_type", None) or output_mime_type
            data_url, content_bytes = _image_to_data_url(img, mime)
            cost_usd = calculate_image_cost(model, number_of_images=1)
            results.append(
                GenerationResult(
                    success=True,
                    url=data_url,
                    content_type=mime,
                    content_bytes=content_bytes,
                    metadata={
                        "cost_usd": cost_usd,
                        "model_name": model,
                    },
                )
            )
        except Exception as e:
            results.append(GenerationResult(success=False, error=str(e)))

    return results


def _generate_video_impl(
    prompt: str,
    *,
    api_key: str | None = None,
    model: str = "veo-2.0-generate-001",
    aspect_ratio: str = "16:9",
    poll_interval_seconds: float = 10.0,
    poll_timeout_seconds: float = 300.0,
    **kwargs: object,
) -> GenerationResult:
    from google.genai import types

    client = _get_client(api_key)
    config = types.GenerateVideosConfig(
        aspect_ratio=aspect_ratio,
        **{k: v for k, v in kwargs.items() if k in ("number_of_videos",)},  # type: ignore[arg-type]
    )
    try:
        operation = client.models.generate_videos(  # type: ignore[attr-defined]
            model=model,
            prompt=prompt,
            config=config,
        )
    except Exception as e:
        return GenerationResult(success=False, error=str(e))

    deadline = time.monotonic() + poll_timeout_seconds
    while time.monotonic() < deadline:
        if getattr(operation, "done", False):
            break
        try:
            operation = client.operations.get(operation)  # type: ignore[attr-defined]
        except Exception as e:
            return GenerationResult(success=False, error=str(e))
        time.sleep(poll_interval_seconds)

    if not getattr(operation, "done", False):
        return GenerationResult(success=False, error="Video generation timed out")

    err = getattr(operation, "error", None)
    if err:
        return GenerationResult(success=False, error=str(err))

    response = getattr(operation, "response", None)
    if not response:
        return GenerationResult(success=False, error="No response in operation")

    generated = getattr(response, "generated_videos", []) or []
    if not generated:
        return GenerationResult(success=False, error="No video in response")

    video = generated[0]
    v = getattr(video, "video", None)
    if v is None:
        return GenerationResult(success=False, error="No video data")

    try:
        raw: bytes
        if hasattr(v, "video_bytes") and v.video_bytes:
            raw = (
                v.video_bytes
                if isinstance(v.video_bytes, bytes)
                else base64.b64decode(v.video_bytes)
            )
        elif hasattr(v, "uri") and getattr(v, "uri", None):
            try:
                raw = client.files.download(file=v)  # type: ignore[attr-defined]
            except Exception as e:
                return GenerationResult(
                    success=False, error=f"Failed to download remote video: {e}"
                )
        else:
            raw = getattr(v, "data", b"") or b""
        if not raw:
            return GenerationResult(success=False, error="Empty video data")
        mime = getattr(v, "mime_type", None) or "video/mp4"
        b64 = base64.b64encode(raw).decode("ascii")
        data_url = f"data:{mime};base64,{b64}"
        cost_usd = calculate_video_cost(model)
        return GenerationResult(
            success=True,
            url=data_url,
            content_type=mime,
            content_bytes=raw,
            metadata={
                "cost_usd": cost_usd,
                "model_name": model,
            },
        )
    except Exception as e:
        return GenerationResult(success=False, error=str(e))


async def _generate_video_impl_async(
    prompt: str,
    *,
    api_key: str | None = None,
    model: str = "veo-2.0-generate-001",
    aspect_ratio: str = "16:9",
    poll_interval_seconds: float = 10.0,
    poll_timeout_seconds: float = 300.0,
    **kwargs: object,
) -> GenerationResult:
    """Async video generation. Uses asyncio.sleep — does not block the event loop."""
    from google.genai import types

    client = _get_client(api_key)
    config = types.GenerateVideosConfig(
        aspect_ratio=aspect_ratio,
        **{k: v for k, v in kwargs.items() if k in ("number_of_videos",)},  # type: ignore[arg-type]
    )
    try:
        operation = client.models.generate_videos(  # type: ignore[attr-defined]
            model=model,
            prompt=prompt,
            config=config,
        )
    except Exception as e:
        return GenerationResult(success=False, error=str(e))

    deadline = time.monotonic() + poll_timeout_seconds
    while time.monotonic() < deadline:
        if getattr(operation, "done", False):
            break
        try:
            operation = client.operations.get(operation)  # type: ignore[attr-defined]
        except Exception as e:
            return GenerationResult(success=False, error=str(e))
        await asyncio.sleep(poll_interval_seconds)

    if not getattr(operation, "done", False):
        return GenerationResult(success=False, error="Video generation timed out")

    err = getattr(operation, "error", None)
    if err:
        return GenerationResult(success=False, error=str(err))

    response = getattr(operation, "response", None)
    if not response:
        return GenerationResult(success=False, error="No response in operation")

    generated = getattr(response, "generated_videos", []) or []
    if not generated:
        return GenerationResult(success=False, error="No video in response")

    video = generated[0]
    v = getattr(video, "video", None)
    if v is None:
        return GenerationResult(success=False, error="No video data")

    try:
        raw: bytes
        if hasattr(v, "video_bytes") and v.video_bytes:
            raw = (
                v.video_bytes
                if isinstance(v.video_bytes, bytes)
                else base64.b64decode(v.video_bytes)
            )
        elif hasattr(v, "uri") and getattr(v, "uri", None):
            try:
                raw = client.files.download(file=v)  # type: ignore[attr-defined]
            except Exception as e:
                return GenerationResult(
                    success=False, error=f"Failed to download remote video: {e}"
                )
        else:
            raw = getattr(v, "data", b"") or b""
        if not raw:
            return GenerationResult(success=False, error="Empty video data")
        mime = getattr(v, "mime_type", None) or "video/mp4"
        b64 = base64.b64encode(raw).decode("ascii")
        data_url = f"data:{mime};base64,{b64}"
        cost_usd = calculate_video_cost(model)
        return GenerationResult(
            success=True,
            url=data_url,
            content_type=mime,
            content_bytes=raw,
            metadata={
                "cost_usd": cost_usd,
                "model_name": model,
            },
        )
    except Exception as e:
        return GenerationResult(success=False, error=str(e))


class GeminiImageProvider:
    """Image generation via Google Gemini (Imagen). Implements ImageGenerationProvider.

    Use with ImageGenerator(provider=GeminiImageProvider(api_key=...)) or
    let Agent create it when generation=True and a Google model/key is available.

    Attributes:
        api_key: Gemini/Google API key. None = use GOOGLE_API_KEY or GEMINI_API_KEY.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

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
        """Generate image(s). Returns list of GenerationResult (one per image)."""
        out = _generate_images_impl(
            prompt,
            api_key=self.api_key,
            model=model or "imagen-4.0-generate-001",
            number_of_images=number_of_images,
            aspect_ratio=aspect_ratio,
            output_mime_type=output_mime_type,
            **kwargs,
        )
        if isinstance(out, list):
            return out
        return [out]


class GeminiVideoProvider:
    """Video generation via Google Gemini (Veo). Implements VideoGenerationProvider.

    Use with VideoGenerator(provider=GeminiVideoProvider(api_key=...)) or
    let Agent create it when generation=True and a Google model/key is available.

    Attributes:
        api_key: Gemini/Google API key. None = use GOOGLE_API_KEY or GEMINI_API_KEY.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    def generate(
        self,
        prompt: str,
        *,
        aspect_ratio: str = "16:9",
        model: str | None = None,
        poll_interval_seconds: float = 10.0,
        poll_timeout_seconds: float = 300.0,
        **kwargs: object,
    ) -> GenerationResult:
        """Generate a short video (sync). Polls with time.sleep. Use generate_async for async."""
        return _generate_video_impl(
            prompt,
            api_key=self.api_key,
            model=model or "veo-2.0-generate-001",
            aspect_ratio=aspect_ratio,
            poll_interval_seconds=poll_interval_seconds,
            poll_timeout_seconds=poll_timeout_seconds,
            **kwargs,
        )

    async def generate_async(
        self,
        prompt: str,
        *,
        aspect_ratio: str = "16:9",
        model: str | None = None,
        poll_interval_seconds: float = 10.0,
        poll_timeout_seconds: float = 300.0,
        **kwargs: object,
    ) -> GenerationResult:
        """Generate a short video (async). Uses asyncio.sleep — does not block event loop."""
        return await _generate_video_impl_async(
            prompt,
            api_key=self.api_key,
            model=model or "veo-2.0-generate-001",
            aspect_ratio=aspect_ratio,
            poll_interval_seconds=poll_interval_seconds,
            poll_timeout_seconds=poll_timeout_seconds,
            **kwargs,
        )
