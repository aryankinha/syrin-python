---
title: Event Bus
description: Domain events and lifecycle hooks for observability and custom behavior
weight: 240
---

## You Can't See What Your Agent Does

You deployed an agent to production. It's making LLM calls, using tools, managing budget. But how do you know what's happening inside? How do you log for compliance? How do you react to events like budget warnings? How do you modify behavior mid-execution?

Agents are black boxes by default. The solution is Syrin's Events system — every moment in the agent lifecycle emits an event you can subscribe to, modify, or react to in real time.

## The Events System

Syrin provides a rich event system built on `Hook` enums:

```python
from syrin import Agent, Hook

agent = Agent(model=model)

# Subscribe to events
agent.events.on(Hook.AGENT_RUN_START, lambda ctx: print(f"Started: {ctx.input}"))
agent.events.on(Hook.AGENT_RUN_END, lambda ctx: print(f"Done: {ctx.cost}"))
```

## Hook Categories

Hooks span nine categories. The **Agent** category covers agent lifecycle moments like `RUN_START` and `RUN_END`. The **LLM** category fires around model interactions — `REQUEST_START` before the API call and `REQUEST_END` after. The **Tool** category fires around tool use — `TOOL_CALL_START` when a tool begins and `TOOL_CALL_END` when it finishes.

The **Memory** category covers memory operations: `MEMORY_STORE` when a memory is saved, `MEMORY_RECALL` when memories are retrieved. The **Context** category handles the token window — `CONTEXT_PREPARE` and `CONTEXT_COMPACT`. The **Budget** category fires on cost checks — `BUDGET_CHECK` every time the budget is evaluated and `BUDGET_EXCEEDED` when the limit is hit.

The **MCP** category covers the Model Context Protocol — `MCP_CONNECTED` and `MCP_TOOL_CALL`. The **Multi-Agent** category fires during agent coordination — `SPAWN_START`, `SPAWN_END`, and similar. The **Grounding** category covers RAG verification — `GROUNDING_EXTRACT_START`, `GROUNDING_VERIFY`, and `GROUNDING_COMPLETE`.

## Basic Event Usage

### Register Handlers

```python
from syrin import Agent, Hook

agent = Agent(model=model)

# Normal handler
agent.events.on(Hook.AGENT_RUN_START, lambda ctx: print("Run started"))

# Before handler (can modify context!)
agent.events.before(Hook.LLM_REQUEST_START, lambda ctx: ctx.update({"temperature": 0.5}))

# After handler (for logging)
agent.events.after(Hook.LLM_REQUEST_END, lambda ctx: print(f"Tokens: {ctx.tokens}"))
```

### Shortcut Methods

For common events, use shortcuts:

```python
agent.events.on_start(lambda ctx: print("Started"))
agent.events.on_complete(lambda ctx: print(f"Done, cost: {ctx.cost}"))
agent.events.on_request(lambda ctx: print("LLM request"))
agent.events.on_response(lambda ctx: print(f"Response: {ctx.content[:50]}"))
agent.events.on_tool(lambda ctx: print(f"Tool: {ctx.tool_name}"))
agent.events.on_error(lambda ctx: print(f"Error: {ctx.error}"))
agent.events.on_budget(lambda ctx: print(f"Budget: {ctx.remaining}"))
```

### Subscribe to All Events

```python
def log_all(hook: Hook, ctx: EventContext):
    print(f"[{hook.value}] {ctx.get('input', '')[:50]}...")

agent.events.on_all(log_all)
```

## EventContext: What's in an Event?

Every handler receives an `EventContext` with relevant data:

```python
class EventContext(dict):
    """Context passed to event handlers."""
    
    # Access like dict
    ctx["input"]
    ctx["cost"]
    ctx["tokens"]
    
    # Or like object
    ctx.input
    ctx.cost
    ctx.tokens
```

### Common Fields by Hook Type

**AGENT_RUN_START/END:**
```python
ctx.input          # User input
ctx.output         # Agent response
ctx.cost           # Total cost
ctx.model_id       # Model used
ctx.agent_name     # Agent class name
```

**LLM_REQUEST_START/END:**
```python
ctx.model_id       # Model identifier
ctx.messages       # Messages sent
ctx.tokens         # Token usage
ctx.duration_ms    # Request duration
ctx.temperature    # Temperature used
```

