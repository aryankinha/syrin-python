---
title: Creating Agents
description: Four ways to build an agent—from minimalist to production-ready
weight: 62
---

## Four Paths to the Same Destination

You wouldn't use a sledgehammer for a finishing nail. Similarly, Syrin gives you four ways to create agents—from quick scripts to enterprise-grade systems. Choose based on your needs.

## The Four Patterns

| Pattern | Best For | Complexity |
|---------|----------|------------|
| **Direct Constructor** | One-off agents, scripts | Low |
| **Class-based** | Named agent types, reuse | Medium |
| **Builder** | Complex configs, fluent APIs | Medium |
| **Presets** | Quick prototypes | Low |

We'll cover each, starting with the simplest.

## 1. Direct Constructor (The Quick Script)

For one-off agents that don't need to be reused:

```python
from syrin import Agent, Model

# All config inline—perfect for scripts
agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    system_prompt="You are a helpful assistant.",
)

response = agent.run("Hello!")
print(response.content)
```

**When to use:** Scripts, one-off tasks, quick prototypes.

**When to avoid:** When you need to reuse the agent, share code, or test it.

### With Tools

```python
from syrin import Agent, Model
from syrin.tool import tool

@tool
def search(query: str) -> str:
    """Search the web."""
    return f"Found results for: {query}"

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    system_prompt="You are a research assistant.",
    tools=[search],
)

response = agent.run("What's the latest news in AI?")
```

## 2. Class-based (The Production Standard)

This is the **recommended approach** for anything you'll use more than once.

```python
from syrin import Agent, Model

class Assistant(Agent):
    # Set defaults on the class
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")
    system_prompt = "You are a helpful assistant. Be concise."
```

Then instantiate and use:

```python
# Create an instance
assistant = Assistant()

# Use it
response = assistant.run("What is Python?")
print(response.content)
```

### Why Classes?

Classes give you:

1. **Reusability** — Create multiple instances with same config
2. **Inheritance** — Build specialized agents from base classes
3. **Introspection** — Tools can inspect the agent class
4. **IDE support** — Autocomplete and type checking

### Complete Class Example

```python
from syrin import Agent, Model, Budget
from syrin.tool import tool
from syrin.memory import MemoryPreset
from syrin.enums import ExceedPolicy

@tool
def search(query: str) -> str:
    """Search the web for information."""
    return f"Web results for '{query}'"

@tool
def calculate(expression: str) -> str:
    """Evaluate a math expression."""
    return str(eval(expression))

class ResearchAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")
    
    system_prompt = """
        You are a thorough research assistant.
        Use tools when you need current information or calculations.
        Cite your sources and be precise.
    """
    
    tools = [search, calculate]
    
    budget = Budget(max_cost=1.00, exceed_policy=ExceedPolicy.STOP)

    memory = MemoryPreset.STANDARD

# Create instances
researcher = ResearchAgent()

# Use it
response = researcher.run("What is 15 * 23?")
print(response.content)
print(f"Cost: ${response.cost:.4f}")
```

### Inheritance: Building Specialized Agents

Here's where classes shine. Build a base agent, then specialize:

```python
from syrin import Agent, Model, Budget
from syrin.tool import tool
from syrin.enums import ExceedPolicy

# Base agent with shared config
class BaseAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")
    budget = Budget(max_cost=0.50, exceed_policy=ExceedPolicy.STOP)

# Specialized researcher
class Researcher(BaseAgent):
    system_prompt = "You are a research specialist. Be thorough."
    tools = []  # Add research tools here

# Specialized writer
class Writer(BaseAgent):
    system_prompt = "You are a creative writer. Be engaging."
    # Inherits budget limit from BaseAgent

# Specialized code assistant
class CodeAssistant(BaseAgent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")  # Override model
    system_prompt = "You are a coding expert. Write clean, efficient code."
    budget = Budget(max_cost=1.00, exceed_policy=ExceedPolicy.STOP)  # More budget for code
```

**What just happened:**
- `Researcher` inherits `model` and `budget` from `BaseAgent`
- `Writer` inherits everything, uses default system prompt
- `CodeAssistant` overrides both `model` (upgrade to gpt-4o) and `budget` (increase limit)

### Merge vs Override Behavior

| Attribute | Behavior | Description |
|-----------|----------|-------------|
| `model` | Override | First defined in inheritance wins |
| `system_prompt` | Override | First defined in inheritance wins |
| `budget` | Override | First defined in inheritance wins |
| `tools` | **Merge** | All tools concatenated |
| `guardrails` | **Merge** | All guardrails concatenated |

```python
class BaseAgent(Agent):
    tools = [search_tool]

class SpecializedAgent(BaseAgent):
    tools = [calculate_tool]  # Merges: [search_tool, calculate_tool]
```

### Constructor Override

Even with class defaults, you can override at instantiation:

```python
# Class defaults
class Assistant(Agent):
    model = Model.OpenAI("gpt-4o-mini")  # Default
    budget = Budget(max_cost=0.10)

# Override at instantiation
expensive_agent = Assistant(
    model=Model.OpenAI("gpt-4o"),  # Override class default
    budget=Budget(max_cost=1.00),  # Override class default
)
```

## 3. Builder Pattern (The Fluent Alternative)

For agents with many options, the builder scales cleanly:

