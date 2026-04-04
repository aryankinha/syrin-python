---
title: Hooks Reference
description: All 182 lifecycle hooks — what fires them, and what context they carry
weight: 172
---

## How to Read This Reference

Every hook is a `Hook` enum value. Subscribe with `agent.events.on(Hook.NAME, callback)`. The callback receives a context dictionary. This page lists every hook, when it fires, and what keys are in that dictionary.

For a conceptual introduction and code examples, see [Hooks & Events](/agent-kit/debugging/hooks).

## Subscribe to Any Hook

```python
from syrin import Agent, Model
from syrin.enums import Hook

agent = Agent(model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"), system_prompt="You are helpful.")
# model = Model.mock()  # no API key needed for testing

# Subscribe to one hook
agent.events.on(Hook.AGENT_RUN_END, lambda ctx: print(f"Cost: ${ctx['cost']:.6f}"))

# Subscribe to everything (useful for debugging)
agent.events.on_all(lambda hook, ctx: print(f"[{hook}] {list(ctx.keys())}"))

agent.run("Hello!")
```

---

## Agent Lifecycle (14 hooks)

**`Hook.AGENT_INIT`** — Fires when the agent is instantiated.
- `ctx['agent_name']` — the agent class name
- `ctx['model']` — the model ID

**`Hook.AGENT_RUN_START`** — Fires when `agent.run()` begins.
- `ctx['input']` — the user's input text
- `ctx['model']` — the model being used
- `ctx['iteration']` — loop iteration count (0 for first call)

**`Hook.AGENT_RUN_END`** — Fires when `agent.run()` is about to return.
- `ctx['input']` — the original input
- `ctx['content']` — the final response text
- `ctx['cost']` — total USD cost of the entire run
- `ctx['tokens']` — total token count
- `ctx['duration']` — wall-clock seconds
- `ctx['stop_reason']` — why the agent stopped (e.g. `"end_turn"`, `"budget"`)
- `ctx['iterations']` — how many LLM calls were made

**`Hook.AGENT_RESET`** — Fires when `agent.reset()` clears conversation history. No context keys.

**`Hook.AGENT_JOINED_SWARM`** — Agent joined a swarm topology.
- `ctx['swarm_name']` — the swarm name
- `ctx['agent_name']` — this agent's name

**`Hook.AGENT_LEFT_SWARM`** — Agent left a swarm topology.
- `ctx['swarm_name']` — the swarm name

**`Hook.AGENT_FAILED`** — An agent in a multi-agent system failed.
- `ctx['agent_name']` — which agent failed
- `ctx['error']` — the error message

**`Hook.AGENT_REGISTERED`** — Agent registered in an agent registry.
- `ctx['agent_name']` — the agent name

**`Hook.AGENT_UNREGISTERED`** — Agent removed from a registry.
- `ctx['agent_name']` — the agent name

**`Hook.AGENT_ESCALATION`** — An agent escalated a task to a parent.
- `ctx['from_agent']` — source agent
- `ctx['reason']` — escalation reason

**`Hook.AGENT_BROADCAST`** — An agent sent a broadcast message.
- `ctx['message']` — the broadcast content

**`Hook.AGENT_PERMISSION_DENIED`** — An agent attempted an unauthorized action.
- `ctx['action']` — what was attempted

**`Hook.AGENT_CONTROL_ACTION`** — A control action was applied (pause, resume, cancel).
- `ctx['action']` — the action name

**`Hook.AGENT_DELEGATION`** — An agent delegated a task.
- `ctx['from_agent']` — delegating agent
- `ctx['to_agent']` — receiving agent

---

## LLM Calls (5 hooks)

**`Hook.LLM_REQUEST_START`** — Fires just before an LLM API call.
- `ctx['model']` — the model ID
- `ctx['message_count']` — number of messages in the request

**`Hook.LLM_REQUEST_END`** — Fires after every LLM response.
- `ctx['content']` — the text the LLM generated
- `ctx['cost']` — USD cost of this specific LLM call
- `ctx['tokens']` — token count object
- `ctx['input_tokens']` — tokens in the prompt
- `ctx['output_tokens']` — tokens in the response
- `ctx['model']` — model used for this call

**`Hook.LLM_STREAM_CHUNK`** — Fires for each streaming chunk.
- `ctx['text']` — the text in this chunk
- `ctx['accumulated_text']` — all text so far
- `ctx['is_final']` — whether this is the last chunk

