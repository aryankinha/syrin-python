"""Public response package facade.

This package exposes the response objects returned by Syrin agent runs and
streams. Import from ``syrin.response`` when you need the main ``Response``
type, structured-output helpers, stream chunks, media attachments, or the
report models attached to responses.

Why use this package:
    - Work with the canonical response shape returned by ``Agent.run()``.
    - Inspect budget, guardrail, memory, grounding, and checkpoint reports.
    - Handle streaming deltas and multimodal attachments in a stable API.

Typical usage:
    >>> from syrin.response import Response
    >>> result: Response[str] = agent.run("Hello")
    >>> print(result.content)

Exported surface:
    - ``Response`` for the main run result
    - report models used across observability and post-run inspection
    - structured output and streaming helpers
"""

from syrin.response._core import (
    AgentReport,
    BudgetStatus,
    CheckpointReport,
    ContextReport,
    GroundingReport,
    GuardrailReport,
    MediaAttachment,
    MemoryReport,
    OutputReport,
    RateLimitReport,
    Response,
    StreamChunk,
    StructuredOutput,
    TokenReport,
    TraceStep,
)

__all__ = [
    "MediaAttachment",
    "StructuredOutput",
    "TraceStep",
    "Response",
    "BudgetStatus",
    "GuardrailReport",
    "GroundingReport",
    "ContextReport",
    "MemoryReport",
    "TokenReport",
    "OutputReport",
    "RateLimitReport",
    "CheckpointReport",
    "AgentReport",
    "StreamChunk",
]

_ = StreamChunk
