---
title: Minimal Examples
description: Create your first agents, use memory, and inspect responses
weight: 310
---

## Minimal Examples

Start here to understand core Syrin concepts: agents, models, memory, and responses.

## Your First Agent

The simplest possible agent with a budget and prompt template.

```python
from syrin import Agent, Model, Budget

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
    budget=Budget(max_cost=0.10),
    system_prompt="You are a helpful assistant.",
)

result = agent.run("What is 2 + 2?")
print(result.content)  # "2 + 2 equals 4."
```

**What just happened:**
1. Created a model with your API key
2. Set a budget of $0.10 per run
3. Asked the agent a question
4. Got back a `Response` object with content and cost

## Using Prompt Templates

Dynamic system prompts with `@prompt` decorator.

```python
from syrin import Agent, Model, prompt

@prompt
def assistant_prompt(name: str, specialty: str) -> str:
    return f"You are {name}, an expert in {specialty}."

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
    system_prompt=assistant_prompt(name="Dr. Smith", specialty="medicine"),
)

result = agent.run("What causes headaches?")
```

**What just happened:**
1. Defined a prompt template function with parameters
2. Called it with specific values to generate the system prompt
3. The agent responds with the configured persona

## Multi-Turn Memory

Add conversation history with `BufferMemory`.

```python
from syrin import Agent, Model, Memory
from syrin.enums import MemoryType, WriteMode

memory = Memory(
    backend=MemoryBackend.SQLITE,
    path="conversation.db",
    write_mode=WriteMode.SYNC,
    types=[MemoryType.CORE, MemoryType.EPISODIC],
)

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
    memory=memory,
    system_prompt="You are a helpful assistant with memory.",
)

# First turn
result1 = agent.run("My name is Alice.")
print(result1.content)

# Second turn - agent remembers "Alice"
result2 = agent.run("What is my name?")
print(result2.content)  # "Your name is Alice."
```

**What just happened:**
1. Created SQLite-backed memory for persistence
2. Attached memory to the agent
3. After two turns, the agent automatically recalls "Alice"

## Inspecting Responses

The `Response` object contains everything about an agent run.

```python
from syrin import Agent, Model

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
    system_prompt="You are helpful.",
)

result = agent.run("Explain photosynthesis.")

# Access all response properties
print(f"Content: {result.content}")
print(f"Cost: ${result.cost:.6f}")
print(f"Tokens: {result.usage.total_tokens}")
print(f"Model: {result.model}")
print(f"Finish reason: {result.finish_reason}")
print(f"Steps: {result.steps}")
print(f"Tools used: {[t.name for t in result.tool_calls]}")
```

**What just happened:**
1. Got back a rich `Response` object
2. Examined content, cost, token usage, and metadata
3. Tracked which tools were called during the run

## Budget Enforcement

Set limits and get notified when exceeded.

```python
from syrin import Agent, Model, Budget
from syrin.enums import ExceedPolicy
from syrin.hooks import Hook

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
    budget=Budget(max_cost=0.01),  # Very small budget
    system_prompt="You are thorough and verbose.",
)

# Get notified when budget is exceeded
def on_budget_exceeded(ctx):
    print(f"Budget exceeded! Spent: ${ctx.get('cost', 0):.6f}")

agent.events.on(Hook.BUDGET_EXCEEDED, on_budget_exceeded)

result = agent.run("Write a detailed essay about history.")
# Will likely hit budget and truncate or error
```

**What just happened:**
1. Set an intentionally small budget
2. Hooked into the `BUDGET_EXCEEDED` event
3. Observed what happens when the agent exceeds its budget

## Running the Examples

```bash
# From project root
PYTHONPATH=. python examples/01_minimal/hello_agent.py
PYTHONPATH=. python examples/01_minimal/hello_memory.py
```

## What's Next?

- Learn about [tasks and structured output](/examples/tools-patterns)
- Explore [memory systems](/core/memory) in depth
- Understand [budget management](/core/budget)

## See Also

- [Agents documentation](/agent/overview)
- [Memory documentation](/core/memory)
- [Response object reference](/agent/response-object)
