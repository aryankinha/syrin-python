"""Image generation with StrEnum options: AspectRatio and OutputMimeType.

Uses the standalone generate_image API with explicit aspect ratio and output
format. Shows the no-free-strings design: use AspectRatio and OutputMimeType
from syrin.enums (or syrin.generation).

Run:
    python -m examples.18_multimodal.generation_with_options

Requires: pip install syrin[generation], GOOGLE_API_KEY.
Covers: AspectRatio, OutputMimeType, standalone generate_image with options.
"""

from __future__ import annotations

import os

from syrin import generate_image
from syrin.enums import AspectRatio, OutputMimeType


def main() -> None:
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Set GOOGLE_API_KEY to run. Showing available options:")
        print("  AspectRatio:", [a.value for a in AspectRatio])
        print("  OutputMimeType:", [m.value for m in OutputMimeType])
        return

    # Use StrEnums for aspect ratio and output format (no free strings)
    result = generate_image(
        "a simple geometric pattern, blue and white",
        api_key=api_key,
        aspect_ratio=AspectRatio.SIXTEEN_NINE.value,
        output_mime_type=OutputMimeType.IMAGE_PNG.value,
    )
    if isinstance(result, list):
        result = result[0] if result else None
    if result and result.success:
        print("Generated with 16:9 aspect ratio, PNG format")
        print("  content_type:", result.content_type)
    else:
        err = result.error if result else "No result"
        print("Generation failed:", err)


if __name__ == "__main__":
    main()