**TOOL_CALL_START/END:**
```python
ctx.tool_name      # Tool name
ctx.arguments      # Tool arguments
ctx.result         # Tool result
ctx.duration_ms    # Execution time
```

**BUDGET_CHECK/EXCEEDED:**
```python
ctx.limit          # Budget limit
ctx.spent          # Amount spent
ctx.remaining       # Remaining budget
ctx.percent        # Percentage used
```

## Practical Examples

### 1. Cost Tracking

```python
total_cost = 0.0

def track_cost(ctx):
    global total_cost
    total_cost += ctx.get("cost", 0)
    print(f"Request cost: ${ctx.get('cost', 0):.4f}")

agent = Agent(model=model, budget=Budget(max_cost=10.00))
agent.events.on(Hook.AGENT_RUN_END, track_cost)

# Run some requests
for i in range(10):
    agent.run(f"Request {i}")

print(f"Total spent: ${total_cost:.4f}")
```

### 2. Request Logging for Compliance

```python
import json
from datetime import datetime

log_file = open("compliance_log.jsonl", "a")

def log_request(ctx):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "hook": ctx.get("hook", ""),
        "input": ctx.get("input", ""),
        "model": ctx.get("model_id", ""),
        "cost": ctx.get("cost", 0),
        "tokens": ctx.get("tokens", {}),
    }
    log_file.write(json.dumps(entry) + "\n")
    log_file.flush()

agent.events.on(Hook.AGENT_RUN_START, log_request)
agent.events.on(Hook.AGENT_RUN_END, log_request)
```

### 3. Modify LLM Requests

```python
# Add custom headers or modify parameters before sending
def add_custom_prompt(ctx):
    messages = ctx.get("messages", [])
    if messages:
        # Inject a compliance message
        messages.insert(0, {
            "role": "system",
            "content": "[Compliance] This conversation is logged for audit purposes."
        })
        ctx["messages"] = messages

agent.events.before(Hook.LLM_REQUEST_START, add_custom_prompt)
```

### 4. Budget Alerts

```python
def budget_warning(ctx):
    percent = ctx.get("percent", 0)
    remaining = ctx.get("remaining", 0)
    
    if percent >= 90:
        print(f"CRITICAL: Budget at {percent}% - ${remaining:.2f} remaining")
    elif percent >= 75:
        print(f"WARNING: Budget at {percent}% - ${remaining:.2f} remaining")

agent.events.on(Hook.BUDGET_CHECK, budget_warning)
```

### 5. Tool Performance Monitoring

```python
tool_times = {}

def track_tool_time(ctx):
    tool_name = ctx.get("tool_name", "unknown")
    duration = ctx.get("duration_ms", 0)
    
    if tool_name not in tool_times:
        tool_times[tool_name] = []
    tool_times[tool_name].append(duration)

agent.events.on(Hook.TOOL_CALL_END, track_tool_time)

# After runs
for tool, times in tool_times.items():
    avg = sum(times) / len(times)
    print(f"{tool}: avg={avg:.1f}ms, calls={len(times)}")
```

### 6. Memory Operations

```python
memory_ops = []

def track_memory(ctx):
    memory_ops.append({
        "operation": ctx.get("operation", ""),
        "memory_type": ctx.get("memory_type", ""),
        "content": ctx.get("content", "")[:100],
    })

agent.events.on(Hook.MEMORY_STORE, track_memory)
agent.events.on(Hook.MEMORY_RECALL, track_memory)
```

### 7. RAG/Grounding Events

```python
def track_grounding(ctx):
    print(f"Grounding: {ctx.get('operation', '')}")
    print(f"  Chunks: {ctx.get('chunk_count', 0)}")
    print(f"  Facts: {ctx.get('fact_count', 0)}")
    print(f"  Verified: {ctx.get('verified_count', 0)}")

agent.events.on(Hook.GROUNDING_EXTRACT_START, track_grounding)
agent.events.on(Hook.GROUNDING_EXTRACT_END, track_grounding)
agent.events.on(Hook.GROUNDING_VERIFY, track_grounding)
agent.events.on(Hook.GROUNDING_COMPLETE, track_grounding)
```

## Before/After Handlers

Before handlers can modify the event context:

