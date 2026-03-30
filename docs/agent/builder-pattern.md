---
title: Builder Pattern
description: Fluent agent construction with the Agent builder API
weight: 63
---

## When Configuration Gets Serious

You know the feeling. Your agent constructor is 47 parameters long, and you're scrolling back and forth trying to find where `with_budget` was in relation to `with_tools`. The builder pattern solves this by letting you chain configuration calls in a readable order.

## Why Builders Exist

Compare these two approaches:

**The Constructor Sprawl:**
```python
agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    system_prompt="You are helpful.",
    tools=[search, calculate],
    budget=Budget(max_cost=1.00),
    memory=MemoryPreset.STANDARD,
    context=Context(max_tokens=80000),
    guardrails=[pii_guardrail],
    loop_strategy=LoopStrategy.REACT,
    debug=True,
)
```

**The Builder Flow:**
```python
agent = (
    Agent.builder(Model.OpenAI("gpt-4o"))
    .with_system_prompt("You are helpful.")
    .with_tools([search, calculate])
    .with_budget(Budget(max_cost=1.00))
    .with_memory()
    .with_context(Context(max_tokens=80000))
    .with_guardrails([pii_guardrail])
    .with_loop_strategy(LoopStrategy.REACT)
    .with_debug()
    .build()
)
```

Same configuration. The builder reads like a recipe: "Take a model, add a prompt, mix in tools..."

## When to Use the Builder

**Use builder when:**
- Agent has 3+ configuration options
- You prefer fluent APIs
- Building agents dynamically (from config files, databases)
- Creating agents in loops
- Configuration needs to be conditional

**Use class-based when:**
- Agent will be reused many times
- You want inheritance
- Code should be self-documenting
- You need IDE autocompletion of class attributes

## Basic Builder Usage

```python
from syrin import Agent, Model

agent = (
    Agent.builder(Model.OpenAI("gpt-4o", api_key="your-api-key"))
    .with_system_prompt("You are a helpful assistant.")
    .build()
)

response = agent.run("Hello!")
```

## Complete Builder Example

```python
from syrin import Agent, Model, Budget, Context
from syrin.tool import tool
from syrin.memory import Memory
from syrin.enums import ExceedPolicy, LoopStrategy

@tool
def search(query: str) -> str:
    """Search the web."""
    return f"Results for: {query}"

# Build a research agent step by step
research_agent = (
    Agent.builder(Model.OpenAI("gpt-4o", api_key="your-api-key"))
    .with_system_prompt("""
        You are a thorough research assistant.
        Use tools when you need current information.
        Cite sources and be precise.
    """)
    .with_tools([search])
    .with_budget(Budget(max_cost=1.00, exceed_policy=ExceedPolicy.STOP))
    .with_memory(Memory())  # Enable default memory
    .with_context(Context(max_tokens=80000))
    .with_loop_strategy(LoopStrategy.REACT)
    .with_debug()
    .build()
)

response = research_agent.run("Research quantum computing")
```

## Builder Methods Reference

### Core Configuration

```python
Agent.builder(model)
    .with_system_prompt("Your instructions here")
    .with_template_variables({"user_name": "Alice"})
    .with_tools([tool1, tool2])
    .build()
```

### Cost and Memory

```python
Agent.builder(model)
    .with_budget(Budget(max_cost=0.50))
    .with_budget_store(FileBudgetStore(), key="user-123")
    .with_memory(MemoryPreset.STANDARD)
    .build()
```

### Advanced Options

```python
Agent.builder(model)
    .with_context(Context(max_tokens=80000))
    .with_guardrails([my_guardrail])
    .with_loop_strategy(LoopStrategy.REACT)
    .with_rate_limit(APIRateLimit(rpm=60))
    .with_checkpoint(CheckpointConfig(storage="memory"))
    .build()
```

### Debugging and Observability

```python
Agent.builder(model)
    .with_debug()                    # Print events to console
    .with_tracer(my_tracer)         # Custom tracing
    .with_event_bus(my_event_bus)    # Domain events
    .build()
```

## Dynamic Agent Construction

This is where builders shine. Build agents from config:

```python
from syrin import Agent, Model, Budget
import json

# Simulate config from a file or API
config = {
    "model": "gpt-4o",
    "system_prompt": "You are a customer support agent.",
    "budget": {"max_cost": 0.50},
    "tools": ["search", "lookup_order"]
}

# Build agent dynamically
def build_agent_from_config(config: dict) -> Agent:
    builder = Agent.builder(
        Model.OpenAI(config["model"], api_key="your-api-key")
    )
    
    if "system_prompt" in config:
        builder = builder.with_system_prompt(config["system_prompt"])
    
    if "budget" in config:
        budget_config = config["budget"]
        budget = Budget(
            max_cost=budget_config.get("max_cost"),
            rate_limits=budget_config.get("rate_limits")
        )
        builder = builder.with_budget(budget)
    
    return builder.build()

agent = build_agent_from_config(config)
```

## Conditional Configuration

Build agents with conditional logic:

