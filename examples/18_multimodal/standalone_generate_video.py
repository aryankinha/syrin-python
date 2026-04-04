"""Standalone video generation — generate_video() without an agent.

Uses Google Gemini Veo. No agent or tools; just call generate_video().
Video generation is async on the API; the function polls until done or timeout.
Requires: pip install syrin[generation], GOOGLE_API_KEY (or GEMINI_API_KEY).

Run:
    python -m examples.18_multimodal.standalone_generate_video

Covers: GenerationResult, polling, aspect_ratio, error when key missing.
"""

from __future__ import annotations

import os
from pathlib import Path

from syrin import GenerationResult, generate_video


def main() -> None:
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("No GOOGLE_API_KEY / GEMINI_API_KEY set. Demonstrating error handling.")
        result = generate_video("a cat walking", api_key=None)
        print(f"  success={result.success}, error={result.error}")
        return

    # Short prompt; Veo may take a minute or more
    prompt = "a golden retriever running through a sunny field, 3 seconds"
    print("Calling generate_video (this may take 1-2 minutes)...")
    result = generate_video(
        prompt,
        api_key=api_key,
        aspect_ratio="16:9",
        poll_interval_seconds=10.0,
        poll_timeout_seconds=300.0,
    )
    if not isinstance(result, GenerationResult):
        print("Unexpected result type.")
        return
    if not result.success:
        print(f"Generation failed: {result.error}")
        return
    print(f"Success: content_type={result.content_type}")
    if result.url and result.url.startswith("data:"):
        print("  (data URL with base64 video)")
    if result.content_bytes:
        out_path = Path(__file__).resolve().parent / "out_video.mp4"
        out_path.write_bytes(result.content_bytes)
        print(f"  Saved to {out_path}")


if __name__ == "__main__":
    main()
