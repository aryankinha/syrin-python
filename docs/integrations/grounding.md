---
title: Grounding
description: Verify AI responses against source documents
weight: 200
---

## The Hallucination Problem

LLMs are impressive. They can write poetry, code, and essays. But they have a dangerous flaw: **hallucination** — making up facts that sound plausible but aren't true.

You've seen it:
- "The company was founded in 1895." (Actually 2012)
- "According to the document, the answer is X." (X isn't mentioned)
- "Our authorized capital is ₹50,00,000." (Which document said this?)

This is dangerous for any production system. Users trust AI answers. If the AI makes things up, that trust breaks.

## The Grounding Solution

**Grounding** is an anti-hallucination layer that:

1. **Extracts** facts from retrieved documents
2. **Verifies** each fact against sources
3. **Generates** citations
4. **Flags** unverified claims

**Without Grounding:**
- User: "What is the authorized capital?"
- Retrieved: [Document about company structure]
- AI: "The authorized capital is ₹50,00,000." (Did it read this? Did it hallucinate?)

**With Grounding:**
- User: "What is the authorized capital?"
- Retrieved: [Document about company structure]
- Extract: "Authorized capital is ₹50,00,000"
- Verify: SUPPORTED
- Cite: [Source: company_structure.pdf, Page 3]
- AI: "According to the company structure document, the authorized capital is ₹50,00,000. [Source: company_structure.pdf, Page 3]"

## Why Grounding Works

Hallucination happens when:

1. LLM doesn't distinguish "I read this" from "This sounds right"
2. Retrieved context has the info but LLM generalizes too much
3. No accountability for fact accuracy

Grounding addresses all three by:

1. **Explicit extraction** — Facts are extracted, not assumed
2. **Verification step** — LLM checks each fact against sources
3. **Source tracking** — Every fact knows its origin

## How Grounding Works

### The Pipeline

The grounding pipeline:

1. **Fact Extraction** — LLM extracts distinct facts from retrieved documents
2. **Source Citation** — Link each fact to document/page
3. **Verification** — LLM verifies each fact against sources
4. **Confidence Score** — Rate each fact's reliability
5. **Formatted Output** — Facts with citations and flagged issues

### Verification Status

Each fact gets a status. `VERIFIED` means the fact is confirmed by the source — safe to use. `CONTRADICTED` means the source says otherwise — flag it or return an error, never use it. `UNVERIFIED` means the source doesn't address the claim — use with caution or exclude. `NOT_FOUND` means no relevant source was found at all — don't use it.

## Using Grounding in Syrin

```python
from syrin import Knowledge, Model
from syrin.knowledge import GroundingConfig
from syrin.embedding import Embedding

knowledge = Knowledge(
    sources=[
        Knowledge.PDF("./contract.pdf"),
        Knowledge.Markdown("./terms.md"),
    ],
    embedding=Embedding.OpenAI("text-embedding-3-small"),
    grounding=GroundingConfig(
        enabled=True,
        extract_facts=True,
        cite_sources=True,
        verify_before_use=True,
        confidence_threshold=0.7,
    ),
)
```

Now the agent:

1. Retrieves relevant documents
2. Extracts facts from those documents
3. Verifies each fact
4. Generates answers with citations

## Configuration Options

### Fact Extraction

```python
GroundingConfig(
    extract_facts=True,  # Extract structured facts
    max_facts=15,         # Max facts per search
    max_chunk_preview=800,  # Characters sent to extraction
)
```

### Verification

```python
GroundingConfig(
    verify_before_use=True,  # Verify facts before generating
    confidence_threshold=0.7,  # Min confidence to include
)
```

### Citation

```python
GroundingConfig(
    cite_sources=True,  # Include source in output
)
```

### Missing Information

```python
GroundingConfig(
    flag_missing=True,  # Flag when expected info not found
)
```

## Output Format

With grounding enabled, `search_knowledge` returns formatted facts:

```
GROUNDED FACTS (verified against source documents):

1. [VERIFIED] Authorized capital is ₹50,00,000 [Source: contract.pdf, Page 3]
2. [VERIFIED] Face value per share is ₹10 [Source: contract.pdf, Page 3]
3. [NOT_FOUND] The following could not be verified in source documents:
   - "Dividends are paid quarterly"
```

## Customizing Extraction

The extraction prompt can be customized:

```python
# The default prompt extracts:
# - Factual statements
# - Source document reference
# - Page number (if available)
# - Confidence (0.0-1.0)

# You can customize by modifying the GroundingConfig
# or implementing custom extraction logic
```

## Verification Prompts

The verification step uses structured prompts:

```
Does the following evidence support, contradict, or provide 
no information about the claim?

Claim: "The authorized capital is ₹50,00,000"
Evidence: "The authorized capital of the company is 
          ₹50,00,000 divided into 5,00,000 equity shares 
          of ₹10 each."

Verdict: SUPPORTED

Claim: "Shares have face value of ₹100"
Evidence: "The authorized capital of the company is 
          ₹50,00,000 divided into 5,00,000 equity shares 
          of ₹10 each."

Verdict: CONTRADICTED
```

## Confidence Thresholds

The `confidence_threshold` controls what's included:

```python
GroundingConfig(
    confidence_threshold=0.7,  # Only include facts with 70%+ confidence
)
```

A threshold of 0.9+ keeps only highly confident facts. 0.7 is the balanced, recommended default. 0.5 includes more facts with some noise. 0.0 includes all facts regardless of confidence.

## Batch Verification

For efficiency, facts are verified in batches:

```python
GroundingConfig(
    # Verification happens in batches of 10
    # (internal optimization)
)
```

This reduces LLM calls while still verifying all facts.

## Using with Agentic RAG

Grounding works especially well with Agentic RAG:

```python
knowledge = Knowledge(
    sources=[...],
    embedding=embedding,
    agentic=True,
    agentic_config=AgenticRAGConfig(...),
    grounding=GroundingConfig(
        enabled=True,
        verify_before_use=True,
    ),
)
```

The flow:

1. Agentic RAG retrieves and refines results
2. Grounding extracts and verifies facts
3. Agent generates answer from verified facts

## Failure Handling

Grounding handles edge cases gracefully:

### Extraction Fails

If LLM extraction fails, falls back to raw chunks:

```
Grounding extraction failed. Falling back to raw chunks.
[Chunk 1] "The authorized capital... ₹50,00,000..."
[Chunk 2] "5,00,000 equity shares of ₹10 each..."
```

### No Relevant Sources

```python
# Returns formatted message
"No grounded facts available. No relevant results found."
```

### Low Confidence

Facts below threshold are excluded or flagged:

```
[NOT VERIFIED] "Some claim" - Confidence below threshold
```

## Hooks for Grounding

Subscribe to grounding events:

```python
def on_extract_start(params, response):
    print(f"Extracting facts from {params.chunk_count} chunks")

agent.events.on(Hook.GROUNDING_EXTRACT_START, on_extract_start)

def on_extract_end(params, response):
    print(f"Extracted {params.fact_count} facts")

agent.events.on(Hook.GROUNDING_EXTRACT_END, on_extract_end)

def on_verify(params, response):
    print(f"Verified: {params.fact[:50]}... → {params.verdict}")

agent.events.on(Hook.GROUNDING_VERIFY, on_verify)

def on_complete(params, response):
    print(f"Verified: {params.verified_count}, "
          f"Unverified: {params.unverified_count}, "
          f"Missing: {params.missing_count}")

agent.events.on(Hook.GROUNDING_COMPLETE, on_complete)
```

## When to Use Grounding

### Use Grounding When

- Answers must be accurate (legal, medical, financial)
- Source citation is required
- Building trust with users
- Compliance requires audit trail

### Consider Alternatives When

- Speed is critical (grounding adds latency)
- Simple lookups (direct retrieval sufficient)
- Creative tasks (not fact-based)

## Performance Considerations

Grounding adds latency. Search alone takes about 100ms either way. Fact extraction adds roughly 200ms and verification adds another 300ms, bringing the total from ~100ms (without grounding) to ~600ms (with grounding). The cost is accuracy. For production systems where accuracy matters, the latency is worthwhile.

## What's Next?

- [Grounding Confidence](/agent-kit/integrations/grounding-confidence) — Trust levels and calibration
- [Agentic RAG](/agent-kit/integrations/knowledge-rag) — Multi-step retrieval
- [Knowledge Pool](/agent-kit/integrations/knowledge-pool) — Complete RAG overview

## See Also

- [Knowledge RAG](/agent-kit/integrations/knowledge-rag) — Retrieval configuration
- [Agentic RAG](/agent-kit/integrations/knowledge-pool) — Advanced retrieval
- [Verification](/agent-kit/integrations/grounding-confidence) — Trust calibration