**`Hook.LLM_RETRY`** — Fires when an LLM call fails and is being retried.
- `ctx['attempt']` — which retry attempt (1-based)
- `ctx['error']` — the error that triggered the retry

**`Hook.LLM_FALLBACK`** — Fires when the primary model fails and the fallback model is used.
- `ctx['primary_model']` — the model that failed
- `ctx['fallback_model']` — the model being tried

---

## Tool Execution (6 hooks)

**`Hook.TOOL_CALL_START`** — Fires before a tool is executed.
- `ctx['tool_name']` — the tool's name
- `ctx['arguments']` — the arguments the LLM passed

**`Hook.TOOL_CALL_END`** — Fires after a tool returns.
- `ctx['tool_name']` — the tool's name
- `ctx['result']` — what the tool returned
- `ctx['duration']` — how long the tool took in seconds

**`Hook.TOOL_ERROR`** — Fires when a tool raises an exception.
- `ctx['tool_name']` — the tool that failed
- `ctx['error']` — the error message

**`Hook.TOOL_OUTPUT_SUSPICIOUS`** — A tool returned output flagged as suspicious.
- `ctx['tool_name']` — the tool name
- `ctx['reason']` — why it was flagged

**`Hook.TOOL_OUTPUT_BLOCKED`** — A tool's output was blocked before being returned to the LLM.
- `ctx['tool_name']` — the tool name

**`Hook.TOOL_OUTPUT_SANITIZED`** — A tool's output was sanitized before being returned.
- `ctx['tool_name']` — the tool name

---

## Budget (5 hooks + 1)

**`Hook.BUDGET_CHECK`** — Fires on every budget check (before each LLM call).
- `ctx['spent']` — amount spent so far
- `ctx['limit']` — the budget limit
- `ctx['remaining']` — how much is left

**`Hook.BUDGET_THRESHOLD`** — Fires when spending crosses a threshold percentage.
- `ctx['percentage']` — what percentage has been spent (e.g. `80.0`)
- `ctx['spent']` — USD spent
- `ctx['remaining']` — USD remaining
- `ctx['limit']` — the budget limit

**`Hook.BUDGET_EXCEEDED`** — Fires when the budget limit is hit.
- `ctx['limit']` — the configured limit
- `ctx['spent']` — how much was spent
- `ctx['budget_type']` — which limit was hit (`"run"`, `"daily"`, etc.)

**`Hook.BUDGET_FORECAST`** — Fires when budget forecasting predicts overage.
- `ctx['projected']` — projected total spend
- `ctx['limit']` — the budget limit

**`Hook.BUDGET_ANOMALY`** — Fires when a sudden cost spike is detected.
- `ctx['spike_amount']` — the anomalous cost increase
- `ctx['threshold']` — the spike threshold

**`Hook.DAILY_LIMIT_APPROACHING`** — Fires when the daily rate limit is nearly reached.
- `ctx['spent_today']` — amount spent today
- `ctx['daily_limit']` — the daily limit

---

## Memory (11 hooks)

**`Hook.MEMORY_STORE`** — Fires when a memory is written via `agent.remember()`.
- `ctx['content']` — the memory content
- `ctx['memory_type']` — `"CORE"`, `"EPISODIC"`, `"SEMANTIC"`, or `"PROCEDURAL"`
- `ctx['importance']` — the importance score

**`Hook.MEMORY_RECALL`** — Fires when memories are retrieved via `agent.recall()`.
- `ctx['query']` — the recall query
- `ctx['results_count']` — how many memories were returned

**`Hook.MEMORY_FORGET`** — Fires when a memory is deleted via `agent.forget()`.
- `ctx['memory_id']` — the ID of the forgotten memory

**`Hook.MEMORY_CONSOLIDATE`** — Fires when episodic memories are consolidated.
- `ctx['count']` — how many memories were consolidated

**`Hook.MEMORY_EXTRACT`** — Fires when the agent auto-extracts memories from a response.
- `ctx['count']` — how many memories were extracted

**`Hook.MEMORY_TRUNCATED`** — Fires when conversation memory is trimmed to fit context.
- `ctx['removed_count']` — how many messages were removed

**`Hook.MEMORY_QUARANTINED`** — Fires when a memory is quarantined due to injection risk.
- `ctx['content']` — the quarantined content

**`Hook.MEMORY_BUS_PUBLISHED`** — A message was published to the MemoryBus.
- `ctx['topic']` — the topic
- `ctx['content']` — the message

