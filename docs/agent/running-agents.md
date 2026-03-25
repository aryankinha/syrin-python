---
title: Running Agents
description: Four ways to execute your agent—sync, async, and streaming
weight: 64
---

## Making Your Agent Work

You've built your agent. You've configured its brain, given it tools, set a budget. Now what?

This page is about *execution*—how to tell your agent "go do this" and get results back. But here's the thing: not all execution patterns are created equal. The choice between sync, async, and streaming isn't just technical trivia—it's the difference between a responsive UI and a frozen one, between getting full tool support and... not.

Let's make sure you pick the right tool for the job.

## The Four Execution Modes

| Method | Returns | Tools Run? | Use When |
|--------|---------|------------|----------|
| `response()` | `Response` | ✅ Yes | Scripts, CLI, blocking code |
| `arun()` | `Response` | ✅ Yes | FastAPI, async apps |
| `stream()` | `Iterator[StreamChunk]` | ❌ No | ChatGPT-style UI (no tools) |
| `astream()` | `AsyncIterator[StreamChunk]` | ❌ No | Async streaming (WebSockets) |

**The critical distinction:** `response()` and `arun()` run the full REACT loop—including tool execution, memory, guardrails, everything. `stream()` and `astream()` do exactly one LLM call. No tools. Choose wisely.

## response(): The Workhorse

This is what you'll use 90% of the time. It's synchronous, which means your code waits until the agent finishes before moving on.

```python
from syrin import Agent, Model

class Assistant(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")
    system_prompt = "You are a helpful assistant."

agent = Assistant()
response = agent.run("What is the capital of France?")
print(response.content)
```

**Output:**
```
Paris is the capital and largest city of France, with a population of over 2 million people in its urban area.
```

### What Just Happened?

```
1. Your code called response()
2. Agent ran guardrails (input validation)
3. Agent built messages (system prompt + memory + history)
4. Agent ran the REACT loop:
   - Called the LLM
   - Got a text response (no tools needed here)
5. Agent ran guardrails (output validation)
6. Response returned to your code
7. Your print() executed
```

### When to Use response()

- **Scripts** that run and exit
- **CLI tools** where blocking is fine
- **Anything with tools** (this is the only mode that runs tools)

### The Problem response() Solves

```python
# Without response():
# - How do you get structured data back?
# - How do you know how much it cost?
# - How do you handle budget limits?
# - How do you trace what happened?

# With response():
response = agent.run("Extract user info: John, 30")
print(response.content)      # "Name: John, Age: 30"
print(response.cost)         # 0.00015
print(response.stop_reason)  # END_TURN
```

One call. Full visibility. That's the promise.

## arun(): When You Can't Block

Sometimes you *can't* block. Your web server needs to handle thousands of requests. Your voice pipeline can't pause everything. That's where `arun()` comes in—it's the async version of `response()`.

```python
import asyncio
from syrin import Agent, Model

class Assistant(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")

async def handle_request(user_input: str):
    agent = Assistant()
    response = await agent.arun(user_input)
    return response.content

# Run it
result = asyncio.run(handle_request("Hello!"))
print(result)
```

### Real-World Use Case: FastAPI

```python
from fastapi import FastAPI
from syrin import Agent, Model

app = FastAPI()

class Assistant(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")

agent = Assistant()

@app.post("/chat")
async def chat(message: str):
    response = await agent.arun(message)
    return {
        "content": response.content,
        "cost": response.cost,
        "tokens": response.tokens.total_tokens,
    }
```

**Why not just use response()?** FastAPI runs on an async event loop. Blocking with `response()` would freeze the entire server for each request. With `await agent.arun()`, other requests can be processed while waiting.

### What Just Happened?

```
1. FastAPI received a POST /chat request
2. The async function started executing
3. await agent.arun() yielded control back to FastAPI
4. FastAPI handled other requests
5. LLM responded
6. arun() resumed, returned Response
7. FastAPI sent the JSON response
```

## stream(): Real-Time Feedback (No Tools)

Imagine you're building a ChatGPT clone. Users expect to see words appear letter by letter, like the AI is "thinking." That's streaming.

```python
from syrin import Agent, Model

class Assistant(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")

agent = Assistant()

print("Agent: ", end="", flush=True)
for chunk in agent.stream("Write a haiku about coding"):
    print(chunk.text, end="", flush=True)
print()
```

**Output:**
```
Agent: Code flows like streams
Logic builds on logic blocks
The bug finds its host
```

### StreamChunk: The Building Block

Each chunk contains:
- `text` — New characters (the delta)
- `accumulated_text` — Everything so far
- `cost_so_far` — Running cost
- `tokens_so_far` — Running token count
- `index` — Chunk number

```python
for chunk in agent.stream("Hello"):
    print(f"Chunk #{chunk.index}: '{chunk.text}'")
    print(f"  Total so far: '{chunk.accumulated_text}'")
    print(f"  Cost: ${chunk.cost_so_far:.6f}")
```

**Output:**
```
Chunk #0: 'Hello'
  Total so far: 'Hello'
  Cost: $0.000000
Chunk #1: ','
  Total so far: 'Hello,'
  Cost: $0.000010
Chunk #2: ' how'
  Total so far: 'Hello, how'
  Cost: $0.000020
```

### The Caveat: No Tool Execution

This is crucial. `stream()` does **one LLM call** and yields tokens as they arrive. It does NOT run tools.

