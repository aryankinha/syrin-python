---
title: Hooks
description: Subscribe to agent lifecycle events for debugging, metrics, and custom behavior
weight: 171
---

## Listening to Your Agent

Your agent just failed a request. Instead of debugging blind, you want to know: What did the LLM receive? What tools were called? What did the tool return? Where did the budget go?

Hooks let you **subscribe to events** throughout the agent lifecycle. When something happens, your handler receives context—structured data about exactly what occurred.

## The Problem

Understanding agent behavior requires seeing inside the black box:

- **What went to the LLM?** System prompt, messages, tools
- **What did the LLM return?** Raw response before parsing
- **What tools were called?** With what arguments?
- **What was remembered?** What was forgotten?
- **What did it cost?** Token breakdown per call

You could add print statements everywhere, but that's fragile and unstructured. You need **observable hooks** that tell you exactly what happened.

## The Solution

Register handlers for lifecycle events:

```python
from syrin import Agent, Hook, Model

agent = Agent(model=Model.Almock())

# Register a handler
agent.events.on(Hook.AGENT_RUN_END, lambda ctx: print(f"Done! Cost: ${ctx.cost:.4f}"))

result = agent.run("Hello")
# Output: Done! Cost: $0.000120
```

**What just happened**: Your handler ran when the agent finished. You received an `EventContext` with all the details.

## EventContext

Every hook receives an `EventContext`—a dict with dot notation access:

```python
def my_handler(ctx):
    # Dot notation (preferred)
    print(ctx.input)
    
    # Dict notation (also works)
    print(ctx["input"])
```

The context fields vary by hook. See the [Hooks Reference](/debugging/hooks-reference) for each hook's context.

## Hook Types

### Normal Hooks (`on`)

Run during the event:

```python
agent.events.on(Hook.AGENT_RUN_END, lambda ctx: print("Done!"))
```

### Before Hooks (`before`)

Run **before** the event, can modify context:

```python
def modify_temperature(ctx):
    ctx["temperature"] = 0.5

agent.events.before(Hook.LLM_REQUEST_START, modify_temperature)
```

Useful for:
- Changing LLM parameters (temperature, top_p)
- Adding custom headers
- Validating inputs
- Injecting context

### After Hooks (`after`)

Run **after** the event for logging/metrics:

```python
def log_duration(ctx):
    print(f"Duration: {ctx.duration_ms}ms")

agent.events.after(Hook.AGENT_RUN_END, log_duration)
```

## Common Patterns

> **Note:** The events API does not support decorator syntax. Use `agent.events.on(Hook.X, handler)` directly.

### Pattern 1: Track Cost Across Requests

```python
total_cost = {"value": 0.0}

def track_cost(ctx):
    total_cost["value"] += ctx.get("cost", 0)

agent.events.on(Hook.AGENT_RUN_END, track_cost)

# Make multiple requests
for i in range(10):
    agent.run(f"Request {i}")

print(f"Total spent: ${total_cost['value']:.4f}")
```

### Pattern 2: Log All Tool Calls

```python
def log_tool(ctx):
    print(f"Tool: {ctx.name}")
    print(f"  Arguments: {ctx.arguments}")
    print(f"  Result: {str(ctx.result)[:100]}")

def log_tool_error(ctx):
    print(f"Tool failed: {ctx.name}")
    print(f"  Error: {ctx.error}")

agent.events.on(Hook.TOOL_CALL_END, log_tool)
agent.events.on(Hook.TOOL_ERROR, log_tool_error)
```

### Pattern 3: Budget Alerts

```python
def alert_threshold(ctx):
    pct = ctx.threshold_percent
    print(f"Budget at {pct}%!")
    if pct >= 90:
        send_alert(f"Budget critical: {pct}%")

def handle_exceeded(ctx):
    print(f"Budget exceeded: ${ctx.used:.4f} of ${ctx.limit:.4f}")

agent.events.on(Hook.BUDGET_THRESHOLD, alert_threshold)
agent.events.on(Hook.BUDGET_EXCEEDED, handle_exceeded)
```

### Pattern 4: Observe LLM Calls

```python
def on_llm_start(ctx):
    print(f"LLM call starting")
    print(f"  Iteration: {ctx.iteration}")
    print(f"  Model: {ctx.model}")

def on_llm_end(ctx):
    print(f"LLM call complete")
    print(f"  Tokens: {ctx.tokens}")
    print(f"  Cost: ${ctx.cost:.4f}")
    print(f"  Content: {str(ctx.content)[:100]}")

agent.events.on(Hook.LLM_REQUEST_START, on_llm_start)
agent.events.on(Hook.LLM_REQUEST_END, on_llm_end)
```

