"""Langfuse exporter for AI-native observability.

Exports spans to Langfuse for production debugging, evaluation, and monitoring.

Example:
    >>> from syrin.observability.langfuse import LangfuseExporter
    >>>
    >>> exporter = LangfuseExporter(
    ...     public_key="pk-...",
    ...     secret_key="sk-...",
    ... )
    >>> trace.add_exporter(exporter)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from syrin.observability import Span, SpanExporter, SpanKind

_log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from langfuse import Langfuse

# Try to import langfuse, but make it optional
try:
    from langfuse import Langfuse

    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    Langfuse = None


class LangfuseExporter(SpanExporter):
    """Export spans to Langfuse for AI-native observability.

    Langfuse provides:
    - Tracing and debugging
    - Evaluation and quality monitoring
    - Prompt management
    - Cost analytics

    Requires: pip install langfuse

    Args:
        public_key: Langfuse public key
        secret_key: Langfuse secret key
        host: Langfuse host (for self-hosted)
        environment: Environment name (production, development)

    Example:
        >>> exporter = LangfuseExporter(
        ...     public_key="pk-...",
        ...     secret_key="sk-...",
        ... )
        >>> trace.add_exporter(exporter)
    """

    def __init__(
        self,
        public_key: str | None = None,
        secret_key: str | None = None,
        host: str | None = None,
        environment: str | None = None,
    ) -> None:
        if not LANGFUSE_AVAILABLE:
            raise ImportError("Langfuse not installed. Install with: pip install langfuse")

        self._langfuse = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
            environment=environment,
        )

    def export(self, span: Span) -> None:
        """Export span to Langfuse."""
        if not LANGFUSE_AVAILABLE:
            return

        try:
            # Only export root spans (agent runs) to Langfuse
            # as Langfuse handles the nesting automatically
            if span.parent_span_id is not None:
                return

            # Convert span to Langfuse trace
            self._export_trace(span)

        except Exception as e:
            _log.warning("Failed to export span to Langfuse: %s", e)

    def _export_trace(self, span: Span) -> None:
        """Export a trace to Langfuse."""
        generation = None

        # Find the LLM call to create a Langfuse generation
        for child in span.walk():
            if child.kind == SpanKind.LLM:
                generation = self._langfuse.generation(
                    name=child.name,
                    start_time=child.start_time,
                    end_time=child.end_time,
                    model=child.attributes.get("llm.model", ""),
                    input=child.attributes.get("llm.prompt", ""),
                    output=child.attributes.get("llm.completion", ""),
                    metadata={
                        "trace_id": span.trace_id,
                        "span_id": child.span_id,
                        **self._extract_metadata(child),
                    },
                )

                # Add token usage if available
                tokens_input = child.attributes.get("llm.tokens.input")
                tokens_output = child.attributes.get("llm.tokens.output")
                if (tokens_input or tokens_output) and generation:
                    generation.update(
                        usage={
                            "input": tokens_input or 0,
                            "output": tokens_output or 0,
                            "total": (tokens_input or 0) + (tokens_output or 0),  # type: ignore[operator]
                        }
                    )
                break

        # Add tool calls as Langfuse spans
        for child in span.walk():
            if child.kind == SpanKind.TOOL:
                self._langfuse.span(
                    name=child.name,
                    start_time=child.start_time,
                    end_time=child.end_time,
                    input=child.attributes.get("tool.input", ""),
                    output=child.attributes.get("tool.output", ""),
                    metadata={
                        "trace_id": span.trace_id,
                        "span_id": child.span_id,
                    },
                )

        if generation:
            generation.end()

    def _extract_metadata(self, span: Span) -> dict[str, object]:
        """Extract relevant metadata from span attributes."""
        metadata = {}

        # Extract common attributes
        for key in ["llm.cost", "llm.stop_reason", "llm.temperature"]:
            if key in span.attributes:
                metadata[key] = span.attributes[key]

        return metadata

    def flush(self) -> None:
        """Flush any pending data to Langfuse."""
        if LANGFUSE_AVAILABLE:
            self._langfuse.flush()


class LangfuseTraceExporter(SpanExporter):
    """Alternative Langfuse exporter using their trace API.

    This exporter uses Langfuse's newer trace-based API for better
    integration with LangChain and other frameworks.
    """

    def __init__(
        self,
        public_key: str | None = None,
        secret_key: str | None = None,
        host: str | None = None,
    ) -> None:
        if not LANGFUSE_AVAILABLE:
            raise ImportError("Langfuse not installed. Install with: pip install langfuse")

        self._langfuse = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )

    def export(self, span: Span) -> None:
        """Export span as a Langfuse trace."""
        if not LANGFUSE_AVAILABLE or span.parent_span_id is not None:
            return

        try:
            with self._langfuse.trace(
                name=span.name,
                session_id=span.session_id,
                metadata={
                    "trace_id": span.trace_id,
                    **span.attributes,
                },
            ):
                # Add LLM calls as generations
                for child in span.walk():
                    if child.kind == SpanKind.LLM:
                        self._langfuse.generation(
                            name=child.name,
                            model=child.attributes.get("llm.model", ""),
                            input=child.attributes.get("llm.prompt", ""),
                            output=child.attributes.get("llm.completion", ""),
                        )

        except Exception as e:
            _log.warning("Failed to export trace to Langfuse: %s", e)


__all__ = [
    "LangfuseExporter",
    "LangfuseTraceExporter",
]