**`Hook.MEMORY_BUS_READ`** — A message was read from the MemoryBus.
- `ctx['topic']` — the topic
- `ctx['reader']` — which agent read it

**`Hook.MEMORY_BUS_FILTERED`** — A MemoryBus message was filtered before delivery.
- `ctx['topic']` — the topic

**`Hook.MEMORY_BUS_EXPIRED`** — A MemoryBus message expired.
- `ctx['topic']` — the topic

---

## Context Management (6 hooks)

**`Hook.CONTEXT_COMPRESS`** — Fires when context is compressed to save tokens.
- `ctx['before_tokens']` — tokens before compression
- `ctx['after_tokens']` — tokens after

**`Hook.CONTEXT_COMPACT`** — Fires when context is compacted via a threshold rule.
- `ctx['trigger_percentage']` — the percentage that triggered compaction

**`Hook.CONTEXT_THRESHOLD`** — Fires when context usage crosses a threshold.
- `ctx['percentage']` — current usage percentage

**`Hook.CONTEXT_SNAPSHOT`** — Fires when a context snapshot is taken.
- `ctx['snapshot_id']` — the snapshot identifier

**`Hook.CONTEXT_OFFLOAD`** — Fires when context is offloaded to external storage.
- `ctx['message_count']` — how many messages were offloaded

**`Hook.CONTEXT_RESTORE`** — Fires when offloaded context is restored.
- `ctx['message_count']` — how many messages were restored

---

## Guardrails (4 hooks)

**`Hook.GUARDRAIL_INPUT`** — Fires when an input guardrail runs.
- `ctx['guardrail_name']` — which guardrail ran
- `ctx['passed']` — whether it passed

**`Hook.GUARDRAIL_OUTPUT`** — Fires when an output guardrail runs.
- `ctx['guardrail_name']` — which guardrail ran
- `ctx['passed']` — whether it passed

**`Hook.GUARDRAIL_BLOCKED`** — Fires when a guardrail rejects content.
- `ctx['guardrail_name']` — which guardrail triggered
- `ctx['reason']` — why it was blocked
- `ctx['stage']` — `"INPUT"`, `"ACTION"`, or `"OUTPUT"`

**`Hook.GUARDRAIL_ERROR`** — Fires when a guardrail raises an exception.
- `ctx['guardrail_name']` — which guardrail failed
- `ctx['error']` — the error message

---

## Structured Output (6 hooks)

**`Hook.OUTPUT_VALIDATION_START`** — Fires when structured output validation begins.
- `ctx['output_type']` — the schema type name

**`Hook.OUTPUT_VALIDATION_ATTEMPT`** — Fires on each validation attempt.
- `ctx['attempt']` — which attempt number (1-based)

**`Hook.OUTPUT_VALIDATION_SUCCESS`** — Fires when validation passes.
- `ctx['attempt']` — which attempt succeeded

**`Hook.OUTPUT_VALIDATION_RETRY`** — Fires when validation fails and will be retried.
- `ctx['attempt']` — the failed attempt number
- `ctx['error']` — what went wrong

**`Hook.OUTPUT_VALIDATION_FAILED`** — Fires when all retries are exhausted.
- `ctx['error']` — the final error
- `ctx['attempts']` — total attempts made

**`Hook.OUTPUT_VALIDATION_ERROR`** — Fires when an unexpected error occurs during validation.
- `ctx['error']` — the error message

---

## Swarm (5 hooks)

**`Hook.SWARM_STARTED`** — Fires when a swarm begins execution.
- `ctx['swarm_name']` — the swarm name
- `ctx['topology']` — the topology type

**`Hook.SWARM_ENDED`** — Fires when a swarm finishes.
- `ctx['cost']` — total cost
- `ctx['topology']` — the topology type

**`Hook.SWARM_PARTIAL_RESULT`** — An agent in the swarm produced a partial result.
- `ctx['agent_name']` — which agent
- `ctx['content']` — the partial content

**`Hook.SWARM_BUDGET_LOW`** — The swarm's shared budget is running low.
- `ctx['remaining']` — remaining budget

**`Hook.SWARM_AGENT_HANDOFF`** — An agent handed off to another within the swarm.
- `ctx['from_agent']` — handing off agent
- `ctx['to_agent']` — receiving agent

---

## Workflow (10 hooks)

