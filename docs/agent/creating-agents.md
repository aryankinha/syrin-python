---
title: Creating Agents
description: Class-based agents are the recommended pattern—here's everything you need to know
weight: 62
---

## The Recommended Pattern: Class-Based Agents

Syrin agents are Python classes. You define a class that inherits from `Agent`, set configuration as class attributes, and create instances. This is the canonical way to build agents — it gives you inheritance, reuse, testability, and clean multi-instance isolation.

## Pattern 1: Class-Based (Recommended)

This is the recommended pattern. You define a Python class that inherits from `Agent`, set configuration as class attributes, then create instances.

```python
from syrin import Agent, Model

class Assistant(Agent):
    model = Model.mock()
    system_prompt = "You are a helpful assistant."

agent = Assistant()
response = agent.run("Hello!")
print(response.content)
print(f"Cost: ${response.cost:.6f}")
```

Output:

```
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod...
Cost: $0.000042
```

That's the whole thing. Two attributes and you have a working agent.

### Why Classes?

The class pattern looks like more work but pays off immediately:

**Reusability.** Create ten instances from the same class. Each instance gets its own state (conversation history, budget counter) but shares the same configuration.

```python
agent_1 = Assistant()
agent_2 = Assistant()  # Same config, independent state
```

**Inheritance.** Build specialized agents from a shared base without repeating yourself.

**Testability.** Pass in a mock model without changing the class definition.

```python
test_agent = Assistant(model=Model.mock())  # Instance overrides class default
```

### Naming Your Agent

By default, your agent's name is the class name. You can customize it with `name` and `description` class attributes:

```python
from syrin import Agent, Model

class CustomerSupportAgent(Agent):
    name = "CustomerSupport"
    description = "Handles product and billing questions"
    model = Model.mock()
    system_prompt = "You are a friendly customer support agent."

agent = CustomerSupportAgent()
print(agent.name)         # "CustomerSupport"
print(agent.description)  # "Handles product and billing questions"
```

Output:

```
CustomerSupport
Handles product and billing questions
```

`name` and `description` are used in the serving playground, agent registries, and multi-agent topologies where agents identify themselves to each other.

### Dynamic System Prompts

Your system prompt can be a method instead of a string. This lets you inject runtime state — the user's name, the current date, external configuration — into the prompt without any string formatting at call time.

```python
from syrin import Agent, Model

class PersonalizedAgent(Agent):
    model = Model.mock()
    _user_name: str = "friend"

    def system_prompt(self) -> str:
        return f"You are a helpful assistant. The user's name is {self._user_name}. Always greet them by name."

agent = PersonalizedAgent()
agent._user_name = "Alice"
response = agent.run("Hello!")
print(response.content[:50])
```

Output:

```
Lorem ipsum dolor sit amet, consectetur adipiscing
```

(With a real model, it would greet Alice by name. The mock model returns lorem ipsum regardless, but the system prompt is correctly wired up.)

### Instance Overrides Class

Every class attribute can be overridden at instantiation. The class sets the default; the constructor overrides it. This is how you test with mock models without changing your production class:

```python
from syrin import Agent, Budget, Model
from syrin.enums import ExceedPolicy

class ProductionAgent(Agent):
    model = Model.mock()  # Would be Model.OpenAI in real code
    system_prompt = "You are a production assistant."
    budget = Budget(max_cost=5.00, exceed_policy=ExceedPolicy.WARN)

# Use defaults
prod = ProductionAgent()

# Override model for testing — no changes to the class needed
test = ProductionAgent(
    model=Model.mock(),
    budget=Budget(max_cost=0.01, exceed_policy=ExceedPolicy.WARN),
)
```

## Pattern 2: The Constructor Pattern

Pass everything directly to `Agent()`. Good for one-off scripts where you don't need a named type.

```python
from syrin import Agent, Model

agent = Agent(
    model=Model.mock(),
    system_prompt="You summarize text in one sentence.",
)

response = agent.run("The weather today is sunny with a high of 75 degrees.")
print(response.content[:60])
```

Output:

```
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed
```

**When to use:** Quick scripts, one-time tasks, ad-hoc experiments.

**When to avoid:** Anything you'll reuse, test, or put in a team codebase.

## Inheritance: Build a Family of Agents

This is the most powerful feature of the class pattern. Define a base agent with shared configuration, then create specialized agents that inherit from it.

```python
from syrin import Agent, Budget, Model, tool
from syrin.enums import ExceedPolicy

@tool
def web_search(query: str) -> str:
    """Search the web for current information."""
    return f"Results for: {query}"

@tool
def run_code(code: str) -> str:
    """Execute Python code and return the result."""
    return f"Code executed: {code[:30]}..."

# The shared base — every agent in this system gets this budget and model
class CompanyAgent(Agent):
    model = Model.mock()
    budget = Budget(max_cost=0.50, exceed_policy=ExceedPolicy.WARN)

# Researcher inherits model and budget, adds its own prompt and tools
class Researcher(CompanyAgent):
    system_prompt = "You are a thorough research specialist. Use web_search for current facts."
    tools = [web_search]

# Engineer inherits model and budget, gets different prompt and tools
class Engineer(CompanyAgent):
    system_prompt = "You are a software engineer. Use run_code to verify solutions."
    tools = [run_code]

researcher = Researcher()
engineer = Engineer()

r1 = researcher.run("Summarize today's AI news")
r2 = engineer.run("Write a function to reverse a string")
print(f"Researcher: {r1.content[:50]}")
print(f"Engineer: {r2.content[:50]}")
```

Output:

```
Researcher: Lorem ipsum dolor sit amet, consectetur adipiscing
Engineer: Lorem ipsum dolor sit amet, consectetur adipiscing
```

Both agents share the `model` and `budget` from `CompanyAgent`. If you change the model in `CompanyAgent`, all subclasses update automatically.

### How Tool Inheritance Works

Tools are the one attribute that **merges** instead of overrides. Every other attribute (model, system prompt, budget) follows "most specific class wins." Tools concatenate from parent to child:

```python
from syrin import Agent, Model
from syrin.tool import tool

@tool
def base_search(query: str) -> str:
    """Search across all company data."""
    return f"Base results: {query}"

@tool
def advanced_filter(results: str, min_date: str) -> str:
    """Filter results by date."""
    return f"Filtered: {results}"

class BaseResearcher(Agent):
    model = Model.mock()
    system_prompt = "You are a researcher."
    tools = [base_search]

class AdvancedResearcher(BaseResearcher):
    tools = [advanced_filter]

researcher = AdvancedResearcher()
tool_names = [t.name for t in researcher._tools]
print(f"Tools: {tool_names}")
```

Output:

```
Tools: ['advanced_filter', 'base_search']
```

The child's tools come first (they take priority in tool selection), followed by the parent's tools. This means `AdvancedResearcher` has access to both `advanced_filter` AND `base_search`.

**Guardrails** follow the same merge behavior — child guardrails run first, then parent guardrails.

## Choosing a Pattern

Use the **class pattern** when:
- You will create more than one instance
- You want to use inheritance
- You are writing production code
- You want IDE autocomplete and type checking

Use the **constructor pattern** when:
- You are writing a quick script
- You need the agent exactly once
- You are exploring the API

## What's Next

- [Running Agents](/agent-kit/agent/running-agents) — `run()`, `arun()`, streaming, and the Response object
- [Tools](/agent-kit/agent/tools) — Give your agents capabilities
- [Budget](/agent-kit/core/budget) — Control what your agents spend
- [Memory](/agent-kit/core/memory) — Make your agents remember things
