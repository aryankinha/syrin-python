---
title: PIIGuardrail
description: Standalone regex-based PII scanner with configurable action and lifecycle hooks
weight: 60
---

## What It Does

`PIIGuardrail` scans text for personally identifiable information — SSNs, emails, phone numbers, credit cards, IP addresses — and either redacts it, blocks the request, or logs it for audit. No LLM calls, no network requests. It's purely regex-based, with Luhn validation for credit card numbers and octet-range validation for IP addresses.

## Quick Start

```python
from syrin.security import PIIGuardrail, PIIAction, PIIEntityType

guard = PIIGuardrail(
    detect=[PIIEntityType.SSN, PIIEntityType.EMAIL],
    action=PIIAction.REDACT,
)

result = guard.scan("My SSN is 123-45-6789, email me at foo@example.com")
print(result.redacted_text)
# My SSN is [REDACTED], email me at [REDACTED]
```

## Entity Types

Five types of PII are detected out of the box.

`PIIEntityType.SSN` matches US Social Security Numbers in `XXX-XX-XXXX` format.

`PIIEntityType.EMAIL` matches email addresses.

`PIIEntityType.PHONE` matches US phone numbers.

`PIIEntityType.CREDIT_CARD` matches credit card numbers and validates them with the Luhn algorithm, so fake numbers don't trip the scanner.

`PIIEntityType.IP_ADDRESS` matches IPv4 addresses with octet-range validation (0–255 per octet).

When `detect` is omitted, all five types are enabled.

## Actions

Three actions control what happens when PII is found.

`PIIAction.REDACT` (the default) replaces every match with `[REDACTED]`. The result is in `result.redacted_text`.

`PIIAction.REJECT` doesn't modify the text — it sets `result.should_block = True`, signaling that the request should be blocked. Use this in an input guardrail to stop PII-containing messages from reaching the LLM.

`PIIAction.AUDIT` logs findings into `result.audit_entries` without blocking or modifying text. Use this to build a PII audit trail without affecting the user experience.

## Checking the Result

```python
from syrin.security import PIIGuardrail, PIIAction, PIIEntityType

guard = PIIGuardrail(
    detect=[PIIEntityType.EMAIL, PIIEntityType.PHONE],
    action=PIIAction.REDACT,
)

result = guard.scan("Call me at 555-123-4567 or email alice@example.com")

print(f"PII found: {result.found}")               # True
print(f"Redacted: {result.redacted_text}")         # Call me at [REDACTED] or email [REDACTED]
print(f"Should block: {result.should_block}")      # False (REDACT mode, not REJECT)
print(f"Audit entries: {result.audit_entries}")   # [] (only populated in AUDIT mode)
print(f"Findings: {result.findings}")              # List of PIIFinding objects
```

`PIIScanResult` has five fields:

`found` — `True` if any PII was detected.

`findings` — A list of `PIIFinding` objects, each with the entity type and position in the text.

`redacted_text` — The text with PII replaced by `[REDACTED]`. Only populated when `action=PIIAction.REDACT`.

`should_block` — `True` when `action=PIIAction.REJECT` and PII was found.

`audit_entries` — A list of log-ready strings. Only populated when `action=PIIAction.AUDIT`.

## Blocking Requests

Use REJECT mode to stop PII-containing requests before they reach the LLM:

```python
from syrin.security import PIIGuardrail, PIIAction

guard = PIIGuardrail(action=PIIAction.REJECT)
result = guard.scan(user_input)

if result.should_block:
    return "Your message contained personal information and was not processed."
```

## Hooks

Pass a `fire_event_fn` to receive lifecycle events when PII is found:

```python
from syrin.enums import Hook
from syrin.security import PIIGuardrail, PIIAction

def on_event(hook: Hook, ctx: dict) -> None:
    print(f"[{hook}] {ctx}")

guard = PIIGuardrail(action=PIIAction.REJECT, fire_event_fn=on_event)
result = guard.scan("Call me at 555-123-4567")
# [pii.detected] {'count': 1, 'entity_types': ['phone']}
# [pii.blocked] {'blocked_count': 1}

print(result.should_block)  # True
```

Four hooks fire for PII events:

`Hook.PII_DETECTED` fires whenever any PII is found, regardless of action.

`Hook.PII_REDACTED` fires when `action=REDACT` and PII was found.

`Hook.PII_BLOCKED` fires when `action=REJECT` and PII was found.

`Hook.PII_AUDIT` fires when `action=AUDIT` and PII was found.

## Using PIIGuardrail as an Agent Guardrail

The standalone `PIIGuardrail` is for scanning text directly. To integrate it into an agent's guardrail pipeline, use `PIIScanner` from `syrin.guardrails`:

```python
from syrin import Agent, Model
from syrin.guardrails import PIIScanner

agent = Agent(
    model=Model.mock(),
    guardrails=[
        PIIScanner(redact=True),  # Redact PII in inputs before LLM sees them
    ],
)
```

See [Guardrails](/agent/guardrails) for the full guardrail pipeline.

## See Also

- [Guardrails](/agent/guardrails) — The agent guardrail pipeline
- [Security: Agent Identity](/security/agent-identity) — Sign and verify agent messages
- [Hooks Reference](/debugging/hooks-reference) — All 182 hooks
