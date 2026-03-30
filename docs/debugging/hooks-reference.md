---
title: Hooks Reference
description: Complete reference for all lifecycle hooks and their context
weight: 172
---

## Complete Hook Reference

Every lifecycle moment in Syrin emits a hook. This reference documents all hooks, when they fire, and what context they provide.

## Hook Categories

- [Agent Lifecycle](#agent-lifecycle)
- [LLM Calls](#llm-calls)
- [Tool Execution](#tool-execution)
- [Budget](#budget)
- [Memory](#memory)
- [Handoff & Spawn](#handoff--spawn)
- [Checkpoint](#checkpoint)
- [Context Management](#context-management)
- [Rate Limiting](#rate-limiting)
- [Guardrails](#guardrails)
- [Pipeline](#pipeline)
- [Serving](#serving)

---

## Agent Lifecycle

### `AGENT_INIT`

Fires when the agent is initialized.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `agent_name` | `str` | Agent class name |
| `model` | `str` | Model ID |

### `AGENT_RUN_START`

Fires when `agent.run()` begins.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `input` | `str` | User input |
| `model` | `str` | Model ID |
| `iteration` | `int` | Current loop iteration |

### `AGENT_RUN_END`

Fires when `agent.run()` completes.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `input` | `str` | User input |
| `output` | `str` | Final output |
| `content` | `str` | Response content (alias for output) |
| `cost` | `float` | Total cost in USD |
| `tokens` | `int` | Total tokens |
| `duration` | `float` | Duration in seconds |
| `stop_reason` | `str` | Why the run ended |
| `iteration` | `int` | Final iteration count |

### `AGENT_RESET`

Fires when `agent.reset()` is called.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| *(empty)* | | No additional context |

---

## LLM Calls

### `LLM_REQUEST_START`

Fires before sending request to the LLM.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `iteration` | `int` | Current iteration |
| `model` | `str` | Model ID |
| `temperature` | `float` | Temperature setting |
| `tools` | `list` | Available tools |
| `tool_count` | `int` | Number of tools |

**Before hook can modify:** `temperature`, `max_tokens`, custom fields.

### `LLM_REQUEST_END`

Fires after receiving response from the LLM.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `content` | `str` | Response content |
| `tokens` | `dict` | Token counts (`input`, `output`, `total`) |
| `cost` | `float` | Cost for this call |
| `duration_ms` | `float` | Call duration in milliseconds |
| `stop_reason` | `str` | Stop reason from model |
| `iteration` | `int` | Current iteration |

### `LLM_STREAM_CHUNK`

Fires for each streamed token (when streaming enabled).

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `text` | `str` | New text chunk |
| `accumulated` | `str` | All accumulated text |
| `index` | `int` | Chunk index |

### `LLM_RETRY`

Fires when an LLM call is retried.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `attempt` | `int` | Retry attempt number |
| `error` | `str` | Error that caused retry |
| `iteration` | `int` | Current iteration |

### `LLM_FALLBACK`

Fires when switching to a fallback model.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `primary_model` | `str` | Failed model |
| `fallback_model` | `str` | New model |
| `reason` | `str` | Why fallback triggered |

---

## Tool Execution

### `TOOL_CALL_START`

Fires before a tool executes.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Tool name |
| `arguments` | `dict` | Tool arguments |
| `iteration` | `int` | Current iteration |

### `TOOL_CALL_END`

Fires after a tool completes.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Tool name |
| `arguments` | `dict` | Tool arguments |
| `result` | `Any` | Tool result |
| `duration_ms` | `float` | Execution time in ms |
| `iteration` | `int` | Current iteration |

### `TOOL_ERROR`

Fires when a tool raises an exception.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Tool name |
| `error` | `str` | Error message |
| `iteration` | `int` | Current iteration |

---

## Budget

### `BUDGET_CHECK`

Fires before each budget check.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `limit` | `float` | Budget limit |
| `spent` | `float` | Amount spent |
| `remaining` | `float` | Remaining budget |

### `BUDGET_THRESHOLD`

Fires when reaching a budget threshold.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `threshold_percent` | `int` | Threshold percentage (e.g., 80) |
| `current_value` | `float` | Current spend |
| `limit_value` | `float` | Budget limit |
| `metric` | `str` | Metric being tracked |

### `BUDGET_EXCEEDED`

Fires when budget is exhausted.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `used` | `float` | Amount used |
| `limit` | `float` | Budget limit |
| `exceeded_by` | `float` | Amount over limit |

---

## Memory

### `MEMORY_STORE`

Fires when content is stored in memory.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `content` | `str` | Stored content |
| `memory_type` | `str` | Memory type (core, episodic, semantic, procedural) |

### `MEMORY_RECALL`

Fires when memories are retrieved.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `query` | `str` | Recall query |
| `memories` | `list` | Retrieved memories |
| `count` | `int` | Number retrieved |

### `MEMORY_FORGET`

Fires when memories are forgotten.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `forgotten_count` | `int` | Number forgotten |
| `reason` | `str` | Why memories were forgotten |

### `MEMORY_CONSOLIDATE`

Fires during memory consolidation.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `consolidated_count` | `int` | Number consolidated |

---

## Handoff & Spawn

### `HANDOFF_START`

Fires when one agent hands off to another.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `source_agent` | `str` | Source agent class |
| `target_agent` | `str` | Target agent class |
| `task` | `str` | Task for target agent |
| `mem_count` | `int` | Memories being transferred |
| `transfer_budget` | `bool` | Whether budget is shared |

### `HANDOFF_END`

Fires when handoff completes.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `target_agent` | `str` | Target agent class |
| `success` | `bool` | Whether handoff succeeded |
| `cost` | `float` | Cost of handoff |
| `duration` | `float` | Duration in seconds |

### `HANDOFF_BLOCKED`

Fires when a handoff is blocked by a before handler.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `source_agent` | `str` | Source agent |
| `target_agent` | `str` | Target agent |
| `reason` | `str` | Why blocked |

### `SPAWN_START`

Fires when spawning a child agent.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `child_agent` | `str` | Child agent class |
| `parent_agent` | `str` | Parent agent class |
| `task` | `str` | Task for child |
| `parent_context_tokens` | `int` | Parent context size |

### `SPAWN_END`

Fires when spawn completes.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `child_agent` | `str` | Child agent class |
| `success` | `bool` | Whether spawn succeeded |

---

## Checkpoint

### `CHECKPOINT_SAVE`

Fires when a checkpoint is saved.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `checkpoint_id` | `str` | Checkpoint identifier |
| `reason` | `str` | Why checkpoint was saved |
| `iteration` | `int` | Loop iteration |

### `CHECKPOINT_LOAD`

Fires when loading from a checkpoint.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `checkpoint_id` | `str` | Checkpoint identifier |

---

## Context Management

### `CONTEXT_COMPACT` / `CONTEXT_COMPACT`

Fires when context is compacted.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `method` | `str` | Compaction method |
| `tokens_before` | `int` | Tokens before |
| `tokens_after` | `int` | Tokens after |
| `messages_before` | `int` | Messages before |
| `messages_after` | `int` | Messages after |

### `CONTEXT_THRESHOLD`

Fires when a context threshold is crossed.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `at` | `int` | Threshold percentage |
| `at_range` | `tuple` | Threshold range |
| `percent` | `int` | Current percentage |
| `tokens` | `int` | Token count |
| `max_tokens` | `int` | Max tokens |

### `CONTEXT_SNAPSHOT`

Fires after each context prepare.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `snapshot` | `dict` | Full context snapshot |
| `utilization_pct` | `float` | Context utilization |

---

## Rate Limiting

### `RATELIMIT_CHECK`

Fires when checking rate limits.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `allowed` | `bool` | Whether request is allowed |
| `reason` | `str` | Reason if not allowed |

### `RATELIMIT_THRESHOLD`

Fires when approaching rate limit.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `at` | `int` | Threshold percentage |
| `percent` | `int` | Current percentage |
| `metric` | `str` | Metric (rpm, tpm, rpd) |
| `used` | `int` | Current usage |
| `limit` | `int` | Limit |

### `RATELIMIT_EXCEEDED`

Fires when rate limit is hit.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `metric` | `str` | Metric that exceeded |
| `used` | `int` | Current usage |
| `limit` | `int` | Limit |

---

## Guardrails

### `GUARDRAIL_INPUT`

Fires before input guardrails.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `input` | `str` | User input |
| `stage` | `str` | "input" |

### `GUARDRAIL_OUTPUT`

Fires before output guardrails.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `output` | `str` | Agent output |
| `stage` | `str` | "output" |

### `GUARDRAIL_BLOCKED`

Fires when guardrail blocks content.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `stage` | `str` | "input" or "output" |
| `reason` | `str` | Why blocked |
| `guardrail_names` | `list` | Blocking guardrails |

---

## Pipeline

### `PIPELINE_START`

Fires when pipeline execution starts.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `task` | `str` | Pipeline task |

### `PIPELINE_END`

Fires when pipeline completes.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `total_cost` | `float` | Total cost |
| `duration` | `float` | Total duration |

### `PIPELINE_AGENT_START`

Fires when pipeline starts an agent step.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `agent_type` | `str` | Agent class |
| `step` | `int` | Step number |

### `PIPELINE_AGENT_COMPLETE`

Fires when pipeline agent step completes.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `agent_type` | `str` | Agent class |
| `step` | `int` | Step number |
| `cost` | `float` | Step cost |

---

## Serving

### `SERVE_REQUEST_START`

Fires when HTTP request received.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `path` | `str` | Request path |
| `method` | `str` | HTTP method |

### `SERVE_REQUEST_END`

Fires when HTTP request completes.

**Context:**
| Field | Type | Description |
|-------|------|-------------|
| `path` | `str` | Request path |
| `status` | `int` | HTTP status |
| `duration_ms` | `float` | Request duration |

---

## Using This Reference

### Example: Log All Tool Calls with Full Context

```python
from syrin import Agent, Hook, Model

agent = Agent(model=Model.Almock())


def detailed_tool_logging(ctx):
    print(f"Tool: {ctx.name}")
    print(f"  Arguments: {json.dumps(ctx.arguments, indent=2)}")
    print(f"  Duration: {ctx.duration_ms}ms")
    if ctx.get("result"):
        print(f"  Result: {str(ctx.result)[:200]}")


def tool_error_logging(ctx):
    print(f"Tool FAILED: {ctx.name}")
    print(f"  Error: {ctx.error}")


agent.events.on(Hook.TOOL_CALL_END, detailed_tool_logging)
agent.events.on(Hook.TOOL_ERROR, tool_error_logging)
```

### Example: Budget Health Dashboard

```python
def dashboard_update(ctx):
    percent = ctx.threshold_percent
    if percent >= 90:
        status = "CRITICAL"
    elif percent >= 75:
        status = "WARNING"
    else:
        status = "OK"

    dashboard.update(
        metric="budget",
        value=percent,
        status=status,
        spent=ctx.current_value,
        limit=ctx.limit_value,
    )


agent.events.on(Hook.BUDGET_THRESHOLD, dashboard_update)
```

## See Also

- [Debugging Overview](/agent-kit/debugging/overview) — Introduction to observability
- [Hooks](/agent-kit/debugging/hooks) — Hooks usage patterns
- [Audit Logging](/agent-kit/debugging/logging) — Persist events to files
- [Playground](/agent-kit/production/playground) — Visual observability panel
