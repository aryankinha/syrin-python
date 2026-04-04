---
title: Hooks & Events
description: 182 lifecycle events you can subscribe to — observe everything, react to anything
weight: 171
---

## The Observation Layer

Every meaningful moment in a Syrin agent's lifecycle fires an event. LLM calls, tool executions, budget checks, memory reads, guardrail decisions, stream chunks — all of them. You subscribe to the ones you care about, and Syrin calls your handler with a context dictionary containing the state at that moment.

This is how you build logging, alerting, dashboards, and cost tracking — without touching the agent code itself.

## Subscribing to Hooks

Use `agent.events.on()` to subscribe. The handler receives a context dictionary:

```python
from syrin import Agent, Budget, Model
from syrin.enums import ExceedPolicy
from syrin.enums import Hook

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
    # model = Model.mock()  # no API key needed for testing
    system_prompt="You are helpful.",
    budget=Budget(max_cost=1.00, exceed_policy=ExceedPolicy.WARN),
)

log = []
agent.events.on(Hook.AGENT_RUN_START, lambda ctx: log.append(f"RUN_START: input='{ctx.get('input', '')[:20]}' model={ctx.get('model', '')}"))
agent.events.on(Hook.LLM_REQUEST_END, lambda ctx: log.append(f"LLM_END: cost=${ctx.get('cost', 0):.6f}"))
agent.events.on(Hook.AGENT_RUN_END, lambda ctx: log.append(f"RUN_END: cost=${ctx.get('cost', 0):.6f}"))

agent.run("Hello!")
for line in log:
    print(line)
```

Output:

```
RUN_START: input='Hello!' model=almock/default
LLM_END: cost=$0.000040
RUN_END: cost=$0.000040
```

## Context Keys By Hook

Each hook fires with different context keys. Here are the most important ones:

`Hook.AGENT_RUN_START` fires when `run()` is called:
- `ctx['input']` — the user's input text
- `ctx['model']` — the model ID being used
- `ctx['iteration']` — the loop iteration count (0 for first call)

`Hook.LLM_REQUEST_END` fires after every LLM response:
- `ctx['content']` — the text the LLM generated
- `ctx['cost']` — USD cost of this LLM call
- `ctx['tokens']` — token count object
- `ctx['input_tokens']` — tokens in the prompt
- `ctx['output_tokens']` — tokens in the response
- `ctx['model']` — model used for this call

`Hook.AGENT_RUN_END` fires when `run()` is about to return:
- `ctx['content']` — the final response text
- `ctx['cost']` — total cost of the entire run
- `ctx['iterations']` — how many LLM calls were made
- `ctx['duration']` — wall-clock seconds
- `ctx['stop_reason']` — why the agent stopped (end_turn, budget, etc.)

`Hook.TOOL_CALL_START` fires before a tool is executed:
- `ctx['tool_name']` — the tool's name
- `ctx['arguments']` — the arguments the LLM passed

`Hook.TOOL_CALL_END` fires after a tool returns:
- `ctx['tool_name']` — the tool's name
- `ctx['result']` — what the tool returned
- `ctx['duration']` — how long the tool took

`Hook.BUDGET_EXCEEDED` fires when the budget limit is hit:
- `ctx['limit']` — the configured limit
- `ctx['spent']` — how much was spent
- `ctx['budget_type']` — which limit was hit (run, daily, etc.)

`Hook.GUARDRAIL_BLOCKED` fires when a guardrail rejects content:
- `ctx['guardrail_name']` — which guardrail triggered
- `ctx['reason']` — why it was blocked
- `ctx['stage']` — INPUT, ACTION, or OUTPUT

`Hook.MEMORY_STORE` fires when a memory is written:
- `ctx['content']` — the memory content
- `ctx['memory_type']` — CORE, EPISODIC, SEMANTIC, or PROCEDURAL
- `ctx['importance']` — the importance score

## Subscribing to All Hooks

To receive every event (useful for debugging or building a comprehensive log):

```python
agent.events.on_all(lambda hook, ctx: print(f"[{hook}] {list(ctx.keys())}"))
```

The handler signature for `on_all` receives the hook name as the first argument and the context as the second.

## Practical Patterns

### Log All Costs to a File

```python
import json
from syrin import Agent, Model
from syrin.enums import Hook

agent = Agent(model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"), system_prompt="You are helpful.")
# model = Model.mock()  # no API key needed for testing

cost_log = []
agent.events.on(
    Hook.AGENT_RUN_END,
    lambda ctx: cost_log.append({
        "cost": ctx.get("cost", 0),
        "duration": ctx.get("duration", 0),
        "stop_reason": ctx.get("stop_reason", ""),
    })
)

agent.run("First question")
agent.run("Second question")

print("Cost log:")
for entry in cost_log:
    print(f"  ${entry['cost']:.6f} in {entry['duration']:.2f}s ({entry['stop_reason']})")
```

