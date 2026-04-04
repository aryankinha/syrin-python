---
title: Class-Based Agent Configuration
description: How to configure agents with class attributes, inheritance, and constructor overrides
weight: 63
---

## Configuration via Class Attributes

All agent configuration lives in the class body as plain Python attributes. This makes agents self-documenting and refactorable with standard tooling.

```python
from syrin import Agent, Budget, Model
from syrin.enums import ExceedPolicy
from syrin.tool import tool

@tool
def search(query: str) -> str:
    """Search the web."""
    return f"Results for: {query}"

class ResearchAgent(Agent):
    name = "research-agent"
    description = "Researches topics thoroughly"
    model = Model.OpenAI("gpt-4o")
    system_prompt = """
        You are a thorough research assistant.
        Use tools when you need current information.
        Cite sources and be precise.
    """
    tools = [search]
    budget = Budget(max_cost=1.00, exceed_policy=ExceedPolicy.WARN)
```

## Dynamic Configuration with Constructor Overrides

Every class attribute can be overridden at instantiation. Use this when you need runtime variation — different models for different environments, different budgets per user, etc.

```python
# Different model at test time
test_agent = ResearchAgent(model=Model.mock())

# Different budget for a premium user
premium_agent = ResearchAgent(budget=Budget(max_cost=10.00))
```

## Building Agents Dynamically

If you need to build agents from config dicts or loop-generated settings, use the constructor:

```python
def make_agent(config: dict) -> ResearchAgent:
    return ResearchAgent(
        model=Model.OpenAI(config["model"]),
        budget=Budget(max_cost=config.get("budget", 1.00)),
    )
```

Or build a thin factory function that returns your class:

```python
def make_agents(roles: list[dict]) -> list[Agent]:
    agents = []
    for role in roles:
        class _Agent(Agent):
            model = Model.OpenAI("gpt-4o")
            system_prompt = role["prompt"]
            budget = Budget(max_cost=role.get("budget", 0.50))
        agents.append(_Agent())
    return agents
```

## Inheritance for Agent Families

Define a base class with shared config, then specialize with subclasses:

```python
from syrin import Agent, Model, Budget
from syrin.enums import ExceedPolicy
from syrin.tool import tool

@tool
def web_search(query: str) -> str:
    """Search across company data."""
    return f"Results: {query}"

@tool
def run_code(code: str) -> str:
    """Execute Python code."""
    return f"Executed: {code[:30]}"

class CompanyAgent(Agent):
    model = Model.OpenAI("gpt-4o")
    budget = Budget(max_cost=0.50, exceed_policy=ExceedPolicy.WARN)

class Researcher(CompanyAgent):
    system_prompt = "You are a thorough research specialist."
    tools = [web_search]

class Engineer(CompanyAgent):
    system_prompt = "You are a software engineer."
    tools = [run_code]
```

Both agents share `model` and `budget`. Change `CompanyAgent.model` and every subclass updates automatically.

### Tool Inheritance

Tools **merge** across the inheritance chain — all other attributes follow "most specific class wins":

```python
class BaseResearcher(Agent):
    model = Model.mock()
    tools = [web_search]

class AdvancedResearcher(BaseResearcher):
    tools = [run_code]  # Added, not replaced

researcher = AdvancedResearcher()
# researcher has both run_code AND web_search
```

Guardrails follow the same merge behavior.

## Choosing a Pattern

Use the **class pattern** when:
- You will create more than one instance
- You want inheritance and shared configuration
- You are writing production code
- You want IDE autocomplete and type checking

Use the **constructor pattern** (inline `Agent(model=..., ...)`) when:
- You need a single, one-off agent in a script
- You are constructing agents dynamically from config at runtime

## What's Next

- [Running Agents](/agent-kit/agent/running-agents) — `run()`, `arun()`, streaming, and the Response object
- [Tools](/agent-kit/agent/tools) — Give your agents capabilities
- [Budget](/agent-kit/core/budget) — Control what your agents spend
- [Memory](/agent-kit/core/memory) — Make your agents remember things