**`Hook.WORKFLOW_STARTED`** — Fires when workflow execution begins.
- `ctx['run_id']` — unique execution ID
- `ctx['workflow_name']` — the workflow name
- `ctx['input']` — the original input text
- `ctx['step_count']` — number of steps defined
- `ctx['budget_total']` — total budget (or `None`)

**`Hook.WORKFLOW_STEP_START`** — Fires when a step begins.
- `ctx['step_index']` — zero-based step number
- `ctx['step_type']` — e.g. `"SequentialStep"`, `"ParallelStep"`
- `ctx['workflow_name']` — the workflow name

**`Hook.WORKFLOW_STEP_END`** — Fires when a step completes.
- `ctx['step_index']` — zero-based step number
- `ctx['step_type']` — the step type
- `ctx['cost']` — cost of this step

**`Hook.WORKFLOW_BRANCH_TAKEN`** — Fires when a branch condition is evaluated.
- `ctx['condition_result']` — `True` or `False`
- `ctx['step_index']` — which branch step

**`Hook.WORKFLOW_PAUSED`** — Workflow was paused.
- `ctx['step_index']` — where execution paused

**`Hook.WORKFLOW_RESUMED`** — Workflow resumed after pause.
- `ctx['step_index']` — where execution resumed

**`Hook.WORKFLOW_COMPLETED`** — All steps finished successfully.
- `ctx['run_id']` — the execution ID
- `ctx['cost']` — total cost across all steps
- `ctx['steps_completed']` — how many steps ran

**`Hook.WORKFLOW_FAILED`** — An unhandled exception occurred.
- `ctx['error']` — the error message
- `ctx['cost']` — cost before the failure

**`Hook.WORKFLOW_CANCELLED`** — Workflow was cancelled.
- `ctx['reason']` — cancellation reason
- `ctx['cost']` — cost before cancellation

**`Hook.WORKFLOW_ENDED`** — Alias for workflow completion (fires alongside `COMPLETED`).
- Same context as `WORKFLOW_COMPLETED`

---

## Pipeline (6 hooks)

**`Hook.PIPELINE_START`** — Pipeline execution begins.
- `ctx['agent_count']` — how many agents

**`Hook.PIPELINE_END`** — Pipeline execution ends.
- `ctx['cost']` — total cost

**`Hook.PIPELINE_AGENT_START`** — A pipeline agent begins running.
- `ctx['agent_name']` — which agent
- `ctx['step_index']` — position in the pipeline

**`Hook.PIPELINE_AGENT_COMPLETE`** — A pipeline agent finishes.
- `ctx['agent_name']` — which agent
- `ctx['cost']` — cost of this agent's run

**`Hook.PIPELINE_PAUSED`** — Pipeline was paused.
- `ctx['step_index']` — where it paused

**`Hook.PIPELINE_RESUMED`** — Pipeline resumed.
- `ctx['step_index']` — where it resumed

---

## Spawn / Task Delegation (5 hooks)

**`Hook.SPAWN_START`** — An agent is delegating a task to another agent via `spawn()`.
- `ctx['source_agent']` — the delegating agent
- `ctx['target_agent']` — the agent receiving the task
- `ctx['task']` — the task string
- `ctx['mem_count']` — memories transferred
- `ctx['transfer_budget']` — whether budget is shared

**`Hook.SPAWN_END`** — The spawn completed.
- `ctx['source_agent']` — the delegating agent
- `ctx['target_agent']` — the agent that ran the task
- `ctx['cost']` — cost of the child's run
- `ctx['duration']` — wall-clock seconds
- `ctx['response_preview']` — first 80 chars of the response

**`Hook.SPAWN_BLOCKED`** — The spawn was blocked (authority restriction).
- `ctx['source_agent']` — source
- `ctx['target_agent']` — blocked target
- `ctx['reason']` — why it was blocked

**`Hook.SPAWN_CHILD_START`** — A child agent instance is being created.
- `ctx['parent_agent']` — the spawning agent
- `ctx['child_agent']` — the agent being spawned

**`Hook.SPAWN_CHILD_END`** — The spawned child agent finished.
- `ctx['child_agent']` — the agent name
- `ctx['cost']` — cost of the child's run

---

## Serving (2 hooks)

**`Hook.SERVE_REQUEST_START`** — An HTTP request hit the agent server.
- `ctx['method']` — `"POST"` etc.
- `ctx['path']` — the request path

**`Hook.SERVE_REQUEST_END`** — The server finished processing a request.
- `ctx['status_code']` — HTTP status
- `ctx['duration']` — processing time in seconds