```python
# Modify temperature based on user tier
def adjust_temperature(ctx):
    user_tier = ctx.get("user_tier", "free")
    
    if user_tier == "premium":
        ctx["temperature"] = 0.9
    elif user_tier == "enterprise":
        ctx["temperature"] = 0.7
    else:
        ctx["temperature"] = 0.5

agent.events.before(Hook.LLM_REQUEST_START, adjust_temperature)

# Log response after
def log_response(ctx):
    print(f"Response length: {len(ctx.get('content', ''))}")

agent.events.after(Hook.LLM_REQUEST_END, log_response)
```

## Async Handlers

For non-blocking operations:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

def async_log(ctx):
    # Fire-and-forget to thread pool
    future = executor.submit(write_to_remote, ctx)
    # Don't await - continues immediately

agent.events.on(Hook.AGENT_RUN_END, async_log)
```

## Multiple Handlers

Register multiple handlers on the same hook:

```python
# Handler 1: Logging
agent.events.on(Hook.AGENT_RUN_END, lambda ctx: print("Done"))

# Handler 2: Metrics
agent.events.on(Hook.AGENT_RUN_END, track_metrics)

# Handler 3: Notifications
agent.events.on(Hook.AGENT_RUN_END, send_slack_notification)

# All three fire in order
```

## Event Reference

### Agent Lifecycle

`AGENT_RUN_START` fires before processing begins. Its context includes `input`, `model_id`, and `agent_name`. `AGENT_RUN_END` fires after completion with `input`, `output`, `cost`, `tokens`, and `duration_ms`. `AGENT_ERROR` fires on any unhandled exception with `error`, `error_type`, and `input`.

### LLM Lifecycle

`LLM_REQUEST_START` fires before the API call with `messages`, `model_id`, `temperature`, and `tools`. `LLM_REQUEST_END` fires after the API response with `content`, `tool_calls`, `tokens`, and `duration_ms`. `LLM_STREAM_START` fires when streaming begins with `model_id`. `LLM_STREAM_END` fires when the stream completes with `content` and `tokens`.

### Tool Lifecycle

`TOOL_CALL_START` fires before tool execution with `tool_name` and `arguments`. `TOOL_CALL_END` fires after execution with `tool_name`, `result`, and `duration_ms`. `TOOL_ERROR` fires when a tool raises an exception with `tool_name`, `error`, and `arguments`.

### Memory Lifecycle

`MEMORY_STORE` fires when a memory is saved with `content`, `memory_type`, and `key`. `MEMORY_RECALL` fires when memories are retrieved with `query` and `results`. `MEMORY_FORGET` fires when a memory is deleted with `key`.

### Context Lifecycle

`CONTEXT_PREPARE` fires when the context window is assembled with `messages`, `tokens`, and `max_tokens`. `CONTEXT_COMPACT` fires when compaction runs with `method`, `tokens_before`, and `tokens_after`. `CONTEXT_THRESHOLD` fires when a threshold is hit with `percent`, `max_tokens`, and `action`.

### Budget Lifecycle

`BUDGET_CHECK` fires each time the budget is evaluated with `limit`, `spent`, `remaining`, and `percent`. `BUDGET_EXCEEDED` fires when the agent hits its limit with `limit`, `spent`, and `exceeded_by`.

## Observability Integration

Events integrate with tracing:

```python
from syrin.observability import trace

tracer = trace(service_name="my-agent")

agent.events.on(Hook.AGENT_RUN_START, lambda ctx: tracer.start_span("agent_run"))
agent.events.on(Hook.AGENT_RUN_END, lambda ctx: tracer.end_span())
```

## Testing with Events

```python
events_fired = []

def capture_event(ctx):
    events_fired.append(ctx.get("hook", "unknown"))

agent.events.on_all(lambda hook, ctx: events_fired.append(hook))

agent.run("Hello")

assert Hook.AGENT_RUN_START in events_fired
assert Hook.AGENT_RUN_END in events_fired
```

## What's Next?

- [Tracing](/agent-kit/debugging/tracing) — Full observability
- [Hooks Reference](/agent-kit/debugging/hooks-reference) — Complete hooks list
- [Testing](/agent-kit/advanced/testing) — Test event handlers

## See Also

- [Observability Overview](/agent-kit/debugging/overview) — Debugging tools
- [Tracing Exporters](/agent-kit/debugging/tracing-exporters) — Export traces
- [Logging](/agent-kit/debugging/logging) — Structured logging
