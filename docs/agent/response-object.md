---
title: Response Object
description: Everything you get back from an agent—and why it matters
weight: 65
---

## Your Agent's Report Card

You asked your agent to do something. It did. Now what?

The `Response` object is your agent's report card. It's not just "the text it said." It's a complete audit trail: how much it cost, how many tokens it burned, what tools it called, how long it took, and whether it actually finished or got stopped mid-way.

Most libraries give you a string. We give you **observability**.

## The Problem: You Can't Improve What You Can't See

Picture this: Your agent is "working." Users say it's slow. Is it the model? The tools? The context window? Without visibility, you're guessing.

Or this: Your agent runs fine for the first 10 requests, then starts hallucinating. Why? Maybe context is growing. Maybe memory is polluted. But you don't know because you're flying blind.

**The Response object changes this.** Every call gives you everything: cost, tokens, iterations, guardrail results, memory operations, routing decisions. It's not just output—it's **feedback**.

## Basic Response Anatomy

```python
from syrin import Agent, Model

class Assistant(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")

agent = Assistant()
response = agent.run("What is 2 + 2?")

# The basics
print(response.content)      # "2 + 2 equals 4."
print(response.cost)         # 0.000015
print(response.tokens)      # TokenUsage(input=45, output=8, total=53)
print(response.stop_reason)  # StopReason.END_TURN
print(response.duration)     # 0.42 (seconds)
```

**Output:**
```
2 + 2 equals 4.
0.000015
TokenUsage(input_tokens=45, output_tokens=8, total_tokens=53)
END_TURN
0.42
```

## The Full Response Schema

Here's every field, organized by what it tells you:

### The Main Answer

| Field | Type | What It Is |
|-------|------|------------|
| `content` | `str` | The main response text |
| `raw` | `str` | Raw text before parsing |

```python
# Quick access
print(response.content)       # The text
print(str(response))          # Same as content (Response is stringable)
```

### The Bill (Cost)

| Field | Type | What It Is |
|-------|------|------------|
| `cost` | `float` | Total cost in USD |
| `budget_remaining` | `float \| None` | Remaining budget |
| `budget_used` | `float \| None` | Spent this run |

```python
print(f"This call cost: ${response.cost:.6f}")

# With budget configured
if response.budget_remaining is not None:
    print(f"Left to spend: ${response.budget_remaining:.4f}")
```

### The Token Burn

| Field | Type | What It Is |
|-------|------|------------|
| `tokens` | `TokenUsage` | Input/output/total tokens |

```python
tokens = response.tokens
print(f"Input: {tokens.input_tokens}")
print(f"Output: {tokens.output_tokens}")
print(f"Total: {tokens.total_tokens}")
```

**Why does this matter?** Tokens are money. If input_tokens is 80,000 and you're sending the same context every time, you're wasting cash. Optimization starts with measurement.

### Why Did It Stop?

| Field | Type | What It Is |
|-------|------|------------|
| `stop_reason` | `StopReason` | Why the run ended |

```python
from syrin.enums import StopReason

response = agent.run("Complex task with many tools")

if response.stop_reason == StopReason.END_TURN:
    print("Completed normally")
elif response.stop_reason == StopReason.BUDGET:
    print("Stopped by budget limit")
elif response.stop_reason == StopReason.MAX_ITERATIONS:
    print("Hit the iteration cap (tools taking too long)")
elif response.stop_reason == StopReason.TOOL_ERROR:
    print("A tool failed")
elif response.stop_reason == StopReason.GUARDRAIL:
    print("Blocked by guardrail")
```

**All StopReason values:**

| Value | When |
|-------|------|
| `END_TURN` | Completed successfully |
| `BUDGET` | Hit cost limit |
| `MAX_ITERATIONS` | Tool loop exceeded `max_tool_iterations` |
| `TIMEOUT` | Timed out |
| `TOOL_ERROR` | Tool raised an exception |
| `HANDOFF` | Transferred to another agent |
| `GUARDRAIL` | Input/output blocked |
| `CANCELLED` | Cancelled |

