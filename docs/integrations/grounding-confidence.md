---
title: Grounding Confidence
description: Understand and calibrate trust levels for grounded facts
weight: 201
---

## How Much Should You Trust?

You've enabled grounding. You've extracted facts and verified them. But now comes the hard question: **how much should you trust each fact?**

A fact can be:
- **Verified but wrong** — The source document was incorrect
- **Verified by weak evidence** — The source tangentially mentions it
- **Not verified at all** — The source doesn't address it

This guide explains confidence levels and how to calibrate them for your use case.

## Understanding Confidence

In Syrin's grounding system, confidence is a score from 0.0 to 1.0:

| Score Range | Interpretation |
| --- | --- |
| 0.9 - 1.0 | Very high confidence |
| 0.7 - 0.9 | High confidence |
| 0.5 - 0.7 | Medium confidence |
| 0.3 - 0.5 | Low confidence |
| 0.0 - 0.3 | Very low confidence |

But confidence isn't just a number. It's about **where the confidence comes from**.

## Sources of Confidence

### 1. Extraction Confidence

When facts are extracted from documents, the LLM assigns an initial confidence:

```
Document: "The company was founded in 2015 with initial 
           capital of ₹10,00,000."

Extracted Fact: "Company founded in 2015"
Confidence: 0.95

Extracted Fact: "Initial capital was significant"
Confidence: 0.3 (vague statement)
```

### 2. Verification Confidence

During verification, the fact is checked against the source:

```
Fact: "Company founded in 2015"
Evidence: "The company was founded in 2015..."

Verification: SUPPORTED
Verification adds: High confidence in fact
```

```
Fact: "Initial capital was ₹10,00,000"
Evidence: "The company was founded in 2015 with initial 
          capital of ₹10,00,000."

Verification: SUPPORTED  
Verification adds: High confidence (exact match)
```

### 3. Combined Confidence

Final confidence considers both extraction and verification:

```
Initial Extraction: 0.7
Verification: SUPPORTED → +0.2
Exact match in source → +0.1

Final Confidence: 0.9
```

## Verification Status Impact

Verification status dramatically affects how to interpret confidence:

### VERIFIED

```python
GroundedFact(
    content="The authorized capital is ₹50,00,000",
    confidence=0.85,
    verification=VerificationStatus.VERIFIED,
    source="contract.pdf",
    page=3,
)
```

**Interpretation:** The source explicitly states this. Use with high confidence.

### CONTRADICTED

```python
GroundedFact(
    content="Shares have face value of ₹100",
    confidence=0.6,  # Looks confident...
    verification=VerificationStatus.CONTRADICTED,  # But contradicts source!
)
```

**Interpretation:** Despite reasonable confidence, the source says otherwise. **Do not use.**

### UNVERIFIED

```python
GroundedFact(
    content="Dividends are paid quarterly",
    confidence=0.4,
    verification=VerificationStatus.UNVERIFIED,
)
```

**Interpretation:** Source doesn't address this claim. Use with caution or exclude.

### NOT_FOUND

```python
GroundedFact(
    content="The company has international offices",
    confidence=0.0,
    verification=VerificationStatus.NOT_FOUND,
)
```

**Interpretation:** No relevant source found. **Do not use.**

## Threshold Configuration

The `confidence_threshold` setting controls inclusion:

```python
GroundingConfig(
    confidence_threshold=0.7,  # Only include facts >= 70% confidence
)
```

### Choosing a Threshold

| Use Case | Threshold | Rationale |
| --- | --- | --- |
| Legal/Compliance | 0.85+ | High accuracy required |
| Financial | 0.8+ | Money implications |
| Medical | 0.8+ | Health stakes |
| General Q&A | 0.7 | Balanced |
| Research | 0.5 | Include more, filter later |

### Threshold vs. Status

**Always consider both:**

```
# Good combination
confidence_threshold=0.7
verification=VERIFIED

# This is high confidence

# Problem combination  
confidence_threshold=0.7
verification=CONTRADICTED

# The status overrides the number!
# CONTRADICTED facts should never be used
```

## Calibrating for Your Use Case

### High-Stakes Decisions

For legal, medical, or financial use cases:

```python
GroundingConfig(
    confidence_threshold=0.85,
    verify_before_use=True,
    cite_sources=True,
    flag_missing=True,  # Explicitly flag gaps
)
```

Additional checks:

```python
# Only use VERIFIED facts
verified_facts = [f for f in facts if f.verification == VerificationStatus.VERIFIED]

# Check confidence
high_confidence = [f for f in verified_facts if f.confidence >= 0.85]
```

### Casual Q&A

For general questions where approximate answers are fine:

```python
GroundingConfig(
    confidence_threshold=0.5,  # Include more facts
    verify_before_use=True,
    cite_sources=True,
)
```

### Research and Discovery

When exploring topics broadly:

```python
GroundingConfig(
    confidence_threshold=0.3,  # Include most facts
    verify_before_use=False,  # Skip verification for speed
    extract_facts=True,  # But still extract
)
```

## Working with Grounded Facts

### Filtering Facts

