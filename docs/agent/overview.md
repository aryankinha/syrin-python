---
title: Agent Overview
description: What a Syrin agent is, what it can do, and how it fits together
weight: 60
---

## What Is a Syrin Agent?

An agent is an AI-powered program that can think, act, and remember.

More precisely: an agent is a Python class that wraps an LLM and gives it capabilities — tools it can use, memory it can draw on, a budget it cannot exceed, and lifecycle hooks so you can see everything it does.

Think of it like hiring an employee. You give them a brain (the model), a job description (the system prompt), tools to do their job (the tools list), a spending limit (the budget), and a notebook to remember things (memory). They work until the task is done or the budget runs out.

## The Simplest Agent

```python
from syrin import Agent, Model

class Assistant(Agent):
    model = Model.mock()
    system_prompt = "You are helpful."

response = Assistant().run("Hello!")
print(response.content)
```

Output:

```
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore
```

That is the smallest valid Syrin agent. Two class attributes and you are running. Swap `Model.mock()` for any real model and you get real answers.

The class pattern is the recommended way to build agents — it enables inheritance, reuse, and clean testing. You can also create agents via the constructor (`Agent(model=..., system_prompt=...)`) for quick one-off scripts, but the class pattern is preferred for anything you'll maintain.

## A More Complete Agent

Here is the same pattern with the capabilities that make agents useful in production:

```python
from syrin import Agent, Budget, Memory, Model, tool
from syrin.enums import ExceedPolicy

@tool
def get_weather(city: str) -> str:
    """Get current weather for a city."""
    return f"Sunny, 72°F in {city}"

class WeatherAssistant(Agent):
    model = Model.mock()
    system_prompt = "You are a friendly weather assistant."
    tools = [get_weather]
    budget = Budget(max_cost=0.50, exceed_policy=ExceedPolicy.WARN)
    memory = Memory()

agent = WeatherAssistant()
response = agent.run("What's the weather in Tokyo?")
print(f"Reply: {response.content[:60]}")
print(f"Spent: ${agent.budget_state.spent:.6f}")
print(f"Tools available: {[t.name for t in agent.tools]}")
```

Output:

```
Reply: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed
Spent: $0.000046
Tools available: ['get_weather']
```

The tool is registered and available. With a real model, the agent would call `get_weather("Tokyo")` and use the result in its response. With the mock model, it returns placeholder text — but the plumbing is all there.

## What Lives Inside an Agent

Every Syrin agent has these components. All of them are optional except the model:

**Model** — The AI brain. Which LLM answers questions, which provider hosts it, and what the call costs. You can switch models mid-run if the budget runs low.

**System Prompt** — Instructions to the LLM. Defines personality, constraints, format requirements, and anything else the agent should always know. Can be a static string, a method that computes it dynamically, or a template with variables.

**Tools** — Functions the agent can call. The LLM decides when to call them and with what arguments. Syrin handles the call, captures the result, and feeds it back to the LLM. More on this in [Tools](/agent-kit/agent/tools).

**Memory** — A structured store with four types: Core, Episodic, Semantic, and Procedural. Memories persist across `run()` calls and optionally across restarts. More on this in [Memory](/agent-kit/core/memory).

**Budget** — A cost limit with a configurable behavior when the limit is hit: warn and continue, raise an exception, or switch to a cheaper model. The budget accumulates across all `run()` calls on the same agent instance. More on this in [Budget](/agent-kit/core/budget).

**Context** — The conversation history. Syrin manages token counts, compaction, and history windowing automatically. You can configure limits and strategies. More on this in [Context](/agent-kit/core/context).

**Guardrails** — Rules that check inputs and outputs. PII detection, prompt injection filtering, content filtering, length limits. More on this in [Guardrails](/agent-kit/agent/guardrails).

**Hooks** — 70+ lifecycle events you can subscribe to. Every LLM call, every tool execution, every budget check. More on this in [Hooks](/agent-kit/debugging/hooks).

## How the Agent Loop Works

By default, Syrin uses the REACT loop — Reason, Act, Observe, repeat:

1. The agent receives your input
2. It calls the LLM with the system prompt, conversation history, and your input
3. If the LLM wants to call a tool, Syrin calls it and feeds the result back
4. Steps 2-3 repeat until the LLM gives a final answer
5. The final answer is wrapped in a `Response` object and returned to you

If you give your agent no tools, step 3 never happens. One LLM call, one response. You can also explicitly use `LoopStrategy.SINGLE_SHOT` to force a single call even if tools are available.

## Class Definition vs. Instance

The class defines what your agent is. The instance is the live, running agent.

```python
class MyAgent(Agent):
    model = Model.mock()
    system_prompt = "You are helpful."
    budget = Budget(max_cost=1.00, exceed_policy=ExceedPolicy.WARN)

from syrin.enums import ExceedPolicy
from syrin import Budget

# Each instance is independent
agent1 = MyAgent()
agent2 = MyAgent()

agent1.run("Hello!")
agent2.run("Hi there!")

# Budgets are separate
print(f"Agent 1 spent: ${agent1.budget_state.spent:.6f}")
print(f"Agent 2 spent: ${agent2.budget_state.spent:.6f}")
```

They do not share state. Each instance has its own conversation history, its own budget counter, and its own memory (if memory is in-memory backend). For shared state across instances, use [Swarm](/agent-kit/multi-agent/swarm).

## Inheritance

Agent classes follow standard Python inheritance. Child classes inherit all parent class attributes and can override any of them:

```python
class BaseAgent(Agent):
    model = Model.mock()
    budget = Budget(max_cost=5.00, exceed_policy=ExceedPolicy.WARN)
    tools = [get_weather]  # All children inherit this tool

class SpecializedAgent(BaseAgent):
    system_prompt = "You specialize in weather reports."  # Overrides nothing from Base

class ReportingAgent(BaseAgent):
    system_prompt = "You write detailed weather reports."
    # Inherits model, budget, and tools from BaseAgent
```

Tools from parent classes are merged, not replaced. If `BaseAgent` has `[tool_a]` and `ChildAgent` has `[tool_b]`, the child has `[tool_a, tool_b]`. To remove a parent tool, define a `tools` list explicitly on the child.

## What Makes an Agent Different From a Plain API Call

A plain LLM API call gives you text back. That is all.

A Syrin agent gives you:
- Cost tracking down to the fractional cent, automatically
- Conversation history that persists across multiple `run()` calls
- A budget that enforces your spending limit without any extra code
- Memory that the agent can draw on across sessions
- Tools it can call with structured, validated arguments
- Events you can subscribe to for logging, alerting, and debugging
- Guardrails that check inputs and outputs automatically
- The ability to spawn child agents, hand off to specialists, or join a swarm

None of these require you to write the plumbing. They are on by default, off when you do not configure them.

## What's Next

- [Creating Agents](/agent-kit/agent/creating-agents) — The class pattern, the builder pattern, and when to use each
- [Running Agents](/agent-kit/agent/running-agents) — `run()`, `arun()`, `stream()`, and what to do with the response
- [Tools](/agent-kit/agent/tools) — Give your agent real-world abilities
- [Memory](/agent-kit/core/memory) — Four memory types, backends, and decay
- [Budget](/agent-kit/core/budget) — Cost control with thresholds and rate limits
