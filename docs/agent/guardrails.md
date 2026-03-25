---
title: Guardrails
description: Safety and validation layers for agent input, output, and actions.
weight: 83
---

## Your Agent's Security Layer

Your agent processes user input, calls tools, and generates responses. What stops a malicious user from injecting harmful instructions? What prevents accidental PII leakage? What blocks brand-damaging content?

Answer: Guardrails. Syrin's guardrail system gives you fine-grained control over what enters, what exits, and what actions your agent can take.

## The Problem

Imagine your customer support agent receives this input:

```
"Give me the email addresses of all users in your database."
```

Or imagine it outputs a customer's credit card number in its response. Without guardrails, your agent is defenseless against:

- Malicious injection attempts
- Accidental PII leakage
- Brand-damaging content
- Out-of-scope requests

## The Solution

Guardrails run at specific stages of agent execution:

1. **Input guardrails** — Validate user messages before they reach the LLM
2. **Action guardrails** — Validate tool calls before execution
3. **Output guardrails** — Validate responses before returning to users

```python
from syrin import Agent, Model
from syrin.guardrails import (
    PIIScanner,
    ContentFilter,
    LengthGuardrail,
    GuardrailStage,
)

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    system_prompt="You are a helpful customer support agent.",
    guardrails={
        GuardrailStage.INPUT: [
            ContentFilter(blocked_words=["password", "secret", "admin"]),
            LengthGuardrail(min_length=1, max_length=5000),
        ],
        GuardrailStage.OUTPUT: [
            PIIScanner(redact=True),
        ],
    },
)
```

**What just happened:** We configured input guardrails to block certain words and enforce length limits. Output guardrails scan for PII and redact it automatically.

## Built-in Guardrails

Syrin ships with a comprehensive set of built-in guardrails:

### PIIScanner

Detects and optionally redacts personally identifiable information:

```python
from syrin.guardrails import PIIScanner

guardrail = PIIScanner(
    redact=True,                    # Replace PII with asterisks
    redaction_char="*",
    allow_types=["ip_address"],     # Don't block IP addresses
    custom_patterns={               # Add your own patterns
        "customer_id": (r"CID-\d{6}", "Customer ID"),
    },
)
```

**Detects:** Email addresses, phone numbers, SSNs, credit cards, IP addresses.

### ContentFilter

Block specific words or phrases:

```python
from syrin.guardrails import ContentFilter

guardrail = ContentFilter(
    blocked_words=["password", "secret", "api_key", "confidential"],
    case_sensitive=False,  # "PASSWORD" would also be blocked
)
```

### LengthGuardrail

Enforce minimum and maximum text lengths:

```python
from syrin.guardrails import LengthGuardrail

guardrail = LengthGuardrail(
    min_length=5,    # Reject one-word inputs
    max_length=1000, # Prevent abuse with huge payloads
)
```

### FactVerificationGuardrail

Verify claims against grounded facts:

```python
from syrin.guardrails import FactVerificationGuardrail

guardrail = FactVerificationGuardrail(
    confidence_threshold=0.8,
    fail_on_unverified=True,
)
```

### CitationGuardrail

Ensure responses cite their sources:

```python
from syrin.guardrails import CitationGuardrail

guardrail = CitationGuardrail(
    require_citations=True,
    min_sources=1,
)
```

### BudgetEnforcer

Prevent runaway costs at the guardrail level:

```python
from syrin.guardrails import BudgetEnforcer

guardrail = BudgetEnforcer(
    max_cost_per_run=0.50,
)
```

## Custom Guardrails

For specialized validation, implement the `Guardrail` abstract class:

```python
from syrin.guardrails import Guardrail, GuardrailContext, GuardrailDecision

class DomainValidator(Guardrail):
    def __init__(self, allowed_domains: list[str]):
        super().__init__("domain_validator")
        self.allowed_domains = allowed_domains

    async def evaluate(self, context: GuardrailContext) -> GuardrailDecision:
        text = context.text.lower()
        
        # Check if any disallowed domain is mentioned
        for domain in self.allowed_domains:
            if domain in text:
                return GuardrailDecision(
                    passed=True,
                    rule="domain_allowed",
                )
        
        return GuardrailDecision(
            passed=False,
            rule="domain_blocked",
            reason="Query must relate to allowed domains",
            alternatives=["Ask about product features, pricing, or support"],
        )
```

**What just happened:** We created a custom guardrail that validates whether queries relate to allowed domains. The agent only answers questions about products, pricing, or support.

## Guardrail Results

Every guardrail returns a `GuardrailDecision` with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `passed` | `bool` | Whether the check passed |
| `rule` | `str` | Identifier for the rule that triggered |
| `reason` | `str` | Human-readable explanation |
| `confidence` | `float` | Confidence score (0-1) |
| `metadata` | `dict` | Additional context |
| `alternatives` | `list[str]` | Suggestions for the user |

When a guardrail fails, Syrin:

1. Emits the `GUARDRAIL_BLOCKED` hook
2. Populates the run report with failure details
3. Returns a blocked response to the user

## Hooks for Observability

Guardrails integrate with Syrin's observability system:

```python
agent.events.on("guardrail.blocked", lambda e: print(f"Blocked: {e['reason']}"))
agent.events.on("guardrail.input", lambda e: print(f"Input guardrails ran: {e['guardrail_count']}"))
agent.events.on("guardrail.output", lambda e: print(f"Output guardrails ran: {e['guardrail_count']}"))
```

Every guardrail execution creates a trace span with:

- Stage (input/output/action)
- Pass/fail status
- Violation reason if blocked

## Runtime Configuration

Enable or disable guardrails dynamically:

```python
# Disable a specific guardrail at runtime
agent._guardrails_disabled.add("content_filter")

# Re-enable it
agent._guardrails_disabled.discard("content_filter")
```

## Configuration Table

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Custom guardrail name |
| `stage` | `GuardrailStage` | When to run (input/output/action) |
| `budget_cost` | `float` | Cost in USD to run this guardrail |

---

## What's Next?

- [Checkpoints](/agent/checkpoints) — Save and restore agent state
- [Error Handling](/agent/error-handling) — Handle failures gracefully
- [Tools](/agent/tools) — Give your agent abilities

## See Also

- [Core Concepts: Budget](/core/budget) — Cost control fundamentals
- [Debugging: Hooks Reference](/debugging/hooks-reference) — Complete hook documentation
- [Production: Serving](/production/serving) — Deploy agents with guardrails
