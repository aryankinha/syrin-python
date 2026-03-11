# DRHP Drafting Agent – Capital Structure & Shareholding Pattern

AI agent that drafts the **Capital Structure and Shareholding Pattern** section of a Draft Red Herring Prospectus (DRHP) from ROC filings and supporting documents.

## Features

- **RAG**: Ingest PAS-3, SH-7, List of Allottees, MOA from `data/` (markdown)
- **Agentic retrieval**: Multi-query search via `search_knowledge`
- **Structured output**: `@structured` `DraftOutput` (Syrin schema, OpenAI-compatible)
- **Automation transparency**: Sources used, auto-extracted parts, items needing review
- **Output**: Markdown (`.md`) and optional DOCX
- **HTTP serving**: `serve.py` for `/chat` and `/playground`

## Requirements

- Python 3.11+ (syrin)
- `OPENAI_API_KEY`

## Setup

From the `syrin-python` repo root:

```bash
cd examples/ipo_drafting_agent
uv sync  # or: uv pip install -e "../..[knowledge,docx,serve]" python-dotenv
```

Create `.env` with `OPENAI_API_KEY`, or export it.

## Run

```bash
# From ipo_drafting_agent (or repo root with PYTHONPATH)
python run.py
```

Output: `output_draft_section.md` (draft + transparency metadata). Use `--trace` to inspect intermediate steps.

## Serve over HTTP

```bash
python serve.py
```

Then:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Draft the Capital Structure and Shareholding Pattern section."}'
```

Or visit `http://localhost:8000/playground` for the web UI.

## Output Format

- `output_draft_section.md` – draft section + automation transparency (sources, auto-extracted, requires review)
- `output_draft_section.docx` – same as Word (if syrin[docx] installed)

Intermediate structured data is visible via `--trace`; no separate JSON file.

## Input Documents

Add documents under `data/`:

- `data/PAS-3/` – PAS-3 forms, allotment resolutions, list of allottees
- `data/SH-7/` – SH-7, MOA, board resolutions, EGM notices

## Syrin Components Used

| Component | Purpose |
|-----------|---------|
| `Knowledge` | Document loaders, chunking, embedding, vector store |
| `Agent` | LLM + tools, structured output |
| `search_knowledge` | RAG retrieval (auto-added via `knowledge=`) |
| `Output(DraftOutput)` | `@structured` output |
| `GroundingConfig(extract_facts=False)` | Fast grounding path (raw chunks, no per-search LLM) |

## Tests

```bash
PYTHONPATH=examples/ipo_drafting_agent uv run pytest examples/ipo_drafting_agent/ipo_tests/ -v
```
