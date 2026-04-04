"""Agent that accepts file uploads: Media.FILE + InputFileRules.

When input_media includes Media.FILE, you must provide input_file_rules with
allowed_mime_types (and optional max_size_mb). Use for agents that accept PDFs,
documents, or specific image types with size limits.

Run:
    python -m examples.18_multimodal.agent_file_input_rules

Covers: Media.FILE, InputFileRules, allowed_mime_types, max_size_mb, validation.
"""

from __future__ import annotations

from syrin import Agent, Model
from syrin.capabilities import InputFileRules
from syrin.enums import Media


def main() -> None:
    # Rules: allow PDF and images, max 10 MB
    file_rules = InputFileRules(
        allowed_mime_types=["application/pdf", "image/png", "image/jpeg"],
        max_size_mb=10.0,
    )

    agent = Agent(
        model=Model.mock(latency_min=0, latency_max=0),
        system_prompt="You accept PDF and image uploads. Summarize or describe them.",
        input_media={Media.TEXT, Media.FILE},
        output_media={Media.TEXT},
        input_file_rules=file_rules,
    )

    print("Agent with file upload support:")
    print("  input_media:", sorted(m.value for m in agent._input_media))
    print("  input_file_rules.allowed_mime_types:", agent._input_file_rules.allowed_mime_types)
    print("  input_file_rules.max_size_mb:", agent._input_file_rules.max_size_mb)
    print("  allows image/png:", agent._input_file_rules.allows("image/png"))
    print("  allows text/plain:", agent._input_file_rules.allows("text/plain"))

    # Demonstrate validation: FILE in input_media without rules would raise
    try:
        Agent(
            model=Model.mock(),
            system_prompt="x",
            input_media={Media.TEXT, Media.FILE},
            # missing input_file_rules
        )
    except ValueError as e:
        print("\nValidation (FILE without input_file_rules):", str(e)[:80] + "...")


if __name__ == "__main__":
    main()