```python
def get_reliable_facts(facts: list[GroundedFact]) -> list[GroundedFact]:
    """Filter to only reliable, verified facts."""
    return [
        f for f in facts
        if f.verification == VerificationStatus.VERIFIED
        and f.confidence >= 0.7
    ]

def get_facts_needing_review(facts: list[GroundedFact]) -> list[GroundedFact]:
    """Facts that should be reviewed by a human."""
    return [
        f for f in facts
        if f.verification != VerificationStatus.CONTRADICTED
        and f.confidence < 0.7
    ]

def get_dangerous_facts(facts: list[GroundedFact]) -> list[GroundedFact]:
    """Facts that should not be used."""
    return [
        f for f in facts
        if f.verification in (
            VerificationStatus.CONTRADICTED,
            VerificationStatus.NOT_FOUND,
        )
    ]
```

### Displaying Facts by Confidence

```python
def format_fact(fact: GroundedFact) -> str:
    """Format a fact with appropriate confidence indicator."""
    if fact.verification == VerificationStatus.CONTRADICTED:
        return f"⚠️ [CONTRADICTED] {fact.content}"
    
    if fact.verification == VerificationStatus.NOT_FOUND:
        return f"❓ [NOT FOUND] {fact.content}"
    
    if fact.confidence >= 0.85:
        indicator = "✅"
    elif fact.confidence >= 0.7:
        indicator = "⚡"
    else:
        indicator = "⚠️"
    
    citation = f" [{fact.source}"
    if fact.page:
        citation += f", p.{fact.page}"
    citation += "]"
    
    return f"{indicator} [{fact.confidence:.0%}] {fact.content}{citation}"
```

### Answer Generation with Confidence

```python
def generate_answer_with_confidence(facts: list[GroundedFact]) -> str:
    """Generate answer with confidence indicators."""
    reliable = get_reliable_facts(facts)
    needs_review = get_facts_needing_review(facts)
    dangerous = get_dangerous_facts(facts)
    
    parts = []
    
    if reliable:
        parts.append("Based on verified information:")
        for f in reliable:
            parts.append(f"- {f.content}")
    
    if needs_review:
        parts.append("\n⚠️ Information needing verification:")
        for f in needs_review:
            parts.append(f"- {f.content}")
    
    if dangerous:
        parts.append("\n❌ Claims not supported by sources:")
        for f in dangerous:
            parts.append(f"- {f.content}")
    
    return "\n".join(parts)
```

## Calibration Over Time

Confidence systems need tuning. Track:

### Accuracy Metrics

```python
# After ground truth is known
def record_accuracy(fact: GroundedFact, ground_truth: bool):
    """Track whether grounded facts were correct."""
    print(f"Fact: {fact.content}")
    print(f"Confidence: {fact.confidence}")
    print(f"Verification: {fact.verification}")
    print(f"Actual: {ground_truth}")
    print(f"Correct: {ground_truth and fact.verification == VerificationStatus.VERIFIED}")
```

### Threshold Tuning

```python
# Analyze accuracy at different thresholds
for threshold in [0.3, 0.5, 0.7, 0.85]:
    correct = sum(1 for r in results if r.confidence >= threshold and r.ground_truth)
    total = sum(1 for r in results if r.confidence >= threshold)
    precision = correct / total if total > 0 else 0
    recall = correct / sum(1 for r in results if r.ground_truth)
    print(f"Threshold {threshold}: Precision={precision:.2f}, Recall={recall:.2f}")
```

### Error Analysis

```python
# Look at failures
false_negatives = [r for r in results 
                   if r.ground_truth and 
                   r.verification != VerificationStatus.VERIFIED]

false_positives = [r for r in results 
                   if not r.ground_truth and 
                   r.verification == VerificationStatus.VERIFIED]

# Improve based on patterns
```

## User-Facing Confidence

When showing results to users, present confidence clearly:

### Display Format

```
✅ High Confidence (85%+)
   "The company was founded in 2015."
   Source: Company Overview, Page 2

⚡ Medium Confidence (70-85%)
   "The product costs $99."
   Source: Price List, Page 1

⚠️ Low Confidence (<70%)
   "The team has 50 employees."
   Source: About Page

❌ Contradicted
   "The company is profitable."
   Source contradicts this claim.

❓ Not Verified
   "The CEO has a computer science degree."
   No source found for this claim.
```

### Actionable Guidance

| Confidence Level | User Guidance |
| --- | --- |
| 90%+ | Very reliable, safe to use |
| 70-90% | Generally reliable, minor verification recommended |
| 50-70% | Verify before critical use |
| <50% | Do not use without additional verification |
| CONTRADICTED | Do not use, incorrect |
| NOT_FOUND | Do not use, not in sources |

## Common Pitfalls

### Ignoring Verification Status

```python
# Wrong: Only checking confidence
if fact.confidence >= 0.7:
    use_fact(fact)

# Right: Check both
if fact.verification == VerificationStatus.VERIFIED and fact.confidence >= 0.7:
    use_fact(fact)
```

### Setting Threshold Too Low

```python
# Wrong: Including unreliable facts
GroundingConfig(confidence_threshold=0.3)

# Right: Calibrate for your use case
GroundingConfig(confidence_threshold=0.7)  # Adjust based on testing
```

### Over-trusting Single Sources

```python
# What if the source is wrong?
# Best practice: Multiple independent sources for critical facts
```

## What's Next?

- [Grounding](/integrations/grounding) — Enable fact verification
- [Agentic RAG](/integrations/knowledge-rag) — Multi-step retrieval
- [Best Practices](/integrations/knowledge-pool) — Production RAG

## See Also

- [Knowledge Pool](/integrations/knowledge-pool) — Complete overview
- [RAG Configuration](/integrations/knowledge-rag) — Retrieval setup
- [Error Handling](/agent/error-handling) — Graceful failure
