# Agent Overview

## What is an Agent?

An **Agent** in Syrin is an AI-powered program that:

- Talks to an LLM (OpenAI, Anthropic, Google, Ollama, etc.)
- Can use **tools** (search, calculate, look up data)
- Can **remember** and **recall** information
- Respects **budgets** and cost limits
- Emits **lifecycle events** (hooks) for observability
- Supports **multi-agent** patterns (handoff, spawn, pipelines)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Agent                                │
├─────────────────────────────────────────────────────────────┤
│  Model          │  LLM provider (OpenAI, Anthropic, etc.)   │
│  System Prompt  │  Instructions for the agent               │
│  Tools          │  Functions the agent can call             │
│  Loop           │  Execution strategy (REACT, SingleShot…)  │
│  Memory         │  Persistent + conversation memory         │
│  Budget         │  Cost limits and thresholds               │
│  Guardrails     │  Input/output validation                  │
│  Events         │  Lifecycle hooks                          │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  response(user_input) → Response                             │
│  arun(user_input)    → Response (async)                      │
│  stream(user_input)  → Iterator[StreamChunk]                 │
│  astream(user_input) → AsyncIterator[StreamChunk]            │
└─────────────────────────────────────────────────────────────┘
```

## Key Concepts

### Model

The LLM that powers the agent. Required. Use `Model.OpenAI()`, `Model.Anthropic()`, `Model.Ollama()`, etc.

```python
from syrin.model import Model

model = Model.OpenAI("gpt-4o-mini", api_key="sk-...")
```

### System Prompt

Instructions that define the agent’s personality and behavior. Passed with every request.

### Tools

Functions the agent can call during a run (e.g., search, compute, API calls). Defined with `@syrin.tool`.

### Loop

Controls how the agent runs:

- **ReactLoop** (default) — Think → Act → Observe with tools
- **SingleShotLoop** — One LLM call, no tool loop
- **HumanInTheLoop** — User approval before each tool call
- **PlanExecuteLoop** — Plan steps, then run them
- **CodeActionLoop** — Generate and run code

### Memory

- **Persistent memory** — Long-term storage via `remember()` / `recall()` / `forget()`
- **Conversation memory** — Session-only chat history

### Budget

Cost limits (e.g., per run, per period) with optional thresholds (switch model, stop, warn).

### Events

Hooks emitted during execution (e.g. `AGENT_RUN_START`, `LLM_REQUEST_END`, `TOOL_CALL_END`). Register handlers with `agent.events.on()`.

## Execution Flow

1. User calls `agent.response("Hello")` or `agent.arun("Hello")`
2. **Input guardrails** run (if configured)
3. **Message building**: system prompt + persistent memory context + conversation history + user input
4. **Loop execution** (e.g. ReactLoop):
   - LLM call
   - If tool calls → run tools → append results → loop
   - If no tool calls → finish
5. **Output guardrails** run on final text (if configured)
6. **Structured output** validation (if `output=Output(MyModel)` is set)
7. **Response** returned with content, cost, tokens, and reports

## Minimum Agent

```python
from syrin import Agent
from syrin.model import Model

agent = Agent(model=Model.OpenAI("gpt-4o-mini"))
response = agent.response("What is 2+2?")
print(response.content)  # "4"
```

## Full-Featured Agent

```python
from syrin import Agent, Budget, Hook
from syrin.model import Model
from syrin.tool import tool

@tool
def search(query: str) -> str:
    """Search the web for information."""
    return f"Results for: {query}"

class ResearchAgent(Agent):
    model = Model.OpenAI("gpt-4o")
    system_prompt = "You are a research specialist. Use tools when needed."
    tools = [search]
    budget = Budget(run=1.0)

agent = ResearchAgent(debug=True)
agent.events.on(Hook.AGENT_RUN_END, lambda ctx: print(f"Cost: ${ctx.get('cost', 0):.4f}"))
response = agent.response("Research quantum computing")
print(response.content)
print(response.cost)
```

## Next Steps

- [Creating Agents](creating-agents.md) — Class vs instance, inheritance
- [Constructor Reference](constructor.md) — All parameters
- [Running Agents](running.md) — Sync, async, streaming