### The Iteration Count

| Field | Type | What It Is |
|-------|------|------------|
| `iterations` | `int` | Number of LLM/tool cycles |

```python
# One response = 1 iteration
# With tools: each tool call = +1 iteration
print(f"Ran for {response.iterations} iterations")
```

**Why care?** If iterations is high (say, 10) but your task should need 2, something's wrong. Maybe tools are failing. Maybe the agent is confused.

### The Model

| Field | Type | What It Is |
|-------|------|------------|
| `model` | `str` | Model ID used |
| `model_used` | `str \| None` | Actual model (for routing/OpenRouter) |
| `routing_reason` | `RoutingReason \| None` | Why model was chosen |

```python
print(f"Model: {response.model}")
# "openai/gpt-4o-mini"
```

## The Full Report: agent.report

The `report` object contains detailed metrics from every subsystem:

```python
response = agent.run("Your request")

# Access the report
report = response.report

# Guardrail results
print(f"Input passed: {report.guardrail.input_passed}")
print(f"Output passed: {report.guardrail.output_passed}")
print(f"Was blocked: {report.guardrail.blocked}")

# Context usage
print(f"Initial tokens: {report.context.initial_tokens}")
print(f"Final tokens: {report.context.final_tokens}")
print(f"Compactions: {report.context.compressions}")

# Memory operations
print(f"Recalls: {report.memory.recalls}")
print(f"Stores: {report.memory.stores}")
print(f"Forgets: {report.memory.forgets}")

# Token details
print(f"Input tokens: {report.tokens.input_tokens}")
print(f"Output tokens: {report.tokens.output_tokens}")
print(f"Total tokens: {report.tokens.total_tokens}")
print(f"Cost: ${report.tokens.cost_usd:.6f}")

# Rate limiting
print(f"Rate limit checks: {report.ratelimits.checks}")
print(f"Throttles: {report.ratelimits.throttles}")

# Checkpointing
print(f"Saves: {report.checkpoints.saves}")
print(f"Loads: {report.checkpoints.loads}")
```

### Report Sub-Objects

| Report | Contains |
|--------|----------|
| `report.guardrail` | Input/output validation results |
| `report.context` | Token counts and compaction |
| `report.memory` | Remember/recall/forget operations |
| `report.tokens` | Detailed token breakdown |
| `report.output` | Structured output validation |
| `report.ratelimits` | Rate limit checks |
| `report.checkpoints` | Saves and loads |
| `report.grounding` | Citation verification (when enabled) |

## The Execution Trace

`response.trace` shows every step the agent took. Think of it as the "flight recorder" for your agent's execution. This is built from hooks internally, but you get it automatically in the Response.

```python
for step in response.trace:
    print(f"Step: {step.step_type}")
    print(f"  Model: {step.model}")
    print(f"  Tokens: {step.tokens}")
    print(f"  Cost: ${step.cost_usd:.6f}")
    print(f"  Latency: {step.latency_ms}ms")
    if step.extra:
        print(f"  Extra: {step.extra}")
```

**Sample trace:**
```
Step: llm_call
  Model: openai/gpt-4o
  Tokens: 142
  Cost: $0.000142
  Latency: 320ms

Step: tool_call
  Extra: {'tool_name': 'search', 'arguments': {'query': 'weather'}}

Step: tool_result
  Extra: {'tool_name': 'search', 'duration_ms': 45}

Step: llm_call
  Tokens: 289
  Cost: $0.000289
  Latency: 410ms
```

### Hooks vs Trace: Two Views of the Same Data

| Aspect | Hooks | Trace |
|--------|-------|-------|
| **When** | Real-time, during execution | Post-hoc, after completion |
| **Use case** | Live dashboards, alerts | Debugging, auditing |
| **Access** | `agent.events.on(Hook.XXX, handler)` | `response.trace` |
| **Persistence** | Fire and forget | Stored in Response |

Use **hooks** when you need to react during execution (alerts, monitoring). Use **trace** when you need to audit or debug after.

