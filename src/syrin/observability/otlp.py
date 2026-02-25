"""OpenTelemetry Protocol (OTLP) exporter for Syrin.

Exports spans to any OTLP-compatible backend (Jaeger, Tempo, Datadog, etc.)

Requires: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-http

Example:
    >>> from syrin.observability.otlp import OTLPExporter
    >>> from syrin.observability import get_tracer
    >>>
    >>> exporter = OTLPExporter(
    ...     endpoint="http://localhost:4318/v1/traces",
    ...     headers={"Authorization": "Bearer token"},
    ...     service_name="my-agent",
    ... )
    >>> get_tracer().add_exporter(exporter)
"""

from __future__ import annotations

import logging
from typing import Any, cast

from syrin.observability import Span, SpanExporter

_log = logging.getLogger(__name__)

# Module-level declarations for optional dependencies
OPENTELEMETRY_AVAILABLE = False
_OTelOTLPExporter: Any = None
_TracerProvider: Any = None
_BatchSpanProcessor: Any = None
_Resource: Any = None


def _try_import_opentelemetry() -> bool:
    """Try to import opentelemetry modules."""
    global \
        OPENTELEMETRY_AVAILABLE, \
        _OTelOTLPExporter, \
        _TracerProvider, \
        _BatchSpanProcessor, \
        _Resource
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter as _OTel,
        )
        from opentelemetry.sdk.resources import Resource as _R
        from opentelemetry.sdk.trace import TracerProvider as _TP
        from opentelemetry.sdk.trace.export import BatchSpanProcessor as _BSP

        _OTelOTLPExporter = _OTel
        _TracerProvider = _TP
        _BatchSpanProcessor = _BSP
        _Resource = _R
        OPENTELEMETRY_AVAILABLE = True
        return True
    except ImportError:
        return False


_try_import_opentelemetry()


class OTLPExporter(SpanExporter):
    """Export Syrin spans to an OTLP-compatible backend (Jaeger, Tempo, Datadog, etc.).

    When OpenTelemetry packages are not installed, export() is a no-op and a warning
    is logged once.

    Args:
        endpoint: OTLP HTTP endpoint (e.g. http://localhost:4318/v1/traces).
        headers: Optional dict of headers (e.g. {"Authorization": "Bearer token"}).
        service_name: Service name for the resource (default: "syrin").
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:4318/v1/traces",
        headers: dict[str, str] | None = None,
        service_name: str = "syrin",
    ) -> None:
        self._endpoint = endpoint
        self._headers = headers or {}
        self._service_name = service_name
        self._otel_exporter: Any = None
        self._tracer_provider: Any = None
        self._tracer: Any = None
        if OPENTELEMETRY_AVAILABLE:
            try:
                resource = _Resource.create({"service.name": service_name})
                self._tracer_provider = _TracerProvider(resource=resource)
                self._otel_exporter = _OTelOTLPExporter(
                    endpoint=endpoint,
                    headers=list(self._headers.items()) if self._headers else None,
                )
                self._tracer_provider.add_span_processor(_BatchSpanProcessor(self._otel_exporter))
                self._tracer = self._tracer_provider.get_tracer("syrin", "0.2.0")
            except Exception as e:
                _log.warning("OTLPExporter init failed: %s", e)
                self._otel_exporter = None
                self._tracer = None

    def export(self, span: Span) -> None:
        """Export a completed Syrin span to OTLP."""
        if not OPENTELEMETRY_AVAILABLE:
            return
        if self._tracer is None:
            return
        try:
            with self._tracer.start_as_current_span(
                span.name,
                kind=self._span_kind_to_otel(span.kind.value),
            ) as otel_span:
                for key, value in span.attributes.items():
                    try:
                        otel_span.set_attribute(key, value)
                    except Exception:
                        otel_span.set_attribute(key, str(value))
                if span.status.value == "error" and span.status_message:
                    from opentelemetry.trace import Status, StatusCode

                    otel_span.set_status(Status(StatusCode.ERROR, span.status_message))
        except Exception as e:
            _log.warning("Failed to export span to OTLP: %s", e)

    @staticmethod
    def _span_kind_to_otel(kind: str) -> int:
        from opentelemetry.trace import SpanKind as OTelSpanKind

        mapping = {
            "agent": OTelSpanKind.INTERNAL,
            "llm": OTelSpanKind.CLIENT,
            "tool": OTelSpanKind.INTERNAL,
            "memory": OTelSpanKind.INTERNAL,
            "budget": OTelSpanKind.INTERNAL,
            "guardrail": OTelSpanKind.INTERNAL,
            "handoff": OTelSpanKind.INTERNAL,
            "workflow": OTelSpanKind.INTERNAL,
            "internal": OTelSpanKind.INTERNAL,
        }
        return cast(int, mapping.get(kind.lower(), OTelSpanKind.INTERNAL))