---

## Checkpoint (2 hooks)

**`Hook.CHECKPOINT_SAVE`** — A checkpoint was saved.
- `ctx['checkpoint_id']` — the checkpoint identifier

**`Hook.CHECKPOINT_LOAD`** — A checkpoint was loaded.
- `ctx['checkpoint_id']` — the checkpoint identifier

---

## Rate Limiting (3 hooks)

**`Hook.RATELIMIT_CHECK`** — Fires on every rate limit check.
- `ctx['current']` — current usage
- `ctx['limit']` — the rate limit

**`Hook.RATELIMIT_THRESHOLD`** — Usage is approaching the rate limit.
- `ctx['percentage']` — current usage as a percentage

**`Hook.RATELIMIT_EXCEEDED`** — The rate limit was hit.
- `ctx['limit_type']` — `"hourly"`, `"daily"`, etc.

---

## Security & PII (9 hooks)

**`Hook.PII_DETECTED`** — PII was found in input or output.
- `ctx['pii_types']` — list of detected PII types
- `ctx['stage']` — `"INPUT"` or `"OUTPUT"`

**`Hook.PII_BLOCKED`** — Content was blocked due to PII.
- `ctx['pii_types']` — what was blocked

**`Hook.PII_REDACTED`** — PII was redacted from content.
- `ctx['pii_types']` — what was redacted
- `ctx['redacted_count']` — how many instances

**`Hook.PII_AUDIT`** — PII audit log entry created.
- `ctx['pii_types']` — types detected

**`Hook.INJECTION_DETECTED`** — A prompt injection attempt was detected.
- `ctx['stage']` — where it was detected
- `ctx['confidence']` — detection confidence score

**`Hook.INJECTION_RATE_LIMITED`** — Injection attempts triggered rate limiting.

**`Hook.CANARY_TRIGGERED`** — A canary token was activated (injection probe).
- `ctx['token']` — which token fired

**`Hook.IDENTITY_VERIFIED`** — Agent identity was successfully verified.
- `ctx['agent_name']` — the verified agent

**`Hook.SIGNATURE_INVALID`** — An agent message had an invalid signature.
- `ctx['agent_name']` — the claiming agent

---

## Model Routing (2 hooks)

**`Hook.MODEL_SWITCH`** — `agent.switch_model()` was called.
- `ctx['from_model']` — previous model
- `ctx['to_model']` — new model

**`Hook.MODEL_SWITCHED`** — The model switch completed.
- `ctx['model']` — the new model ID

**`Hook.ROUTING_DECISION`** — The model router chose a model.
- `ctx['selected_model']` — which model was chosen
- `ctx['reason']` — why it was chosen

---

## Knowledge / RAG (13 hooks)

**`Hook.KNOWLEDGE_INGEST_START`** — Document ingestion begins.
- `ctx['source']` — the document source

**`Hook.KNOWLEDGE_INGEST_END`** — Ingestion completed.
- `ctx['chunk_count']` — how many chunks were created
- `ctx['duration']` — time taken

**`Hook.KNOWLEDGE_SEARCH_START`** — A knowledge search begins.
- `ctx['query']` — the search query

**`Hook.KNOWLEDGE_SEARCH_END`** — Search completed.
- `ctx['results_count']` — number of results found

**`Hook.KNOWLEDGE_SYNC`** — Knowledge store was synced.

**`Hook.KNOWLEDGE_SOURCE_ADDED`** — A knowledge source was added.
- `ctx['source']` — the source identifier

**`Hook.KNOWLEDGE_SOURCE_REMOVED`** — A knowledge source was removed.
- `ctx['source']` — the source identifier

**`Hook.KNOWLEDGE_CHUNK_PROGRESS`** — Document chunking progress update.
- `ctx['chunks_done']` — chunks processed so far

**`Hook.KNOWLEDGE_EMBED_PROGRESS`** — Embedding progress update.
- `ctx['embeddings_done']` — embeddings generated so far

**`Hook.KNOWLEDGE_AGENTIC_DECOMPOSE`** — Agentic RAG query decomposed.

**`Hook.KNOWLEDGE_AGENTIC_GRADE`** — Agentic RAG graded a result.

**`Hook.KNOWLEDGE_AGENTIC_REFINE`** — Agentic RAG refined a query.

**`Hook.KNOWLEDGE_AGENTIC_VERIFY`** — Agentic RAG verified an answer.

