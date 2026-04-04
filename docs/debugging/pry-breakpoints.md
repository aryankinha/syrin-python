---
title: Pry — Breakpoints
description: All DebugPoint values, when each fires, what context is available at each pause, and how to configure PryResumeMode.
weight: 177
---

## DebugPoint

`DebugPoint` is a `StrEnum` that identifies where in the agent lifecycle execution should pause. Pass a list of values to `PryConfig(breakpoints=[...])` or directly to a workflow step's `on` parameter.

```python
from syrin.enums import DebugPoint
from syrin.debug._pry_swarm import PryConfig

config = PryConfig(break_on=[DebugPoint.ON_SPAWN, DebugPoint.ON_ERROR])
```

> Note: The enum is defined in `syrin.enums.DebugPoint`. The source currently defines 5 values; the table below documents all values including those planned for the full v0.11.0 T16 implementation.

---

## All DebugPoint Values

### ON_SPAWN

**When it fires:** Just before one agent passes its `SpawnContext` to the next. Fires for both explicit `.spawn()` calls and workflow step transitions.

**Pause state:** Both the parent and child agents are visible in the `[a]` agents tab. The `SpawnContext` payload is shown in full — all keys, values, and budget carried forward.

**Available context:** `source_agent`, `target_agent`, `user_input`, `context_keys`, `budget_remaining`.

```python
PryConfig(breakpoints=[DebugPoint.ON_SPAWN])
```

---

### ON_ERROR

**When it fires:** When any agent raises an unhandled exception, instead of triggering the configured `FallbackStrategy`.

**Pause state:** The `[r]` errors tab jumps to the new error. The full traceback, agent name, and the input that caused the error are shown. Other agents in the swarm remain running unless `pause_on_agent_failure=True`.

**Available context:** `agent_name`, `error_type`, `error_message`, `traceback`, `iteration`.

```python
PryConfig(breakpoints=[DebugPoint.ON_ERROR], pause_on_agent_failure=True)
```

---

### ON_LLM_REQUEST

**When it fires:** Just before each LLM API call is sent. Fires once per iteration of the agent's ReAct loop.

**Pause state:** The `[e]` event tab shows the full prompt that would be sent — system prompt, conversation history, and any tool definitions. Useful for debugging unexpected prompt construction.

**Available context:** `agent_name`, `model`, `messages` (full message list), `tools` (schema list), `estimated_tokens`, `budget_remaining`.

```python
PryConfig(breakpoints=[DebugPoint.ON_LLM_REQUEST])
```

---

### ON_TOOL_RESULT

**When it fires:** After each tool call returns, before the result is appended to the conversation.

**Pause state:** The `[t]` tools tab shows the tool name, full arguments, and the raw result. Useful for verifying tool outputs before the agent acts on them.

**Available context:** `agent_name`, `tool_name`, `tool_args`, `tool_result`, `iteration`, `cost_so_far`.

```python
PryConfig(breakpoints=[DebugPoint.ON_TOOL_RESULT])
```

---

### ON_A2A_RECEIVE

**When it fires:** When an agent receives an agent-to-agent (A2A) message via the MemoryBus or direct messaging.

**Pause state:** The A2A timeline panel (when `show_a2a_timeline=True`) highlights the incoming message. The `[e]` event tab shows sender, channel, and full message payload.

**Available context:** `recipient_agent`, `sender_agent`, `channel`, `message_type`, `payload`.

```python
PryConfig(
    breakpoints=[DebugPoint.ON_A2A_RECEIVE],
    show_a2a_timeline=True,
)
```

---

### ON_STEP_START

**When it fires:** Before each workflow step begins — before the step's agent is invoked.

**Pause state:** The agent graph highlights the about-to-run node. The `[d]` debug tab shows the step name, step index, and the `HandoffContext` being passed in.

**Available context:** `step_name`, `step_index`, `agent_class`, `input_context`.

---

### ON_STEP_END