```python
@tool
def search(query: str) -> str:
    """Search the web."""
    return f"Results for: {query}"

class ResearchAgent(Agent):
    model = Model.OpenAI("gpt-4o")
    tools = [search]

agent = ResearchAgent()

# DON'T DO THIS:
for chunk in agent.stream("What's the weather?"):
    print(chunk.text, end="")
# You'll get a raw response, but no tools will execute

# DO THIS INSTEAD:
response = agent.run("What's the weather?")
print(response.content)
# Tools execute, you get the real answer
```

**Why does this limitation exist?** Streaming is a low-level LLM feature. The model generates tokens; Syrin passes them through. Implementing tool execution in a streaming context requires complex state management. The solution: use `arun()` for full functionality, then stream the result if needed.

## astream(): Async Streaming

The async version of `stream()`. Use with WebSockets, async frameworks, or anywhere you can't block but need streaming.

```python
import asyncio
from syrin import Agent, Model

class Assistant(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")

async def stream_response(user_input: str):
    agent = Assistant()
    async for chunk in agent.astream(user_input):
        yield chunk.text

async def main():
    async for text in stream_response("Write a story"):
        print(text, end="", flush=True)

asyncio.run(main())
```

## Choosing the Right Mode

### Decision Guide

Here's how to pick the right execution method:

**Step 1: Do you need tools to execute?**
- Yes → Do you need async? → Yes: `arun()` / No: `response()`
- No → Continue to Step 2

**Step 2: Do you need streaming (real-time output)?**
- Yes → Do you need async? → Yes: `astream()` / No: `stream()`
- No → Use `response()` (simpler, returns full Response)

### Quick Reference

| Scenario | Method |
|----------|--------|
| Simple script | `response()` |
| CLI tool | `response()` |
| FastAPI endpoint | `arun()` |
| WebSocket handler | `astream()` |
| ChatGPT clone | `astream()` (or `arun()` + custom streaming) |
| Background job | `arun()` |
| Agent with tools | `response()` or `arun()` |
| Simple Q&A | `response()` |

## Per-Call Overrides

All four methods accept optional parameters for one-off customization:

```python
# Override context for this call
response = agent.run(
    "Complex query",
    context=Context(max_tokens=8000),  # Different context for this call
)

# Dynamic template variables
response = agent.run(
    "Help me with {task}",
    template_variables={"task": "coding"},
)

# Inject context (RAG results, etc.)
response = agent.run(
    "What does the docs say?",
    inject=[{"role": "system", "content": "[RAG] Python is a language..."}],
    inject_source_detail="rag",
)

# Override task type for routing
response = agent.run(
    "Write a function",
    task_type=TaskType.CODE,
)
```

## Error Handling

Things go wrong. Here's how to handle it:

### Budget Exceeded

```python
from syrin import Agent, Model, Budget
from syrin.exceptions import BudgetExceededError, BudgetThresholdError

class ExpensiveAgent(Agent):
    model = Model.OpenAI("gpt-4o")
    budget = Budget(max_cost=0.01)  # Very small budget

agent = ExpensiveAgent()

try:
    response = agent.run("Explain quantum computing")
except BudgetExceededError as e:
    print(f"Budget exceeded at ${e.current_cost:.4f}")
    print(f"Limit was ${e.limit:.4f}")
except BudgetThresholdError as e:
    print(f"Threshold reached: {e.threshold}")
```

### Tool Errors

```python
from syrin.exceptions import ToolExecutionError

try:
    response = agent.run("Do something")
except ToolExecutionError as e:
    print(f"Tool '{e.tool_name}' failed: {e.message}")
```

### Complete Error Handling Example

```python
from syrin.exceptions import BudgetExceededError, BudgetThresholdError, ToolExecutionError

try:
    response = agent.run(user_input)
    
    # Check if it completed successfully
    if response.stop_reason == StopReason.END_TURN:
        print("Success!")
        print(response.content)
    elif response.stop_reason == StopReason.BUDGET:
        print("Stopped due to budget")
    elif response.stop_reason == StopReason.MAX_ITERATIONS:
        print("Hit iteration limit")
    else:
        print(f"Stopped for: {response.stop_reason}")
        
except BudgetExceededError:
    print("Budget limit reached!")
except ToolExecutionError as e:
    print(f"Tool failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Budget Reset Behavior

Every call to `response()`, `arun()`, `stream()`, or `astream()` resets the **run budget** to zero. This ensures each request is tracked independently.

```python
# First request: $0.0001
response1 = agent.run("Hello")
print(agent.budget_state.spent)  # 0.0001

# Second request: starts fresh at $0
response2 = agent.run("Hi")
print(agent.budget_state.spent)  # 0.0002 (new request's cost)
```

**Period limits (day, week, month) persist across calls.** Only `run` resets per request.

## Response Timeouts

Long-running agents can hit timeouts. Configure at the application level:

```python
# Using asyncio with timeout
import asyncio

async def run_with_timeout():
    try:
        response = await asyncio.wait_for(
            agent.arun("Complex task"),
            timeout=30.0  # 30 seconds
        )
        return response.content
    except asyncio.TimeoutError:
        return "Request timed out"

# Or use the built-in timeout parameter (if supported)
response = agent.run("Task", timeout=30)
```

## What's Next?

- [Response Object](/agent/response-object) - Everything you get back
- [Loop Strategies](/agent/running-agents) - How the agent thinks
- [Structured Output](/agent/structured-output) - Get typed responses
- [Streaming](/agent/streaming) - Deep dive into streaming

## See Also

- [Agent Anatomy](/agent/anatomy) - Components overview
- [Creating Agents](/agent/creating-agents) - Build your agent
- [Budget](/core/budget) - Cost control
- [Serving](/production/serving) - Serve over HTTP
