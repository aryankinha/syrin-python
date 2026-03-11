# Response Object

`agent.response()` and `agent.arun()` return a `Response` object with content, metadata, and reports.

## Basic Usage

```python
response = agent.response("Hello")
print(response.content)   # Text output
print(response.cost)      # Cost in USD
print(response.tokens)    # TokenUsage
print(response.model)     # Model ID used
```

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `content` | `T` (usually `str`) | Main text output |
| `raw` | `str` | Raw text (same as content for text) |
| `cost` | `float` | Cost in USD |
| `tokens` | `TokenUsage` | Input/output/total tokens |
| `model` | `str` | Model identifier |
| `routing_reason` | `RoutingReason \| None` | When routing: why model was chosen (selected_model, task_type, reason, cost_estimate, etc.) |
| `model_used` | `str \| None` | When routing/provider reports: actual model ID used (e.g. OpenRouter header) |
| `task_type` | `TaskType \| None` | When routing: detected or overridden task type |
| `actual_cost` | `float \| None` | When provider reports: actual cost (e.g. OpenRouter `x-openrouter-total-cost`) |
| `duration` | `float` | Duration in seconds |
| `budget_remaining` | `float \| None` | Remaining budget |
| `budget_used` | `float \| None` | Budget used |
| `trace` | `list[TraceStep]` | Per-step trace |
| `tool_calls` | `list` | Tool calls made |
| `stop_reason` | `StopReason` | Why the run stopped |
| `parsed` | `object \| None` | Convenience: parsed structured output (same as `structured.parsed`) |
| `structured` | `StructuredOutput \| None` | Parsed structured output |
| `template_data` | `dict \| None` | Slot values when `output_config.template` is used |
| `file` | `Path \| None` | Path to generated file when output_config format is TEXT/MARKDOWN/HTML/PDF/DOCX |
| `file_bytes` | `bytes \| None` | Raw bytes of generated file |
| `citations` | `list[Citation]` | Parsed citations when `output_config.citation` is set; empty otherwise |
| `raw_response` | `Any` | Provider raw response; parsed Pydantic for structured output |
| `iterations` | `int` | Loop iterations |
| `report` | `AgentReport` | Run metrics and sub-reports |

**Routing metadata** — When using Agent with `model=[...]` and `model_router`, the response includes `routing_reason`, `model_used`, `task_type`, and `actual_cost` (when the provider reports it). See [Routing](../routing.md).

## String Conversion

`str(response)` returns `response.content`:

```python
response = agent.response("Hello")
print(response)  # Same as print(response.content)
```

## Boolean Check

`bool(response)` is `True` when `stop_reason == StopReason.END_TURN` (finished normally).

```python
if response:
    print("Completed successfully")
else:
    print(f"Stopped: {response.stop_reason}")
```

## StopReason

| Value | Meaning |
|-------|---------|
| `END_TURN` | Normal completion |
| `BUDGET` | Budget limit reached |
| `MAX_ITERATIONS` | Hit iteration cap |
| `TIMEOUT` | Timeout |
| `TOOL_ERROR` | Tool failure |
| `HANDOFF` | Handed off to another agent |
| `GUARDRAIL` | Blocked by guardrail |
| `CANCELLED` | Cancelled |

## Structured Output

When using `output=Output(MyModel)`:

```python
response = agent.response("Extract user info: John, 30, john@example.com")
print(response.structured.parsed)   # MyModel instance
print(response.structured.raw)      # Raw JSON
print(response.data)                # dict (alias for _data)
```

See [Structured Output](structured-output.md).

## Budget Property

`response.budget` returns a `BudgetStatus` object:

```python
status = response.budget
print(status.remaining)
print(status.used)
print(status.total)
print(status.cost)
```

## AgentReport

`response.report` aggregates metrics for the run:

| Sub-report | Description |
|------------|-------------|
| `report.guardrail` | Guardrail results |
| `report.context` | Context usage |
| `report.memory` | Memory operations |
| `report.tokens` | Token usage |
| `report.output` | Output validation |
| `report.ratelimits` | Rate limit checks |
| `report.checkpoints` | Checkpoint saves/loads |

```python
print(response.report.tokens.total_tokens)
print(response.report.guardrail.input_passed)
print(response.report.memory.recalls)
```

## TraceStep

Each step in `response.trace`:

| Field | Type | Description |
|-------|------|-------------|
| `step_type` | `str` | e.g. `"llm"` |
| `timestamp` | `float` | Unix timestamp |
| `model` | `str` | Model used |
| `tokens` | `int` | Tokens for step |
| `cost_usd` | `float` | Cost for step |
| `latency_ms` | `float` | Step duration |
| `extra` | `dict` | Additional data |

## TokenUsage

`response.tokens` (and `StreamChunk.tokens_so_far`):

| Field | Type | Description |
|-------|------|-------------|
| `input_tokens` | `int` | Prompt tokens |
| `output_tokens` | `int` | Completion tokens |
| `total_tokens` | `int` | input + output |
