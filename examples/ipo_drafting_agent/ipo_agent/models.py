"""Structured output models for DRHP Capital Structure section.

Uses Syrin @structured for schema generation; intermediate data is visible via --trace.
"""

from __future__ import annotations

from typing import Annotated

from syrin.model import structured


@structured
class DraftOutput:
    """Agent output: draft section and automation transparency metadata.

    All fields required for OpenAI strict schema; use empty lists where none.
    """

    draft_section: Annotated[
        str,
        "Draft DRHP section in paragraph-style legal disclosure language",
    ]
    sources_used: Annotated[list[str], "Source documents used for facts"]
    auto_extracted_parts: Annotated[list[str], "Parts auto-extracted from documents"]
    requires_review: Annotated[list[str], "Items requiring human review"]
