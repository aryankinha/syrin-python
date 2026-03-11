# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **DoclingLoader** — Universal document loader (PDF, DOCX, PPTX, XLSX, HTML, images) with AI-powered table extraction. Tables become separate Documents with `table_csv`, `table_html`, `table_markdown` in metadata. `pip install syrin[docling]`
- **DOCXLoader** — Load DOCX files. Uses Docling when available, else python-docx. `Knowledge.DOCX()`, `pip install syrin[docx]`
- **CSVLoader** — Load CSV files with optional `rows_per_document`. `Knowledge.CSV()`, no extra deps
- **ExcelLoader** — Load XLSX files, one Document per sheet. `Knowledge.Excel()`, `pip install syrin[excel]`
- **DirectoryLoader** — Now supports `.docx`, `.csv`, `.xlsx`, `.xls` via new loaders
- **Grounding layer** — `GroundingConfig` on Knowledge for anti-hallucination: fact extraction, verification, and citations. `search_knowledge` / `search_knowledge_deep` return verified facts when `grounding=GroundingConfig(enabled=True)`
- **GroundedFact** — Dataclass for verified facts with `content`, `source`, `page`, `confidence`, `verification` (VERIFIED/UNVERIFIED/CONTRADICTED/NOT_FOUND)
- **VerificationStatus** — StrEnum for fact verification states
- **DecisionAction.FLAG** — Guardrail action to annotate without blocking (for unverified claims)
- **FactVerificationGuardrail** — Verifies output claims against `context.metadata["grounded_facts"]`
- **CitationGuardrail** — Ensures factual statements have source citations (`[Source: doc, Page N]`)
- **Shared verification** — `verify_claim` and `grade_results` moved to `_verification.py` for reuse by agentic RAG and grounding
- **Template engine** — Slot-based generation with Mustache syntax. `Template`, `SlotConfig`, `OutputFormat`, `OutputConfig`. Use `output_config=OutputConfig(format=..., template=tpl)` on Agent (requires `output=Output(MyModel)`). `response.content` = rendered template, `response.template_data` = slot values
- **OutputConfig** — Renamed from `OutputFormatConfig`. Agent uses `output_config` (renamed from `output_format`).
- **File generation** — When `output_config` format is TEXT/MARKDOWN/HTML/PDF/DOCX, agent produces `response.file` (Path) and `response.file_bytes` (bytes). `save_as_pdf()`, `save_as_docx()`, `save_as()` helpers. PDF requires `pip install syrin[pdf-output]`, DOCX requires `syrin[docx]`.
- **Citation system** — `OutputConfig.citation=CitationConfig(style=...)` parses `[Source: doc.pdf, Page N]` markers from content, reformats as inline/footnote/appendix, and populates `response.citations` (`Citation` dataclass with text, source, page). Use for financial, legal, medical outputs.
- **@structured improvements** — Nested types (`list[Shareholder]`) with JSON schema `$defs`/`$ref`, `Annotated[T, "description"]` for field descriptions (helps LLM), proper required/optional from `Optional` and defaults.
- **response.parsed** — Convenience property: `response.parsed` is same as `response.structured.parsed` when output is configured.

### Changed

- **Tool result length** — `max_tool_result_length` default is now `0` (no truncation). Full tool results are sent to the LLM. Use `max_tool_result_length > 0` to cap length. Display in traces/playground remains truncated to 2000 chars.
- **Structured output retry** — When validation fails, the agent calls the LLM again with the validation error and schema so the model can fix the output. Use `validation.get_retry_prompt(output_type, error_message)` for custom flows.
- **Knowledge search** — Results are deduplicated by content hash so overlapping chunks do not repeat.
- **PDFLoader** — Logs a warning when a page produces no text and suggests `Knowledge.Docling(...)` for table/image extraction.
- **Guardrails** — `ParallelEvaluationEngine` default timeout 30s. `GuardrailChain` supports `timeout_s=30` (default) per guardrail so evaluation cannot hang.

### Fixed

