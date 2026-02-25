# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Observability:** Span coverage for agent runs: root agent span plus automatic child spans for each LLM call and tool execution when the loop uses a tracer. `AgentRunContext` now exposes an optional `tracer` property so loops can create LLM/tool spans.
- **Observability:** `_llm_span_context` and `_tool_span_context` helpers in `loop` so SingleShot and React loops create `SpanKind.LLM` and `SpanKind.TOOL` spans with semantic attributes (tokens, model, tool name, input/output).
- **Observability:** OTLP exporter implementation in `syrin.observability.otlp`: `OTLPExporter` converts Syrin spans to OpenTelemetry and exports to OTLP HTTP endpoint when optional dependency is installed; no-op when not.
- **Tests:** `tests/observability/test_observability_integration.py` — TDD tests for span coverage (agent/LLM/tool), session propagation, metrics schema, sampling parent-child consistency, debug mode, OTLP exporter, hook coverage, and export format.

### Changed

- **Observability:** Session ID from `trace.session()` now propagates to all spans created during agent runs (spans already had `session_id`; context was already used by tracer).
- **Docs:** `docs/observability.md` — Updated "What's Traced by Default" with exact span kinds and tree shape; added Metrics schema subsection; fixed Production Setup imports (create_sampler from sampling).
- **Plan:** Observability checklist in `plan/v0.2.0.md` marked complete.

### Fixed

### Deprecated

### Removed

### Security

---

## [0.1.1] - 2026-02-25

**syrin** v0.1.1 — Python library for building AI agents with budget management, declarative definitions, and production-ready observability.

Initial Release

---

**Install:** `pip install syrin==0.1.1`
