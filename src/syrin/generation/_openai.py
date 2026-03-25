"""OpenAI image generation provider (DALL·E). Requires openai package."""

from __future__ import annotations

import base64

from syrin.cost import calculate_image_cost
from syrin.generation._result import GenerationResult

# Aspect ratio to DALL-E 3 size: 1:1 -> 1024x1024, 16:9 -> 1792x1024, 9:16 -> 1024x1792
_DALLE_ASPECT_TO_SIZE: dict[str, str] = {
    "1:1": "1024x1024",
    "16:9": "1792x1024",
    "9:16": "1024x1792",
    "4:3": "1792x1024",
    "3:4": "1024x1792",
}


class DalleImageProvider:
    """Image generation via OpenAI DALL·E 3. Implements ImageGenerationProvider.

    Requires: pip install openai. Set OPENAI_API_KEY or pass api_key=.

    Attributes:
        api_key: OpenAI API key. None = use OPENAI_API_KEY env.
    """

    def __init__(self, api_key: str | None = None, **kwargs: object) -> None:
        self.api_key = api_key
        self._kwargs = kwargs

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
        """Generate image(s) using DALL·E 3. number_of_images=1 for DALL-E 3 (API limit)."""
        try:
            from openai import OpenAI
        except ImportError as e:
            return [
                GenerationResult(
                    success=False,
                    error=f"DALL·E requires openai package. pip install openai. {e!s}",
                )
            ]
        import os

        key = self.api_key or os.environ.get("OPENAI_API_KEY")
        if not key or not str(key).strip():
            return [
                GenerationResult(
                    success=False,
                    error="DALL·E requires OPENAI_API_KEY or api_key=.",
                )
            ]
        size = _DALLE_ASPECT_TO_SIZE.get(aspect_ratio, "1024x1024")
        model_id = model or "dall-e-3"
        response_format = "b64_json" if "png" in output_mime_type.lower() else "b64_json"
        try:
            client = OpenAI(api_key=key)
            resp = client.images.generate(  # type: ignore[call-overload]
                prompt=prompt[:4000],
                model=model_id,
                n=min(number_of_images, 1),
                size=size,
                response_format=response_format,
                **{**self._kwargs, **kwargs},
            )
            results: list[GenerationResult] = []
            for data in getattr(resp, "data", []) or []:
                b64 = getattr(data, "b64_json", None)
                if b64:
                    raw = base64.b64decode(b64)
                    mime = "image/png" if "png" in output_mime_type.lower() else "image/png"
                    b64_url = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"
                    cost_usd = calculate_image_cost(model_id, number_of_images=1)
                    results.append(
                        GenerationResult(
                            success=True,
                            url=b64_url,
                            content_type=mime,
                            content_bytes=raw,
                            metadata={
                                "cost_usd": cost_usd,
                                "model_name": model_id,
                            },
                        )
                    )
            return results if results else [GenerationResult(success=False, error="No image data")]
        except Exception as e:
            return [GenerationResult(success=False, error=str(e))]