```python
def create_agent(role: str, premium: bool) -> Agent:
    builder = Agent.builder(Model.OpenAI("gpt-4o", api_key="your-api-key"))
    
    # Role-based system prompt
    prompts = {
        "support": "You are a helpful support agent.",
        "sales": "You are a friendly sales assistant.",
        "technical": "You are a technical support specialist.",
    }
    builder = builder.with_system_prompt(prompts.get(role, "You are helpful."))
    
    # Premium users get more budget
    if premium:
        builder = builder.with_budget(Budget(max_cost=5.00))
    else:
        builder = builder.with_budget(Budget(max_cost=0.50))
    
    # Premium users get memory
    if premium:
        from syrin.memory import Memory
        builder = builder.with_memory(Memory())
    
    return builder.build()

# Different agents for different users
basic_agent = create_agent("support", premium=False)
premium_agent = create_agent("support", premium=True)
```

## Builder in a Loop

Create multiple agents with variations:

```python
roles = [
    {"name": "researcher", "prompt": "You research topics thoroughly."},
    {"name": "writer", "prompt": "You write clear, engaging content."},
    {"name": "coder", "prompt": "You write clean, efficient code."},
]

agents = {}
for role in roles:
    agents[role["name"]] = (
        Agent.builder(Model.OpenAI("gpt-4o", api_key="your-api-key"))
        .with_system_prompt(role["prompt"])
        .with_budget(Budget(max_cost=0.25))
        .build()
    )

# Use each agent
research = agents["researcher"].run("Explain quantum computing")
content = agents["writer"].run("Write about AI ethics")
code = agents["coder"].run("Implement a binary search")
```

## Builder vs Class: The Trade-offs

| Aspect | Builder | Class |
|--------|---------|-------|
| **Readability** | Fluent, readable | May get long |
| **Reusability** | Creates instances | Can subclass |
| **Inheritance** | No | Yes |
| **Dynamic config** | Easy | Possible but awkward |
| **IDE support** | Method chaining | Attribute access |
| **Self-documenting** | Less | More (defaults visible) |

## Common Patterns

### Minimal Builder
```python
agent = Agent.builder(Model.OpenAI("gpt-4o")).build()
```

### Full-Featured Builder
```python
agent = (
    Agent.builder(Model.OpenAI("gpt-4o"))
    .with_system_prompt("You are helpful.")
    .with_tools([search, calculate])
    .with_budget(Budget(max_cost=1.00))
    .with_memory(MemoryPreset.STANDARD)
    .with_context(Context(max_tokens=80000))
    .with_guardrails([safety_rail])
    .with_debug()
    .build()
)
```

### Environment-Based Builder
```python
import os

model = os.getenv("MODEL", "gpt-4o-mini")
api_key = os.getenv("OPENAI_API_KEY")

agent = (
    Agent.builder(Model.OpenAI(model, api_key=api_key))
    .with_system_prompt(os.getenv("SYSTEM_PROMPT", "You are helpful."))
    .with_budget(Budget(max_cost=float(os.getenv("BUDGET", "0.50"))))
    .build()
)
```

## Reusing Builder Configurations

You can create a "builder factory" for common patterns:

```python
class AgentFactory:
    @staticmethod
    def research(model: Model) -> AgentBuilder:
        return (
            Agent.builder(model)
            .with_system_prompt("You are a thorough researcher.")
            .with_loop_strategy(LoopStrategy.REACT)
            .with_budget(Budget(max_cost=1.00))
        )
    
    @staticmethod
    def assistant(model: Model) -> AgentBuilder:
        return (
            Agent.builder(model)
            .with_system_prompt("You are a helpful assistant.")
            .with_budget(Budget(max_cost=0.10))
        )

# Create research agent
researcher = AgentFactory.research(
    Model.OpenAI("gpt-4o", api_key="your-key")
).with_tools([search]).build()

# Create assistant
helper = AgentFactory.assistant(
    Model.OpenAI("gpt-4o-mini", api_key="your-key")
).build()
```

## Troubleshooting

**"Agent has no attribute 'build'"**
```python
# Wrong: missing parentheses
agent = Agent.builder(model).build  # Missing ()

# Right:
agent = Agent.builder(model).build()
```

**"Builder doesn't have 'with_something'"**
Check the builder methods list. Only documented methods are available.

**"TypeError: argument should be..."**
Pass the correct type. e.g., `with_budget(Budget(...))` not `with_budget(...)`.

## What's Next?

- [Running Agents](/agent-kit/agent/running-agents) - Execute your built agent
- [Tools](/agent-kit/agent/tools) - Add abilities to your agent
- [Memory](/agent-kit/core/memory) - Persistent memory
- [Budget](/agent-kit/core/budget) - Cost control

## See Also

- [Creating Agents](/agent-kit/agent/creating-agents) - Class-based approach
- [Agent Anatomy](/agent-kit/agent/anatomy) - Component reference
- [Response Object](/agent-kit/agent/response-object) - What you get back
- [Loop Strategies](/agent-kit/agent/running-agents) - Thinking behavior