---

## Generation (9 hooks)

These fire when using image, video, or voice generation:

- `Hook.GENERATION_IMAGE_START` — image generation begins
- `Hook.GENERATION_IMAGE_END` — image generation completes; `ctx['url']` is the result
- `Hook.GENERATION_IMAGE_ERROR` — image generation failed
- `Hook.GENERATION_VOICE_START` — voice synthesis begins
- `Hook.GENERATION_VOICE_END` — voice synthesis completes; `ctx['audio_duration']` is the length
- `Hook.GENERATION_VOICE_ERROR` — voice synthesis failed
- `Hook.GENERATION_VIDEO_START` — video generation begins
- `Hook.GENERATION_VIDEO_END` — video generation completes
- `Hook.GENERATION_VIDEO_ERROR` — video generation failed

---

## A2A Messaging (5 hooks)

These fire when using agent-to-agent (A2A) typed messaging:

- `Hook.A2A_MESSAGE_SENT` — message sent; `ctx['to']`, `ctx['message_type']`
- `Hook.A2A_MESSAGE_RECEIVED` — message received; `ctx['from']`, `ctx['message_type']`
- `Hook.A2A_MESSAGE_ACKED` — message acknowledged; `ctx['message_id']`
- `Hook.A2A_MESSAGE_TIMEOUT` — message timed out; `ctx['to']`
- `Hook.A2A_QUEUE_FULL` — the A2A message queue is full; `ctx['queue_size']`

---

## MCP (4 hooks)

- `Hook.MCP_CONNECTED` — MCP server connected; `ctx['server_name']`
- `Hook.MCP_DISCONNECTED` — MCP server disconnected; `ctx['server_name']`
- `Hook.MCP_TOOL_CALL_START` — MCP tool call begins; `ctx['tool_name']`
- `Hook.MCP_TOOL_CALL_END` — MCP tool call ends; `ctx['tool_name']`, `ctx['duration']`

---

## Other Hooks

**`Hook.SYSTEM_PROMPT_BEFORE_RESOLVE`** / **`Hook.SYSTEM_PROMPT_AFTER_RESOLVE`** — Fires before/after the system prompt method is called. Useful for debugging dynamic system prompts.

**`Hook.GOAL_SET`** / **`Hook.GOAL_UPDATED`** — An agent's goal was set or updated.

**`Hook.WATCH_TRIGGER`** — A watch handler fired; `ctx['trigger_data']`

**`Hook.WATCH_ERROR`** — A watch handler raised an error; `ctx['error']`

**`Hook.HITL_PENDING`** / **`Hook.HITL_APPROVED`** / **`Hook.HITL_REJECTED`** — Human-in-the-loop approval events.

**`Hook.CIRCUIT_TRIP`** / **`Hook.CIRCUIT_RESET`** — Circuit breaker opened or reset.

**`Hook.REMOTE_CONFIG_UPDATE`** / **`Hook.REMOTE_CONFIG_ERROR`** — Remote config was updated or failed to apply.

**`Hook.CHECKPOINT_SAVE`** / **`Hook.CHECKPOINT_LOAD`** — State checkpoint events.

**`Hook.BROADCAST_SENT`** / **`Hook.BROADCAST_RECEIVED`** / **`Hook.BROADCAST_DROPPED`** — Swarm broadcast events.

**`Hook.PRY_BREAKPOINT_HIT`** / **`Hook.PRY_SESSION_ENDED`** — Pry debugger events.

**`Hook.ESTIMATION_COMPLETE`** — Cost estimation finished; `ctx['p50']`, `ctx['p95']`

**`Hook.DYNAMIC_PIPELINE_*`** — Seven hooks for dynamic pipeline execution (start, plan, execute, agent spawn, agent complete, end, error).

**`Hook.GROUNDING_*`** — Four hooks for fact grounding (extract start, extract end, verify, complete).

**`Hook.MONITOR_*`** — Four hooks for the MonitorLoop (heartbeat, state change, cost spike, intervention).

**`Hook.HARNESS_*`** — Six hooks for the execution harness (session start/end, progress, circuit trip/reset, retry).

---

## What's Next

- [Hooks & Events](/agent-kit/debugging/hooks) — How to subscribe and practical patterns
- [Tracing](/agent-kit/debugging/tracing) — OpenTelemetry-compatible spans
- [Logging](/agent-kit/debugging/logging) — Structured log output