```python
# Hooks: React during execution
agent.events.on(Hook.BUDGET_THRESHOLD, lambda ctx: send_alert(ctx))

# Trace: Review after execution
response = agent.run("Task")
for step in response.trace:
    log_step(step)  # Audit trail
```

## The Tool Calls

`response.tool_calls` shows what tools the model requested (before execution):

```python
for call in response.tool_calls:
    print(f"Tool: {call.name}")
    print(f"Arguments: {call.arguments}")
```

**Note:** This is what the model *requested*, not what happened. For execution results, check the trace.

## Structured Output: Getting Typed Responses

When you need data, not text, use structured output:

```python
from pydantic import BaseModel
from syrin import Agent, Model, Output

class UserInfo(BaseModel):
    name: str
    age: int
    email: str

class Extractor(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")
    output = Output(UserInfo)

agent = Extractor()
response = agent.run("John is 30 years old, email: john@example.com")

# Access structured data
print(response.structured.parsed)        # UserInfo instance
print(response.structured.parsed.name)   # "John"
print(response.structured.parsed.age)    # 30
print(response.structured.parsed.email)  # "john@example.com"

# Convenience accessors
print(response.parsed)                    # Same as structured.parsed
print(response.data)                     # Dict form
```

### Structured Output Validation

```python
print(f"Valid: {response.structured.is_valid}")
print(f"Errors: {response.structured.all_errors}")
print(f"Attempts: {len(response.structured.validation_attempts)}")
```

## Media Attachments

For agents that generate images, audio, or video:

```python
response = agent.run("Generate an image of a sunset")

for attachment in response.attachments:
    print(f"Type: {attachment.type}")           # "image"
    print(f"Content-Type: {attachment.content_type}")  # "image/png"
    
    if attachment.content_bytes:
        # Binary data
        with open("output.png", "wb") as f:
            f.write(attachment.content_bytes)
    
    if attachment.url:
        # URL reference
        print(f"URL: {attachment.url}")
```

## Routing Information

When using model routing (`model=[gpt-4o-mini, gpt-4o]`):

```python
response = agent.run("Explain quantum physics")

# Why was this model chosen?
if response.routing_reason:
    print(f"Selected: {response.routing_reason.selected_model}")
    print(f"Task type: {response.routing_reason.task_type}")
    print(f"Reason: {response.routing_reason.reason}")

# What actually ran?
print(f"Model used: {response.model_used}")
print(f"Actual cost: {response.actual_cost}")
```

## Budget Status

```python
# Quick access
budget = response.budget
print(budget)
# "BudgetStatus(remaining=$0.85, used=$0.15, total=$1.00)"

print(f"Remaining: ${budget.remaining:.4f}")
print(f"Used: ${budget.used:.4f}")
print(f"Total: ${budget.total}")
```

## Boolean and String Magic

```python
# Boolean: True if completed successfully
if response:
    print("Got a complete response")
else:
    print(f"Stopped early: {response.stop_reason}")

# String: Same as content
print(response)  # Prints the text content
```

## Complete Example: Debugging an Expensive Agent

