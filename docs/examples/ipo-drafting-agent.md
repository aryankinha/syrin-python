---
title: IPO Drafting Agent
description: Draft regulatory documents with RAG, grounding, and structured output
weight: 390
---

## IPO Drafting Agent

A production-ready example that drafts the **Capital Structure and Shareholding Pattern** section of a Draft Red Herring Prospectus (DRHP) from ROC filings.

This demonstrates real-world enterprise patterns: RAG, agentic retrieval, structured output, fact grounding, and guardrails.

## Architecture

```
ROC Filings (PAS-3, SH-7, MOA)
    ↓
Knowledge (Chunk + Embed + Store)
    ↓
Agentic RAG (Multi-query search)
    ↓
Grounding + Guardrails
    ↓
Structured Output (DraftSection)
```

## The DRHP Agent

```python
from syrin import Agent, Budget, FactVerificationGuardrail, Output
from syrin.embedding import Embedding
from syrin.enums import KnowledgeBackend
from syrin.knowledge import (
    AgenticRAGConfig,
    ChunkConfig,
    ChunkStrategy,
    GroundingConfig,
    Knowledge,
)

def create_drhp_agent() -> Agent:
    knowledge = Knowledge(
        sources=[
            # Load all filings from data directory
            Knowledge.Directory("data", glob="**/*.md"),
        ],
        embedding=Embedding.OpenAI("text-embedding-3-small"),
        backend=KnowledgeBackend.MEMORY,
        chunk_config=ChunkConfig(
            strategy=ChunkStrategy.RECURSIVE,
            chunk_size=512,
        ),
        top_k=12,
        score_threshold=0.2,
        agentic=True,  # Multi-query retrieval
        agentic_config=AgenticRAGConfig(
            max_search_iterations=3,
            decompose_complex=True,
            grade_results=True,
        ),
        grounding=GroundingConfig(
            extract_facts=True,
            verify_before_use=True,
            cite_sources=True,
            confidence_threshold=0.7,
        ),
    )
    
    return Agent(
        model=Model.OpenAI("gpt-4o"),
        system_prompt=SYSTEM_PROMPT,
        knowledge=knowledge,
        output=Output(DraftOutput, validation_retries=3),
        max_tool_iterations=15,
        budget=Budget(max_cost=1.0),
        guardrails=[FactVerificationGuardrail()],
        debug=True,
    )
```

**What just happened:**
1. Loaded all ROC filings from data directory
2. Configured agentic RAG with multi-query search
3. Added grounding for fact verification
4. Set structured output with validation

## Structured Output Schema

Define the expected output with `@structured`:

```python
from syrin.model import structured

@structured
class DraftOutput:
    draft_section: str  # Paragraph-style legal disclosure
    sources_used: list[str]  # Document names used
    auto_extracted_parts: list[str]  # Fields extracted
    requires_review: list[str]  # Items needing verification
```

**Why this matters:**
- Legal documents need exact numbers
- Sources tracked for compliance
- Review items flagged automatically

## System Prompt

Instructions for legal drafting:

```python
SYSTEM_PROMPT = """You are a DRHP drafting assistant.

CRITICAL - Call search_knowledge FIRST with these queries:
- "capital structure", "authorized capital"
- "issued capital", "shareholding"
- "PAS-3", "List of Allottees", "allottees"
- "equity shares", "MOA", "SH-7"

RULES:
- Copy numbers and names EXACTLY from search results
- Use the company name exactly as in documents
- draft_section MUST be paragraph-style legal disclosure
- Do NOT invent or approximate numbers

Output valid JSON with draft_section, sources_used, 
auto_extracted_parts, requires_review."""
```

## Agentic RAG

Multi-step retrieval for complex queries:

```python
agentic_config=AgenticRAGConfig(
    max_search_iterations=3,  # Up to 3 search rounds
    decompose_complex=True,    # Break complex queries
    grade_results=True,        # Score relevance
    relevance_threshold=0.35,  # Minimum score
)
```