### Pattern 5: Memory Visibility

```python
def on_store(ctx):
    print(f"Stored: {ctx.content[:50]}...")

def on_recall(ctx):
    print(f"Recalled: {len(ctx.memories)} memories")
    for m in ctx.memories[:3]:
        print(f"  - {m.content[:50]}")

def on_forget(ctx):
    print(f"Forgot: {ctx.forgotten_count} items")

agent.events.on(Hook.MEMORY_STORE, on_store)
agent.events.on(Hook.MEMORY_RECALL, on_recall)
agent.events.on(Hook.MEMORY_FORGET, on_forget)
```

### Pattern 6: Before/After Hooks

```python
# Before: modify the LLM call
def add_context(ctx):
    ctx["custom_field"] = "my_value"
    ctx["temperature"] = 0.7

# After: record metrics
def record_latency(ctx):
    metrics.histogram("llm_latency", ctx.duration_ms)

agent.events.before(Hook.LLM_REQUEST_START, add_context)
agent.events.after(Hook.LLM_REQUEST_END, record_latency)
```

## Shortcut Methods

For common hooks, use shortcuts:

```python
agent.events.on_start(lambda ctx: print("Started"))
agent.events.on_complete(lambda ctx: print(f"Done! Cost: ${ctx.cost:.4f}"))
agent.events.on_request(lambda ctx: print("LLM call"))
agent.events.on_response(lambda ctx: print(f"Tokens: {ctx.tokens}"))
agent.events.on_tool(lambda ctx: print(f"Tool: {ctx.name}"))
agent.events.on_error(lambda ctx: print(f"Error: {ctx.error}"))
agent.events.on_budget(lambda ctx: print(f"Budget: {ctx}"))
```

## Listen to All Events

Track everything:

```python
def log_all(hook, ctx):
    print(f"[{hook.value}] {ctx}")

agent.events.on_all(log_all)
```

**Output:**
```
[agent.run.start] {'input': 'Hello'}
[llm.request.start] {'iteration': 0, 'model': 'gpt-4o'}
[llm.request.end] {'tokens': 45, 'cost': 0.000150}
[agent.run.end] {'cost': 0.000150, 'tokens': 45}
```

## Multiple Handlers

Register multiple handlers for the same hook:

```python
agent.events.on(Hook.AGENT_RUN_END, handler1)
agent.events.on(Hook.AGENT_RUN_END, handler2)
agent.events.on(Hook.AGENT_RUN_END, handler3)
```

All three run in registration order.

## Handler Best Practices

### Keep Handlers Fast

Handlers run synchronously in the agent's execution path:

```python
# Good: fast in-memory operations
def track_cost(ctx):
    total_cost += ctx.cost

agent.events.on(Hook.AGENT_RUN_END, track_cost)

# Bad: slow operations block the agent
def slow_operation(ctx):
    requests.post("https://analytics.example.com", json=ctx)  # Blocks!

agent.events.on(Hook.AGENT_RUN_END, slow_operation)
```

### Use Fire-and-Forget for Slow Operations

```python
import threading

def send_analytics(ctx):
    def fire_and_forget():
        requests.post("https://analytics.example.com", json=dict(ctx))
    threading.Thread(target=fire_and_forget, daemon=True).start()

agent.events.on(Hook.AGENT_RUN_END, send_analytics)
```

### Access Context Safely

Not all hooks have all fields:

```python
def safe_handler(ctx):
    cost = ctx.get("cost", 0)  # Use .get() with defaults
    tokens = ctx.get("tokens", 0)
    duration = ctx.get("duration", 0)

agent.events.on(Hook.AGENT_RUN_END, safe_handler)
```

## Debug Mode vs Custom Hooks

| Feature | Debug Mode | Custom Hooks |
|---------|-----------|--------------|
| Setup | One flag (`debug=True`) | Register handlers |
| Output | Rich console output | Your logic |
| Customization | Limited | Full control |
| Production | Not recommended | Recommended |
| Performance impact | Minimal | Depends on handler |

**Debug mode** is great for development. **Custom hooks** are better for production.

## See Also

- [Debugging Overview](/debugging/overview) — Introduction to observability
- [Hooks Reference](/debugging/hooks-reference) — Complete hook reference
- [Audit Logging](/debugging/logging) — Persist events to files
- [Playground](/production/playground) — Visual observability panel
