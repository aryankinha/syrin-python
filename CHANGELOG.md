# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-02-26

### Added

- **Almock (LLM Mock)** — `Model.Almock()` for development and testing without an API key. Configurable pricing tiers (LOW, MEDIUM, HIGH, ULTRA_HIGH), latency (default 1–3s or custom), and response (Lorem Ipsum or custom text). Examples and docs use Almock by default; swap to a real model with one line.
- **Memory decay and consolidation** — Decay strategies with configurable min importance and optional reinforcement on access. `Memory.consolidate()` for content deduplication with optional budget. Entries without IDs receive auto-generated IDs.
- **Checkpoint triggers** — Auto-save on STEP, TOOL, ERROR, or BUDGET in addition to MANUAL. Loop strategy comparison (REACT, SINGLE_SHOT, PLAN_EXECUTE, CODE_ACTION) documented in advanced topics.
- **Provider resolution** — `ProviderNotFoundError` when using an unknown provider, with a message listing known providers. Strict resolution available via `get_provider(name, strict=True)`.
- **Observability** — Agent runs emit a root span plus child spans for each LLM call and tool execution. Session ID propagates to all spans. Optional OTLP exporter (`syrin.observability.otlp`) for OpenTelemetry.
- **Documentation** — Architecture guide, code quality guidelines, CONTRIBUTING.md. Community links (Discord, X) and corrected doc links.

### Changed

- **Model resolution** — Agent construction with an invalid `provider` in `ModelConfig` now raises `ProviderNotFoundError` instead of falling back (breaking for callers relying on LiteLLM fallback).
- **API** — `syrin.run()` return type and `tools` parameter typing clarified. Duplicate symbols removed from public API exports.
- **Docs** — README and guides use lowercase `syrin` imports. Guardrails and rate-limit docs: fixed imports and references.

### Fixed

- Response and recall contract; spawn return type and budget inheritance. Rate limit thresholds fully controlled by user action callback. Guardrail input block skips LLM; output block returns GUARDRAIL response. Checkpoint trigger behavior (STEP, MANUAL). Session span count when exporting. Edge cases: empty tools, no budget, unknown provider.

---

## [0.1.1] - 2026-02-25

- Initial release. Python library for building AI agents with budget management, declarative definitions, and observability.

**Install:** `pip install syrin==0.1.1`