**When it fires:** After a workflow step finishes — after the step's agent returns its response.

**Pause state:** The graph node transitions to STOPPED. The `[e]` event tab shows the step output and updated `HandoffContext`.

**Available context:** `step_name`, `step_index`, `agent_class`, `output`, `cost`, `duration_ms`.

---

### ON_AGENT_START

**When it fires:** When an agent begins its `run()` or `arun()` execution — after budget check, before the first LLM call.

**Pause state:** The graph node transitions to RUNNING. The `[a]` agents tab shows the agent's starting state: model, system prompt, tools, memory config, budget allocation.

**Available context:** `agent_name`, `agent_id`, `model`, `budget_limit`, `tools_count`.

---

### ON_AGENT_END

**When it fires:** When an agent's `run()` or `arun()` completes normally.

**Pause state:** The graph node transitions to STOPPED. The `[a]` agents tab shows final cost, token count, and iteration count.

**Available context:** `agent_name`, `agent_id`, `cost_spent`, `tokens_used`, `iterations`, `stop_reason`.

---

### ON_BUDGET_WARNING

**When it fires:** When an agent crosses a budget threshold (e.g. 80% of its allocation consumed). Corresponds to `Hook.BUDGET_THRESHOLD`.

**Pause state:** The budget tree panel highlights the over-threshold node in amber. Useful for diagnosing runaway agents before they exhaust their budget.

**Available context:** `agent_name`, `threshold_pct`, `spent`, `limit`, `remaining`.

---

### ON_MEMORY_WRITE

**When it fires:** When an agent stores an entry to memory (`Hook.MEMORY_STORE`).

**Pause state:** The `[m]` memory tab shows the new entry — memory type, content, decay curve, and storage backend.

**Available context:** `agent_name`, `memory_type`, `content_preview`, `backend`, `memory_id`.

---

## PryResumeMode

`PryResumeMode` controls what happens when you press `c` or `s` (or call `PrySession.resume()` programmatically).

Three resume modes are available. `STEP` (key `s`) executes one hook and pauses again — use this to walk through a spawn or tool sequence one event at a time. `CONTINUE` (key `c`) resumes all paused agents and continues normal execution with no further automatic pauses unless another `DebugPoint` fires. `CONTINUE_AGENT` (no default key binding) resumes only the currently focused agent while other agents in the swarm remain paused.

```python
from syrin.enums import PryResumeMode
from syrin.debug._pry_swarm import PrySession, PryConfig

session = PrySession(config=PryConfig())
await session.resume(mode=PryResumeMode.STEP)
```

---

## Configuring Breakpoints vs. Log-Only

Breakpoints listed in `PryConfig.breakpoints` will **pause execution**. All other `DebugPoint` events are still captured in the event stream and visible in the TUI — they just do not pause.

To log all events without pausing on any:

```python
# No breakpoints — stream-only mode
PryConfig(breakpoints=[])
```

To pause on spawns and errors only:

```python
PryConfig(breakpoints=[DebugPoint.ON_SPAWN, DebugPoint.ON_ERROR])
```

To pause on every LLM call (useful for prompt debugging):

```python
PryConfig(breakpoints=[DebugPoint.ON_LLM_REQUEST])
```

---

## Workflow Step Breakpoints

Individual workflow steps can declare their own `DebugPoint` override without a global `PryConfig`:

```python
from syrin import Workflow
from syrin.enums import DebugPoint

wf = Workflow("pipeline", pry=True)
wf.step("research", ResearchAgent, on=DebugPoint.ON_SPAWN)
wf.step("write", WriterAgent)
```

The `on` parameter accepts a single `DebugPoint`. When omitted it defaults to `DebugPoint.ON_SPAWN`.

---

## What's Next?

- [Pry Multi-Agent TUI](/debugging/pry-multi-agent) — panel layout, keyboard controls, state export
- [Pry (single-agent)](/debugging/pry) — single-agent reference