```python
from syrin import Agent, Model, Budget
from syrin.tool import tool
from syrin.enums import ExceedPolicy

agent = (
    Agent.builder(Model.OpenAI("gpt-4o", api_key="your-api-key"))
    .with_system_prompt("You are a helpful assistant.")
    .with_tools([search, calculate])
    .with_budget(Budget(max_cost=0.50, exceed_policy=ExceedPolicy.STOP))
    .with_memory()  # Enable default memory
    .with_context(Context(max_tokens=80000))
    .with_debug(True)
    .build()
)
```

**When to use:**
- Complex configurations
- When you prefer method chaining
- Dynamic agent construction
- Building agents in loops or from config

**Equivalent class-based:**

```python
class MyAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")
    system_prompt = "You are a helpful assistant."
    tools = [search, calculate]
    budget = Budget(max_cost=0.50, exceed_policy=ExceedPolicy.STOP)
    memory = MemoryPreset.STANDARD
    context = Context(max_tokens=80000)

agent = MyAgent(debug=True)  # Note: debug is constructor-only
```

### Builder Methods

| Method | Description |
|--------|-------------|
| `with_system_prompt(str)` | Set instructions |
| `with_tools([...])` | Add tools |
| `with_budget(Budget)` | Set cost limits |
| `with_memory(Memory)` | Enable memory |
| `with_context(Context)` | Set context config |
| `with_guardrails([...])` | Add safety |
| `with_loop_strategy(LoopStrategy)` | Set thinking style |
| `with_debug(True)` | Enable debug output |
| `with_checkpoint(...)` | Enable state persistence |
| `build()` | Create the agent |

## 4. Presets (The Quick Start)

For common patterns, presets give you a running agent in one line:

```python
from syrin import Agent, Model

# Minimal agent (no memory, no budget)
agent = Agent.basic(Model.OpenAI("gpt-4o", api_key="your-api-key"))

# Agent with conversation memory
agent = Agent.with_memory(Model.OpenAI("gpt-4o", api_key="your-api-key"))

# Agent with cost control
agent = Agent.with_budget(Model.OpenAI("gpt-4o", api_key="your-api-key"))
```

**When to use:** Quick prototyping, when you just need *something* working fast.

**When to avoid:** Production code where you need specific configurations.

## Comparison: All Four Patterns

### Direct Constructor
```python
Agent(model=m, system_prompt="Hi", tools=[t])
```
✅ Quick, inline
❌ No reuse, hard to test

### Class-based
```python
class MyAgent(Agent):
    model = m
    system_prompt = "Hi"
    tools = [t]
```
✅ Reusable, inheritable, introspectable
❌ Slightly more code

### Builder
```python
Agent.builder(m).with_system_prompt("Hi").with_tools([t]).build()
```
✅ Fluent, readable for complex configs
❌ No class-level defaults

### Presets
```python
Agent.basic(m)
```
✅ Fastest to write
❌ Limited customization

## Adding Tools to Your Agent

Tools are how agents interact with the world:

```python
from syrin import Agent, Model
from syrin.tool import tool

@tool
def search(query: str) -> str:
    """Search the web for information.
    
    Args:
        query: The search query (e.g., "latest AI news")
    
    Returns:
        Search results as a string
    """
    # Real implementation would call search API
    return f"Results for '{query}'"

class ResearchAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")
    system_prompt = "Use the search tool when asked about current events."
    tools = [search]

agent = ResearchAgent()
response = agent.run("What's happening in tech today?")
# Agent decides to call search() internally
```

## Adding Memory

```python
from syrin import Agent, Model
from syrin.memory import Memory, MemoryPreset, MemoryType

class RememberingAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")
    memory = MemoryPreset.STANDARD

agent = RememberingAgent()

# Remember something
agent.remember("User's name is Alice", memory_type=MemoryType.CORE)

# Later conversations remember this
response = agent.run("What's my name?")
# Agent recalls and responds appropriately
```

## Complete Example: Research Assistant

```python
from syrin import Agent, Model, Budget
from syrin.tool import tool
from syrin.memory import MemoryPreset
from syrin.enums import ExceedPolicy

@tool
def search_web(query: str) -> str:
    """Search the web for current information."""
    return f"Web results for '{query}'"

@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression."""
    return str(eval(expression))

class ResearchAssistant(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")
    
    system_prompt = """
        You are a thorough research assistant.
        - Use tools when you need current information
        - Be precise and cite sources
        - Ask clarifying questions when needed
    """
    
    tools = [search_web, calculate]
    
    budget = Budget(max_cost=1.00, exceed_policy=ExceedPolicy.STOP)

    memory = MemoryPreset.STANDARD

# Create and use
assistant = ResearchAssistant()
response = assistant.run("Compare GPT-4 and Claude 2")
print(response.content)
```

## What's Next?

- [Builder Pattern](/agent/builder-pattern) - Fluent agent construction in depth
- [Running Agents](/agent/running-agents) - Execute your agent
- [Tools](/agent/tools) - Create powerful tools
- [Memory](/core/memory) - Persistent memory

## See Also

- [Agent Anatomy](/agent/anatomy) - Understanding each component
- [Response Object](/agent/response-object) - What you get back
- [Budget](/core/budget) - Cost control
- [Loop Strategies](/agent/running-agents) - Control thinking behavior