Output:

```
Cost log:
  $0.000040 in 1.66s (end_turn)
  $0.000041 in 1.71s (end_turn)
```

### Alert When Budget Is Low

```python
from syrin import Agent, Budget, Model
from syrin.enums import ExceedPolicy
from syrin.enums import Hook

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
    # model = Model.mock()  # no API key needed for testing
    system_prompt="You are helpful.",
    budget=Budget(max_cost=1.00, exceed_policy=ExceedPolicy.WARN),
)

agent.events.on(
    Hook.BUDGET_THRESHOLD,
    lambda ctx: print(f"ALERT: Budget at {ctx.get('percentage', 0):.0f}%! Remaining: ${ctx.get('remaining', 0):.4f}")
)
```

### Track Tool Performance

```python
import time
from syrin import Agent, Model
from syrin.enums import Hook

agent = Agent(model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"), system_prompt="You are helpful.")
# model = Model.mock()  # no API key needed for testing
tool_times = {}

agent.events.on(
    Hook.TOOL_CALL_END,
    lambda ctx: tool_times.setdefault(ctx.get("tool_name", "?"), []).append(ctx.get("duration", 0))
)

# After running:
# for tool, times in tool_times.items():
#     avg = sum(times) / len(times)
#     print(f"{tool}: avg {avg:.2f}s over {len(times)} calls")
```

## The 182 Hooks

Syrin fires 182 distinct hooks organized into these categories:

- **Agent** (14 hooks) — AGENT_RUN_START, AGENT_RUN_END, AGENT_INIT, AGENT_RESET, and more
- **LLM** (5 hooks) — LLM_REQUEST_START, LLM_REQUEST_END, LLM_STREAM_CHUNK, LLM_RETRY, LLM_FALLBACK
- **Tool** (6 hooks) — TOOL_CALL_START, TOOL_CALL_END, TOOL_ERROR, and more
- **Budget** (5 hooks) — BUDGET_CHECK, BUDGET_THRESHOLD, BUDGET_EXCEEDED, BUDGET_FORECAST, BUDGET_ANOMALY
- **Memory** (11 hooks) — MEMORY_STORE, MEMORY_RECALL, MEMORY_FORGET, MEMORY_DECAY, and more
- **Guardrail** (4 hooks) — GUARDRAIL_BLOCKED, GUARDRAIL_PASSED, GUARDRAIL_WARN, GUARDRAIL_FLAG
- **Context** (6 hooks) — CONTEXT_COMPACTED, CONTEXT_TRUNCATED, CONTEXT_WINDOW_FULL, and more
- **Workflow** (10 hooks) — WORKFLOW_STARTED, WORKFLOW_STEP_START, WORKFLOW_STEP_END, and more
- **Swarm** (5 hooks) — SWARM_STARTED, SWARM_ENDED, AGENT_JOINED_SWARM, AGENT_LEFT_SWARM, SWARM_BUDGET_LOW
- **Knowledge** (13 hooks) — KNOWLEDGE_SEARCH_START, KNOWLEDGE_CHUNK_RETRIEVED, and more
- **Generation** (9 hooks) — GENERATION_IMAGE_START, GENERATION_IMAGE_END, and more
- **PII** (4 hooks) — PII_DETECTED, PII_REDACTED, and more
- **A2A** (5 hooks) — A2A_MESSAGE_SENT, A2A_MESSAGE_RECEIVED, and more
- And 90+ more across checkpoint, circuit breaker, serving, watch, MCP, and more

## Hooks Are Synchronous

Hook handlers run in the thread that called `agent.run()`. Keep them fast. For expensive operations — writing to a database, sending a network request, publishing a metric — dispatch to a background thread:

```python
import threading
from syrin.enums import Hook

def expensive_handler(ctx):
    # This would block the agent if called directly
    def do_work():
        # write to database, send to metrics system, etc.
        pass
    threading.Thread(target=do_work, daemon=True).start()

agent.events.on(Hook.AGENT_RUN_END, expensive_handler)
```

## Hooks vs. Debug Mode

`debug=True` on the agent prints all events to the console with full context. It is the fastest way to see what is happening during development:

```python
agent = Agent(model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"), system_prompt="You are helpful.", debug=True)
# model = Model.mock()  # no API key needed for testing
agent.run("Hello!")
# Prints every hook as it fires
```

For production, use hooks to forward specific events to your observability platform. For full tracing, see [Tracing](/agent-kit/debugging/tracing).

## What's Next

- [Hooks Reference](/agent-kit/debugging/hooks-reference) — Every hook with its full context schema
- [Tracing](/agent-kit/debugging/tracing) — OpenTelemetry-compatible spans for distributed tracing
- [Logging](/agent-kit/debugging/logging) — Structured log output
- [Pry Debugger](/agent-kit/debugging/pry) — Interactive step-through debugging
