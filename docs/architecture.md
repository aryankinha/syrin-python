# Syrin Architecture: Agent vs Standalone Components

This document clarifies which components **require an Agent** and which can be used **standalone** (without an agent).

---

## Quick Reference

| I want to... | Where to look |
|--------------|---------------|
| Call an LLM without an agent | [Models Guide](models.md) — `model.complete(messages)` |
| Build an agent | [Agent Documentation](agent/README.md) |
| Use guardrails on arbitrary text | [Guardrails](guardrails.md) — `GuardrailChain.evaluate()` |
| Trace spans without an agent | [Observability](observability.md) |
| Manage budget state | [Budget Control](budget-control.md) — `BudgetStore` |
| Configure an agent's budget | [Agent: Budget](agent/budget.md) |

---

## Agent-Only Components

These require an `Agent` and cannot be used standalone:

| Component | Description |
|-----------|-------------|
| **Agent** | Core agent class |
| **Loop** | ReactLoop, SingleShotLoop, etc. — execution loops used internally by Agent |
| **Events / Hooks** | `agent.events`, lifecycle hooks (Hook.BEFORE_RESPONSE, etc.) |
| **Response** | Return type of `agent.response()` |
| **Handoff / Spawn** | `handoff()`, `spawn()`, `spawn_parallel()` |
| **Pipeline, AgentTeam, DynamicPipeline** | Multi-agent orchestration |
| **Checkpoint API** | `save_checkpoint()`, `load_checkpoint()` — agent state only |
| **ConversationMemory** | In-session history managed by the agent |
| **Tools (execution)** | Tool *execution* happens inside the agent loop |

**Docs:** [Agent Documentation](agent/README.md)

---

## Standalone Components

These work **without an Agent**:

| Component | Standalone use |
|-----------|----------------|
| **Model** | `model.complete(messages)` or `await model.acomplete(messages)` |
| **Pipe** | `pipe(value, f1, f2).result()` — data flow pipeline |
| **BudgetStore** | Store and retrieve budget state across runs |
| **Cost** | `calculate_cost()`, `ModelPricing` |
| **Tool (definition)** | `@tool` decorator creates `ToolSpec` |
| **Prompt** | `PromptTemplate`, `@prompt` decorator |
| **GuardrailChain** | Evaluate input/output directly with `GuardrailContext` |
| **Observability** | `get_tracer()`, `Span`, exporters |
| **Memory backends** | Redis, Chroma, SQLite, etc. — storage layer |
| **Config** | `configure()`, `get_config()` |
| **Output** | Model-level structured output configuration |
| **Validation** | `ValidationPipeline` |
| **Checkpoint backend** | `Checkpointer`, `CheckpointConfig` — storage layer |

**Docs:** [Models](models.md), [Guardrails](guardrails.md), [Observability](observability.md), [Budget Control](budget-control.md)

---

## Shared Components

These have **both** standalone and agent-integrated usage:

| Component | Standalone | Agent integration |
|-----------|------------|-------------------|
| **Budget** | `BudgetStore` get/save | Agent `budget=` param, `budget_summary` |
| **Guardrails** | `GuardrailChain.evaluate()` | Agent `guardrails=` param |
| **Memory (persistent)** | Backends, `MemoryConfig` | Agent `remember()`, `recall()`, `forget()` |
| **Rate limit** | `APIRateLimit` config, backends | Agent `rate_limit=` param |
| **Structured output** | Model `output=` | Agent `output=` param |
| **Context** | Token counting, compaction | Agent `context=` param |
| **Checkpoint** | `Checkpointer`, `CheckpointConfig` | Agent `checkpoint=` param, `save_checkpoint()` |

**Strategy:** Root docs cover the component, config, and standalone usage. Agent docs cover how the agent integrates it.

| Topic | Root doc | Agent doc |
|-------|----------|-----------|
| Model | [models.md](models.md) | [agent/model.md](agent/model.md) |
| Budget | [budget-control.md](budget-control.md) | [agent/budget.md](agent/budget.md) |
| Memory | [memory.md](memory.md) | [agent/memory.md](agent/memory.md) |
| Guardrails | [guardrails.md](guardrails.md) | [agent/guardrails.md](agent/guardrails.md) |
| Checkpoint | [checkpoint.md](checkpoint.md) | [agent/checkpointing.md](agent/checkpointing.md) |
| Structured output | [structured-output.md](structured-output.md) | [agent/structured-output.md](agent/structured-output.md) |
| Rate limit | [ratelimit.md](ratelimit.md) | [agent/rate-limiting.md](agent/rate-limiting.md) |
