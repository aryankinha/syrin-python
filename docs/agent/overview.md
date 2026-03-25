---
title: Agents Overview
description: What is an Agent in Syrin and why you'd want one
weight: 60
---

## Your AI Agent: Not Just a Chatbot Wrapper

You've seen them. Those "AI agents" that are really just a fancy API call with a for-loop. They hallucinate answers, burn through your budget like there's no tomorrow, and have no memory of what happened five messages ago.

Syrin agents are different. They're built for **production**—real applications where cost matters, memory persists, tools actually work, and you can see exactly what's happening under the hood.

## What is an Agent, Anyway?

An agent is an AI-powered program that:

- Talks to an LLM (OpenAI, Anthropic, Google, Ollama, etc.)
- Can call **tools** (search, calculate, make API calls)
- Can **remember** and **recall** information across sessions
- Respects **budgets**—literally stops when it hits your cost limit
- Emits **lifecycle events** for full observability
- Supports **multi-agent** patterns (handoff, spawn, pipelines)

Think of it as an employee. You give them a brain (model), instructions (system prompt), tools (abilities), and a budget (allowance). They work until the budget runs out or the task is done.

## The Problem with Plain API Calls

Here's what happens with a basic API call:

```python
# The "AI agent" that will haunt your dreams
import openai
response = openai.ChatCompletion.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}]
)
print(response.choices[0].message.content)
```

**What you get:** A single response. No tools. No memory. No budget control. No visibility. Just... hope that worked.

## The Syrin Solution: Agents with Superpowers

Here's what an actual agent looks like:

```python
from syrin import Agent, Model, Budget
from syrin.tool import tool
from syrin.enums import MemoryType, ExceedPolicy

# Define a tool the agent can use
@tool
def search_web(query: str) -> str:
    """Search the web for current information."""
    # Real implementation would call a search API
    return f"Search results for: {query}"

# Create an agent with budget, memory, and tools
class ResearchAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")
    system_prompt = """
        You are a thorough research assistant. Use tools when you need 
        current information. Be precise and cite your sources.
    """
    tools = [search_web]
    budget = Budget(max_cost=1.00, exceed_policy=ExceedPolicy.STOP)

# Create and use the agent
agent = ResearchAgent()
response = agent.run("What are the latest developments in AI?")
print(f"Response: {response.content}")
print(f"Cost: ${response.cost:.4f}")
```

**What just happened:**
1. Agent created with a specific model and personality
2. Tool registered so the agent can search the web
3. Budget set to $1.00 max per run
4. Response received with full cost transparency

## Agent vs Script: When to Use Each

| Scenario | Use an Agent | Use a Script |
|----------|-------------|--------------|
| Multi-turn conversations | ✅ | ❌ |
| Tool use required | ✅ | ❌ |
| Budget control needed | ✅ | ❌ |
| Persistent memory across sessions | ✅ | ❌ |
| Single LLM call | ✅ | ✅ |
| Simple transformation | ✅ | ✅ |

## What's Inside an Agent

Each agent has these components:

- **Model** — The brain (OpenAI, Anthropic, etc.)
- **System Prompt** — The instruction manual
- **Tools** — What the agent can DO
- **Memory** — What the agent remembers
- **Context** — Token budget and compaction
- **Budget** — Cost control with thresholds
- **Guardrails** — Safety rails for input/output
- **Loop** — How the agent thinks (REACT, etc.)

Each of these is a **dial you can turn**. We'll cover each in detail, but first...

## The Simplest Possible Agent

```python
from syrin import Agent, Model

# This is valid. It works. It's not recommended for production.
agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
)
response = agent.run("Hello!")
print(response.content)
```

That's it. No tools, no memory, no budget. Just a brain and a message.

## A More Complete Example

```python
from syrin import Agent, Model, Budget
from syrin.tool import tool
from syrin.enums import ExceedPolicy
from syrin.memory import Memory, MemoryPreset

@tool
def get_weather(city: str) -> str:
    """Get current weather for a city."""
    return f"Sunny, 72°F in {city}"

class WeatherAssistant(Agent):
    # The brain - pick your model
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")
    
    # The personality - how it should behave
    system_prompt = "You are a friendly weather assistant."
    
    # The tools - what it can do
    tools = [get_weather]
    
    # The wallet - how much it can spend
    budget = Budget(max_cost=0.50, exceed_policy=ExceedPolicy.STOP)
    
    # The memory - what it remembers
    memory = MemoryPreset.STANDARD  # Core + Episodic memory

# Create and use
agent = WeatherAssistant()
response = agent.run("What's the weather in Tokyo?")
print(f"Reply: {response.content}")
print(f"Spent: ${agent.budget_state.spent:.4f}")
```

## How an Agent Thinks (The Loop)

By default, Syrin uses **ReACT**—a think-act-observe loop:

```
1. Think: "The user asked about weather in Tokyo"
2. Act: Call the get_weather tool
3. Observe: "Sunny, 72°F in Tokyo"
4. Think: "Now I have the answer"
5. Respond: "It's sunny and 72°F in Tokyo!"
```

You can change this with `loop_strategy`:

```python
# Single shot = one LLM call, no tool loops
agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    loop_strategy=LoopStrategy.SINGLE_SHOT,  # Just one response
)
```

## Real Control, Real Visibility

The key difference with Syrin: **you control everything, and you see everything**.

```python
from syrin import Agent, Model, Budget, Hook
from syrin.enums import ExceedPolicy

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    budget=Budget(max_cost=0.10, exceed_policy=ExceedPolicy.WARN),
    debug=True,  # Print events to console
)

# Hook into any lifecycle event
agent.events.on(Hook.LLM_REQUEST_END, lambda ctx: print(f"Tokens: {ctx.tokens}"))
agent.events.on(Hook.BUDGET_THRESHOLD, lambda ctx: print(f"{ctx.percentage:.0f}% spent!"))

response = agent.run("Tell me about quantum computing")
print(f"Total cost: ${agent.budget_state.spent:.4f}")
```

This level of control is what makes Syrin agents production-ready.

## When NOT to Use an Agent

Agents add overhead. If you just need a single LLM call, use the model directly:

```python
# Don't do this:
agent = Agent(model=Model.OpenAI("gpt-4o"))
agent.run("Translate 'hello' to French")

# Do this instead:
from syrin.model import Model
model = Model.OpenAI("gpt-4o")
# ... make a single call
```

## What's Next?

- [Agent Anatomy](/agent/anatomy) - Deep dive into each component
- [Creating Agents](/agent/creating-agents) - Four ways to build an agent
- [Running Agents](/agent/running-agents) - Sync, async, and streaming
- [Builder Pattern](/agent/builder-pattern) - Fluent agent construction

## See Also

- [Models](/core/models) - Choosing the right AI brain
- [Memory](/core/memory) - Making agents remember
- [Budget](/core/budget) - Controlling costs
- [Tools](/agent/tools) - Giving agents abilities
