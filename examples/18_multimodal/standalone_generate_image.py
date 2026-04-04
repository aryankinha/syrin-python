"""Standalone image generation — generate_image() without an agent.

Uses Google Gemini Imagen. No agent or tools; just call generate_image().
Requires: pip install syrin[generation], GOOGLE_API_KEY (or GEMINI_API_KEY).

Run:
    python -m examples.18_multimodal.standalone_generate_image

Covers: GenerationResult, aspect_ratio, optional save to file, error when key missing.
"""

from __future__ import annotations

import os
from pathlib import Path

from syrin import GenerationResult, generate_image


def main() -> None:
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("No GOOGLE_API_KEY / GEMINI_API_KEY set. Demonstrating error handling.")
        results = generate_image("a sunset over mountains", api_key=None)
        result = results[0] if results else None
        assert result is not None and isinstance(result, GenerationResult)
        print(f"  success={result.success}, error={result.error}")
        return

    # Single image, default 1:1
    prompt = "a minimalist logo of a blue bird on white background"
    result = generate_image(prompt, api_key=api_key)
    if isinstance(result, list):
        result = result[0] if result else None
    if not result:
        print("No result returned.")
        return
    if not result.success:
        print(f"Generation failed: {result.error}")
        return
    print(f"Success: content_type={result.content_type}, url length={len(result.url or '')} chars")
    if result.url and result.url.startswith("data:"):
        print("  (data URL with base64 image)")

    # With aspect_ratio string
    result_wide = generate_image(
        "a wide landscape with mountains",
        api_key=api_key,
        aspect_ratio="16:9",
    )
    if isinstance(result_wide, list):
        result_wide = result_wide[0] if result_wide else None
    if result_wide and result_wide.success:
        print("  16:9 image generated successfully")

    # Optional: save to file (if you have a valid result)
    out_path = Path(__file__).resolve().parent / "out_image.png"
    if result and result.success and result.content_bytes:
        out_path.write_bytes(result.content_bytes)
        print(f"  Saved to {out_path}")


if __name__ == "__main__":
    main()
