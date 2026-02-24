# Guardrails

> **Full guide:** For GuardrailChain, built-in guardrails, standalone `evaluate()`, and authority/intelligence layers, see [Guardrails](../guardrails.md).

Validate input and output before and after processing.

## Basic Usage

```python
from syrin import Agent
from syrin.guardrails import BlockedWordsGuardrail

agent = Agent(
    model=model,
    guardrails=[BlockedWordsGuardrail(["spam", "offensive"])],
)
```

## Built-in Guardrails

- **BlockedWordsGuardrail** — Block inputs containing specific words
- **LengthGuardrail** — Enforce min/max length

## Custom Guardrail

Implement the `Guardrail` interface:

```python
from syrin.guardrails import Guardrail
from syrin.guardrails.decision import GuardrailDecision

class MyGuardrail(Guardrail):
    name = "my_guardrail"

    async def evaluate(self, context):
        if "blocked" in context.text.lower():
            return GuardrailDecision(
                passed=False,
                action="block",
                reason="Contains blocked content",
            )
        return GuardrailDecision(passed=True, action="allow")
```

## Behavior

- **Input guardrails** run before processing.
- **Output guardrails** run on the final text when there are no tool calls.
- On failure: response with empty content and `stop_reason=GUARDRAIL`.

## Hooks

- `GUARDRAIL_INPUT` — Input check
- `GUARDRAIL_OUTPUT` — Output check
- `GUARDRAIL_BLOCKED` — When a guardrail blocks

## Report

`response.report.guardrail` contains:

- `input_passed`, `output_passed`
- `blocked`, `blocked_stage`
- `input_reason`, `output_reason`
- `input_guardrails`, `output_guardrails`

## See Also

- [Guardrails](../guardrails.md) — Full guide, built-ins, standalone evaluation
