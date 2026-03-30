"""Public observability package facade.

This package exposes Syrin's tracing and observability API while keeping the
runtime implementation in private modules. Import from ``syrin.observability``
when you need spans, tracers, exporters, semantic attributes, or the convenience
context managers and decorators used for tracing agent activity.

Why use this package:
    - Trace agent, LLM, tool, memory, budget, and guardrail operations.
    - Export spans to console, JSONL, or other observability backends.
    - Attach semantic attributes and session context to runtime activity.
    - Use lightweight helpers and decorators for instrumentation in application code.

Typical usage:
    >>> from syrin.observability import trace, SpanKind
    >>> with trace.span("agent.run", kind=SpanKind.AGENT) as span:
    ...     span.set_attribute("agent.name", "assistant")

Exported surface:
    - core tracing types such as ``Span``, ``Tracer``, ``Session``, and ``SpanExporter``
    - exporters, semantic attributes, and trace/session accessors
    - convenience decorators for common Syrin operation categories
"""

from syrin.observability._core import (
    ConsoleExporter,
    InMemoryExporter,
    JSONLExporter,
    SemanticAttributes,
    Session,
    Span,
    SpanContext,
    SpanExporter,
    SpanKind,
    SpanStatus,
    Tracer,
    agent_span,
    budget_span,
    current_session,
    current_span,
    get_tracer,
    guardrail_span,
    handoff_span,
    llm_span,
    memory_span,
    session,
    set_debug,
    span,
    tool_span,
    trace,
)

get_observability_tracer = get_tracer

__all__ = [
    "Span",
    "SpanKind",
    "SpanStatus",
    "SpanContext",
    "Session",
    "Tracer",
    "SpanExporter",
    "ConsoleExporter",
    "JSONLExporter",
    "InMemoryExporter",
    "SemanticAttributes",
    "trace",
    "span",
    "session",
    "current_span",
    "current_session",
    "set_debug",
    "get_observability_tracer",
    "get_tracer",
    "llm_span",
    "tool_span",
    "memory_span",
    "budget_span",
    "guardrail_span",
    "handoff_span",
    "agent_span",
]