- Chunk metadata from documents (page, title, etc.) is preserved through all chunkers.
- Budget tracker is wired for knowledge tools; embedding costs from `search_knowledge` are recorded on the agent run budget.

---

## [0.8.0] - 2026-03-11

### Added

- **Intelligent model routing**: Automatic LLM selection based on cost, performance, and context requirements.
- **Multi-modality support**: Native support for images, video, and audio generation/processing.
- **Knowledge integration**: RAG (Retrieval-Augmented Generation) with vector stores, document loaders, and semantic search.

### Changed

- **Simplified installation**: `pip install syrin` now includes OpenAI and serving dependencies by default.
- **Removed CLI**: `syrin trace`, `syrin run`, and `syrin doctor` commands removed; use `python my_agent.py --trace` for observability.

### Breaking

- **CLI removal**: Command-line interface deprecated; use direct Python execution with `--trace` flag.

---

## [0.7.0] - 2026-03-07

### Breaking

- **Context:** `Context.budget` removed. Use **`Context.token_limits`** (TokenLimits). **`ContextWindowBudget`** → **`ContextWindowCapacity`**. **`Context.get_budget(model)`** → **`Context.get_capacity(model)`**. **ContextManager.prepare()** takes **`capacity`** instead of **`budget`**.

### Added

- **Context management** — Snapshot (provenance, why_included, context_rot_risk), breakdown, custom compaction prompt, `auto_compact_at`, runtime injection, `context_mode` (full/focused), formation_mode (push/pull), stored output chunks, persistent context map, pluggable RelevanceScorer.
- **Memory–context** — Memory on by default; `memory=None` turns off. No extra field.
- **Handoff/spawn** — Context visibility in events (`handoff_context`, `context_inherited`, `initial_context_tokens`).

### Fixed

- Examples: `Output(type=...)` → `Output(MyModel)`; `Agent(dependencies=...)` → `Agent(config=AgentConfig(dependencies=...))`.

---

## [0.6.0] - 2026-03-05

### Added

- **Remote config** — `syrin.init(api_key=...)` or `SYRIN_API_KEY` enables real-time config overrides from Syrin Cloud or self-hosted backend. Overrides (budget, memory, temperature, etc.) via SSE; zero overhead when not enabled.
- **Config routes** — `GET /config`, `PATCH /config`, `GET /config/stream` added to `agent.serve()`. Baseline + overrides + revert; works with or without `syrin.init()`.
- **`syrin.remote`** — Types: `AgentSchema`, `ConfigOverride`, `OverridePayload`, `SyncRequest`/`SyncResponse`. `ConfigRegistry`, `ConfigResolver`, `extract_schema()`. Transports: `SSETransport`, `ServeTransport`, `PollingTransport`.
- **Hooks** — `Hook.REMOTE_CONFIG_UPDATE`, `Hook.REMOTE_CONFIG_ERROR`.

### Changed

- Agent registers with remote config on init when `syrin.init()` was called.

---

## [0.5.0] - 2026-03-04

### Added

- **C5 fix** — Memory.remember/recall/forget use configured backend (SQLite, Qdrant, Chroma) instead of in-memory dict when backend != MEMORY.
- **QdrantConfig** — `Memory(qdrant=QdrantConfig(url=..., api_key=..., collection=..., namespace=...))` for Qdrant Cloud or local.
- **ChromaConfig** — `Memory(chroma=ChromaConfig(path=..., collection=...))` for Chroma vector backend.
- **Namespace isolation** — `QdrantConfig.namespace` scopes all operations; payload filter on search/list.
- **WriteMode** — `WriteMode.SYNC` (block until complete) vs `WriteMode.ASYNC` (fire-and-forget, default).
- **Memory export/import** — `Memory.export()` returns `MemorySnapshot`; `Memory.import_from(snapshot)` appends memories. JSON-serializable for GDPR export.
- **Examples** — `examples/04_memory/qdrant_memory.py`, `chroma_memory.py`, `async_memory.py`, `export_import_memory.py`.

### Changed

