---
title: Agent Methods as Entry Points
description: Define named, typed operations on your agent — call them like Python functions
weight: 80
---

## Tools vs. Entry-Point Methods

Tools give the LLM capabilities it can choose to use. The LLM decides when to call a tool and with what arguments. That's great for open-ended reasoning.

But sometimes you want explicit, named operations that you call directly — like an API. "Summarize this text." "Translate this." "Compare these two things." You're not asking the LLM to decide; you're calling a specific function.

The answer is plain Python methods on your agent class.

## Defining Named Methods

Add methods to your Agent class that call `self.run()` internally:

```python
from syrin import Agent, Model

class ResearchAssistant(Agent):
    model = Model.mock()
    system_prompt = "You are a helpful research assistant."

    def summarize(self, text: str) -> str:
        """Summarize the given text in one sentence."""
        return self.run(f"Summarize this: {text}").content or ""

    def translate(self, text: str, language: str = "English") -> str:
        """Translate text to the specified language."""
        return self.run(f"Translate to {language}: {text}").content or ""

agent = ResearchAssistant()

summary = agent.summarize("Long article about AI and its implications...")
print(f"Summary: {summary[:50]}")

translation = agent.translate("Hello world", language="Spanish")
print(f"Translation: {translation[:50]}")
```

Output:

```
Summary: Lorem ipsum dolor sit amet, consectetur adipiscing
Translation: Lorem ipsum dolor sit amet, consectetur adipiscing
```

(With a real model, these would be actual summaries and translations.)

## Why Define Methods?

Methods are about the **caller's interface**, not the LLM's behavior. When you build an agent that will be used programmatically — as part of a workflow, or a larger system — you want explicit entry points.

Without named methods:

```python
# Callers have to know the right prompt to pass
result = agent.run("Summarize this: " + text)
```

With named methods:

```python
# Callers use a named, typed method
result = agent.summarize(text)
```

The second form is discoverable, type-checkable, and readable. IDEs can autocomplete it.

## Methods with Structured Output

Methods can return any Python type — dicts, Pydantic models, dataclasses:

```python
from syrin import Agent, Model

class AnalysisAgent(Agent):
    model = Model.mock()
    system_prompt = "You analyze text and data."

    def triage(self, item: str) -> dict:
        """Triage an item and return priority, category, summary."""
        response = self.run(
            f"Triage this item: {item}. "
            "Respond with: priority (high/medium/low), category, and summary."
        )
        content = response.content or ""
        return {
            "priority": "medium",
            "category": "general",
            "summary": content[:100],
        }

agent = AnalysisAgent()
result = agent.triage("Server CPU at 98% for the last 10 minutes")
for key, value in result.items():
    print(f"  {key}: {value}")
```

## Methods That Call Tools

A method can invoke the agent, and the agent can use its tools internally. The method is the external interface; tools are the internal machinery:

```python
from syrin import Agent, Model
from syrin.tool import tool

@tool
def web_search(query: str) -> str:
    """Search the web for information."""
    return f"Results for: {query}"

class ResearchAgent(Agent):
    model = Model.mock()
    system_prompt = "You research topics thoroughly using web search."
    tools = [web_search]

    def deep_research(self, topic: str) -> str:
        """Research a topic thoroughly and provide a summary."""
        return self.run(f"Research {topic} in depth").content or ""

agent = ResearchAgent()
result = agent.deep_research("large language model efficiency")
print(result[:50])
```

The LLM may call `web_search` internally — the method doesn't care. It just calls `self.run()` and returns the content.

## When Named Methods Make Sense

Use named methods when:
- You want named, discoverable entry points for your agent's capabilities
- You're building an agent that other code will call programmatically
- You want IDE autocomplete and type checking for callers
- The operation has a specific, repeatable purpose

Use plain `agent.run()` when:
- The user or system drives the conversation naturally
- You don't know in advance what the agent will be asked to do
- You want open-ended chat behavior

## What's Next

- [Tools](/agent-kit/agent/tools) — Give the agent capabilities that the LLM can call
- [Running Agents](/agent-kit/agent/running-agents) — How `run()`, `arun()`, and streaming work
- [Structured Output](/agent-kit/agent/structured-output) — Return typed Python objects from agents
