---
title: Debugging Overview
description: Understand what happened and why in your agent runs
weight: 170
---

## Something Went Wrong

Your agent was supposed to route users to the right specialist. Instead, it's sending billing questions to technical support, and nobody knows why.

You added logging, but it's not helping. The output is noise—function calls, token counts, timing data—but no answers. Why did it make that routing decision? Why didn't it use the tool you expected? Why did it suddenly stop mid-conversation?

Traditional debugging doesn't work for AI agents. They're not deterministic. They're not functions you can step through. But they do give signals—*if you know how to listen*.

Syrin's debugging system is built on a simple principle: **everything your agent does, it announces**. Every LLM call, every tool execution, every budget check, every context switch—emitted as a hook that you can observe, log, or act on.

## The Problem

AI agents are notoriously opaque:

- **Black box behavior** — You send input, get output, nothing in between
- **Non-deterministic output** — Same prompt, different results
- **Hidden state changes** — Memory modified, budget spent, context rotated
- **Tool mystery** — Did it call the tool? With what arguments? Why did it fail?
- **Cost blindness** — No visibility into what's being spent

Traditional approaches:
- `print()` statements everywhere (noise, not signal)
- Scattered logging (no unified view)
- Guessing based on final output (frustrating)

## The Solution

Syrin provides **first-class observability** at every step:

1. **Hooks** — Subscribe to lifecycle events (LLM calls, tool executions, etc.)
2. **Debug mode** — Rich console output showing everything
3. **Audit logging** — Persist events to files for compliance
4. **Tracing** — Correlate events across distributed systems

```python
from syrin import Agent, Hook, Model

agent = Agent(model=Model.OpenAI("gpt-4o", api_key="your-api-key"))

# Subscribe to what interests you
agent.events.on(Hook.AGENT_RUN_END, lambda ctx: print(f"Cost: ${ctx.cost:.4f}"))
agent.events.on(Hook.TOOL_CALL_END, lambda ctx: print(f"Tool: {ctx.name}"))
```

**What just happened**: You just hooked into the agent's lifecycle. Now you see every tool call and the final cost.

## How Hooks Work

Hooks are **event subscriptions**. When something happens in the agent, it emits a hook with context data:

```
┌─────────────────────────────────────────────────────┐
│  Agent Lifecycle                                      │
│                                                      │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌────────┐ │
│  │  Input  │─▶│   LLM   │─▶│  Tools  │─▶│ Output │ │
│  └─────────┘  └─────────┘  └─────────┘  └────────┘ │
│       │            │            │            │     │
│       ▼            ▼            ▼            ▼     │
│  AGENT_RUN    LLM_REQUEST   TOOL_CALL   AGENT_RUN  │
│  _START       _START/END    _END        _END       │
│                                                      │
│  Every step emits a hook you can subscribe to        │
└─────────────────────────────────────────────────────┘
```

## What You Can Observe

| Category | Hooks | Use Cases |
|----------|-------|-----------|
| **Agent lifecycle** | `AGENT_RUN_START`, `AGENT_RUN_END` | Track requests, measure duration |
| **LLM calls** | `LLM_REQUEST_START`, `LLM_REQUEST_END` | Token counts, cost, latency |
| **Tool execution** | `TOOL_CALL_START`, `TOOL_CALL_END` | Tool usage, arguments, results |
| **Budget** | `BUDGET_CHECK`, `BUDGET_THRESHOLD`, `BUDGET_EXCEEDED` | Cost control, alerts |
| **Memory** | `MEMORY_STORE`, `MEMORY_RECALL`, `MEMORY_FORGET` | What was remembered |
| **Handoff** | `HANDOFF_START`, `HANDOFF_END` | Agent transfers |
| **Context** | `CONTEXT_COMPACT`, `CONTEXT_THRESHOLD` | Token usage, compaction |

## Quick Example: Debug Mode

Enable debug mode for instant visibility:

```python
from syrin import Agent, Model

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    system_prompt="You are a helpful assistant.",
    debug=True,  # Enable debug output
)

agent.run("Hello")
```

**Console output:**
```
▶ 14:32:01.001 agent.run.start
     Input: Hello
     Model: gpt-4o

💬 14:32:01.150 llm.request.start
     Iteration: 0

💬 14:32:01.200 llm.request.end
     Cost: $0.000150
     Tokens: 45

✓ 14:32:01.250 agent.run.end
     Cost: $0.000150
     Duration: 250ms
```

**What just happened**: With one flag, you see the complete execution flow. You know exactly when each step happened, how much it cost, and what the agent did.

## Quick Example: Custom Hooks

Subscribe only to what you care about:

```python
from syrin import Agent, Hook, Model

model = Model.OpenAI("gpt-4o", api_key="your-api-key")

agent = Agent(model=model, system_prompt="You are helpful.")


# Track cost
def track_cost(ctx):
    print(f"Request cost: ${ctx.cost:.4f}")
    print(f"Tokens: {ctx.tokens}")


# Track tools
def track_tools(ctx):
    print(f"Tool called: {ctx.name}")
    print(f"Arguments: {ctx.arguments}")
    print(f"Result: {str(ctx.result)[:100]}")


# Track budget
def alert_budget(ctx):
    print(f"Budget at {ctx.threshold_percent}%!")


agent.events.on(Hook.AGENT_RUN_END, track_cost)
agent.events.on(Hook.TOOL_CALL_END, track_tools)
agent.events.on(Hook.BUDGET_THRESHOLD, alert_budget)

result = agent.run("Use your tools to find today's weather")
```

## Why Hooks Over Logging?

| Feature | `print()` | Hooks |
|---------|-----------|-------|
| **Structured data** | Strings only | Typed context |
| **Subscribe selectively** | All or nothing | Filter by event |
| **Modify behavior** | No | `before()` hooks can change context |
| **Side effects** | No | Fire webhooks, write files |
| **Correlation** | Manual | Built-in trace IDs |
| **Production-ready** | Ad-hoc | Audit logging, OTLP export |

## See Also

- [Hooks](/agent-kit/debugging/hooks) — Complete hooks reference with examples
- [Hooks Reference](/agent-kit/debugging/hooks-reference) — Every hook and its context
- [Serving: HTTP API](/agent-kit/production/serving-http) — Debug mode in HTTP serving
- [Playground](/agent-kit/production/playground) — Visual observability panel