- Agent and Memory handoff now use `memory._backend_kwargs()` for backend config.
- `syrin[qdrant]` and `syrin[chroma]` optional dependencies added to pyproject.toml.

---

## [0.4.1] - 2026-03-01

### Added

- API additions: `Response.raw_response`, `GuardrailCheckResult.guardrail_name`, `CircuitBreaker.state`, `EventBus.on`, `GlobalConfig.debug`, `TokenLimits.per_hour`, `RateLimit.window`, `agent.checkpointer`.

### Fixed

- Model fallback and response transformer now use `model.acomplete()` when model has fallbacks/transformers.
- `Model.with_middleware()` preserves `provider`.
- Provider availability checks use `importlib.util.find_spec()` instead of import.

### Changed

- Strict typing: `TypedDict` + `Unpack` for memory kwargs, `ServeConfig`, agent specs. Pyright config added.
- Replaced `Any` with `object` / `TypedDict` across core modules.
- Docs: `docs/TYPING.md` for typing standards; updated API references.

---

## [0.4.0] - 2026-02-28

### Added

- **Agent Serving** — `agent.serve()` with HTTP, CLI, STDIO; composable features from agent composition (MCP, discovery). `AgentRouter` for multi-agent on one server.
- **MCP** — `syrin.MCP` declarative server (`@tool` in class); `syrin.MCPClient` for remote MCP; `.select()`, `.tools()`; MCP in `tools=[]` auto-mounts `/mcp`.
- **Agent Discovery** — A2A Agent Card at `GET /.well-known/agent-card.json`; auto-generated from agent metadata; multi-agent registry.
- **Dynamic prompts** — `@prompt`, callable `system_prompt`, `prompt_vars`, `PromptContext` with built-ins (`date`, `conversation_id`, etc.).
- **Web playground** — `enable_playground=True` for chat UI; `debug=True` for observability (cost, tokens, traces per reply); supports single, multi-agent, pipeline.
- **Serving extras** — `syrin[serve]` for FastAPI, uvicorn; `/chat`, `/stream`, `/health`, `/ready`, `/describe`, `/budget`.

### Changed

- **Discovery path** — Agent Card served at `/.well-known/agent-card.json` (was `/.well-known/agent.json`). Canonical URL: `https://{domain}/.well-known/agent-card.json`.

---

## [0.3.0] - 2026-02-27

### Added

- **Sub-agents & handoff** — `spawn(task=...)`, `handoff(AgentClass, task)` with optional memory transfer and budget inheritance.
- **Handoff interception** — `events.before(Hook.HANDOFF_START, fn)`; raise `HandoffBlockedError` to block; `HandoffRetryRequested` for retry.
- **Audit logging** — `AuditLog`, `JsonlAuditBackend`; `Agent(audit=...)`, `Pipeline(audit=...)`, `DynamicPipeline(audit=...)`.
- **HITL** — `@syrin.tool(requires_approval=True)`; `ApprovalGate` protocol; hooks: HITL_PENDING, HITL_APPROVED, HITL_REJECTED.
- **Circuit breaker** — `CircuitBreaker` for LLM/provider failures; CLOSED → OPEN → HALF_OPEN; configurable fallback.
- **Budget-aware context** — Context tier selection by budget percent remaining.
- **Dependency Injection** — `Agent(deps=...)`, `RunContext[Deps]`; tools receive `ctx.deps` (excluded from LLM schema).
- **Dynamic Pipeline** — Improved hooks and events API; flow diagram in docs/dynamic-pipeline.md.
- **Manual validation** — `docs/MANUAL_VALIDATION.md` with run commands for examples.

### Changed

- **API validation** — Agent, Model, Memory, Loop validate inputs at construction; clear errors for wrong types.
- **agent.response(user_input)** — Validates `user_input` is `str`; friendly error for `None`/`int`/`dict`.
- **Example paths** — Fixed run instructions (`08_streaming`, `07_multi_agent`).

### Fixed

- Chaos stress test fixes: Agent/Loop validation; Loop `max_iterations < 1` no longer causes UnboundLocalError. Model `_provider_kwargs` passed to provider.

---

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