**What this does:**
1. Initial search for broad results
2. Decompose if query is complex
3. Refine search based on results
4. Grade and filter by relevance

## Grounding & Verification

Verify facts against source documents:

```python
grounding=GroundingConfig(
    extract_facts=True,
    verify_before_use=True,
    cite_sources=True,
    confidence_threshold=0.7,
)
```

**Grounded facts structure:**

```python
@dataclass
class GroundedFact:
    content: str        # The fact
    source: str         # Document source
    confidence: float   # 0.0 - 1.0
    verification: VerificationStatus  # VERIFIED, CONTRADICTED, etc.
```

## Fact Verification Guardrail

```python
from syrin.guardrails import FactVerificationGuardrail

guardrails=[FactVerificationGuardrail()]
```

**What it does:**
- Checks each fact against sources
- Flags contradictions
- Requires minimum confidence

## Running the Agent

```bash
# From project root
cd examples/ipo_drafting_agent
python run.py
```

**Output:**

```
=== RESULT ===

### DRAFT SECTION ###
"The authorized capital of the Company is Rs. 5,00,00,000 divided into 
50,00,000 equity shares of Rs. 10 each. Pursuant to PAS-3 filings dated 
[date], the company has issued and allotted..."

### SOURCES USED ###
- data/PAS-3/allotment_resolution.md
- data/SH-7/shareholding_pattern.md

### AUTO-EXTRACTED PARTS ###
- Authorized capital: Rs. 5 Cr
- Issued capital: Rs. 3.5 Cr
- Promoter holding: 62.5%

### REQUIRES REVIEW ###
- Verify PAS-3 filing dates
- Confirm SH-7 ROC acknowledgment

=== METRICS ===
Cost: $0.2345
Grounded Facts: 15
  - Verified: 12
  - Contradicted: 0
  - Not Found: 1
  - Unverified: 2
```

## HTTP Serving

Expose via REST API:

```python
# serve.py
from syrin import Agent

agent = create_drhp_agent()

if __name__ == "__main__":
    agent.serve(port=8000, enable_playground=True)
```

```bash
# Start server
python serve.py

# Call via curl
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Draft the Capital Structure section."}'

# Visit playground
# http://localhost:8000/playground
```

## Input Documents

Add filings to `data/`:

```
data/
├── PAS-3/
│   ├── allotment_resolution.md
│   └── list_of_allottees.md
└── SH-7/
    ├── shareholding_pattern.md
    ├── moa_extract.md
    └── board_resolution.md
```

## Components Used

Six components work together in this example. `Knowledge` handles document loading, chunking, and embedding. `AgenticRAGConfig` enables multi-query search with iterative retrieval. `GroundingConfig` performs fact extraction and verification against source documents. `FactVerificationGuardrail` validates that grounded facts meet the confidence threshold before they enter the output. `Output(DraftOutput)` enforces the structured legal output schema with validation retries. `Budget` caps the cost per run to prevent runaway spend on deep retrieval tasks.

## Key Patterns

1. **Agentic Retrieval**: LLM decides search queries dynamically
2. **Grounding**: Every fact traced to source
3. **Structured Output**: Machine-readable + human-readable
4. **Guardrails**: Compliance validation
5. **Transparency**: Sources and review items exposed

## Running Tests

```bash
PYTHONPATH=. pytest examples/ipo_drafting_agent/ipo_tests/ -v
```

## What's Next?

- Learn about [knowledge management](/agent-kit/examples/knowledge-agent)
- Explore [grounding and confidence](/agent-kit/integrations/grounding)
- Understand [structured output](/agent-kit/agent/structured-output)

## See Also

- [Knowledge pool documentation](/agent-kit/integrations/knowledge-pool)
- [Grounding documentation](/agent-kit/integrations/grounding)
- [Guardrails documentation](/agent-kit/agent/guardrails)
- [Structured output](/agent-kit/agent/structured-output)
