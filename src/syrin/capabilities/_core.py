"""Agent capabilities: input/output media and file rules.

Declarative config for what an agent can receive (input_media, input_file_rules)
and produce (output_media). Used for validation, discovery, and wiring generation tools.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class InputFileRules:
    """Rules for file uploads when Media.FILE is in agent input_media.

    Attributes:
        allowed_mime_types: MIME types accepted (e.g. image/png, application/pdf).
            Empty list = no files allowed (invalid when FILE in input_media).
        max_size_mb: Max file size in MB. Must be positive.
    """

    allowed_mime_types: list[str]
    max_size_mb: float = 10.0

    def __post_init__(self) -> None:
        if not isinstance(self.allowed_mime_types, list):
            raise TypeError(
                "InputFileRules.allowed_mime_types must be a list of MIME type strings."
            )
        if self.max_size_mb <= 0:
            raise ValueError(f"InputFileRules.max_size_mb must be > 0; got {self.max_size_mb!r}.")

    def allows(self, mime_type: str) -> bool:
        """Return True if the given MIME type is allowed."""
        return mime_type.strip().lower() in {m.strip().lower() for m in self.allowed_mime_types}


__all__ = ["InputFileRules"]