```python
from syrin import Agent, Model, Budget
from syrin.enums import ExceedPolicy, StopReason

class ExpensiveAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")
    budget = Budget(max_cost=0.50, exceed_policy=ExceedPolicy.WARN)

agent = ExpensiveAgent()

# Run a request
response = agent.run("Research quantum computing applications")

# Full diagnostic
print("=" * 50)
print("DIAGNOSTIC REPORT")
print("=" * 50)

print(f"\n📝 Content (first 100 chars):")
print(f"   {response.content[:100]}...")

print(f"\n💰 Cost:")
print(f"   This call: ${response.cost:.6f}")
print(f"   Budget remaining: ${response.budget_remaining:.4f}")
print(f"   Budget status: {response.budget}")

print(f"\n📊 Tokens:")
print(f"   Input: {response.tokens.input_tokens}")
print(f"   Output: {response.tokens.output_tokens}")
print(f"   Total: {response.tokens.total_tokens}")

print(f"\n🔄 Execution:")
print(f"   Stop reason: {response.stop_reason.value}")
print(f"   Iterations: {response.iterations}")

print(f"\n🛡️ Guardrails:")
print(f"   Input passed: {response.report.guardrail.input_passed}")
print(f"   Output passed: {response.report.guardrail.output_passed}")
print(f"   Blocked: {response.report.guardrail.blocked}")

print(f"\n🧠 Memory:")
print(f"   Recalls: {response.report.memory.recalls}")
print(f"   Stores: {response.report.memory.stores}")

print(f"\n⏱️ Performance:")
print(f"   Duration: {response.duration:.2f}s")

if response.stop_reason != StopReason.END_TURN:
    print(f"\n⚠️ WARNING: Did not complete normally!")
    print(f"   Reason: {response.stop_reason.value}")
```

**Sample output:**
```
==================================================
DIAGNOSTIC REPORT
==================================================

📝 Content (first 100 chars):
   Quantum computing harnesses quantum mechanical phenomena like superposition...

💰 Cost:
   This call: $0.023456
   Budget remaining: $0.476544
   Budget status: BudgetStatus(remaining=$0.48, used=$0.02, total=$0.50)

📊 Tokens:
   Input: 1245
   Output: 567
   Total: 1812

🔄 Execution:
   Stop reason: end_turn
   Iterations: 3

🛡️ Guardrails:
   Input passed: True
   Output passed: True
   Blocked: False

🧠 Memory:
   Recalls: 2
   Stores: 1

⏱️ Performance:
   Duration: 1.42s
```

## Common Patterns

### Pattern 1: Check for Success

```python
response = agent.run("Task")
if response:
    # Success
    process(response.content)
else:
    # Handle failure
    print(f"Failed: {response.stop_reason}")
```

### Pattern 2: Extract Structured Data

```python
response = agent.run("Extract: Alice, 25, alice@example.com")
if response.structured:
    user = response.structured.parsed
    print(user.name, user.age, user.email)
```

### Pattern 3: Monitor Costs

```python
response = agent.run("Task")
if response.cost > 0.10:
    print(f"Expensive call: ${response.cost:.4f}")
    # Alert, log, etc.
```

### Pattern 4: Debug Iterations

```python
response = agent.run("Complex task")
if response.iterations > 5:
    print(f"High iteration count: {response.iterations}")
    # Investigate tool performance
```

### Pattern 5: Check Memory Health

```python
response = agent.run("User input")
memory_report = response.report.memory
if memory_report.recalls > 10:
    print("Excessive memory recalls - check relevance scoring")
if memory_report.stores > 3:
    print("Many stores - agent may be remembering too much")
```

## The Response in Context

Here's how the Response fits into the full execution flow:

**Before response() returns:**
1. Input guardrails validate user input
2. Memory recalls relevant information
3. Messages are built (system prompt + memory + history)
4. REACT loop runs (LLM calls + tool executions)
5. Output guardrails validate the response
6. Memory stores new information
7. Budget is recorded

**The Response contains:**
- `content` — The main response text
- `cost` — How much this call cost
- `tokens` — Token usage breakdown
- `stop_reason` — Why the agent stopped
- `iterations` — How many tool loops
- `report` — Detailed metrics from all subsystems
- `trace` — Step-by-step execution record

## What's Next?

- [Structured Output](/agent-kit/agent/structured-output) - Get typed data back
- [Streaming](/agent-kit/agent/streaming) - Real-time responses
- [Tools](/agent-kit/agent/tools) - What tools do
- [Budget](/agent-kit/core/budget) - Cost control

## See Also

- [Running Agents](/agent-kit/agent/running-agents) - How to call response()
- [Loop Strategies](/agent-kit/agent/running-agents) - How the agent thinks
- [Agent Anatomy](/agent-kit/agent/anatomy) - Components overview
- [Memory](/agent-kit/core/memory) - What was remembered
