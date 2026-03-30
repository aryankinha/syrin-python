---
title: Tasks
description: Structured agent methods that feel like function calls
weight: 80
---

## Tasks: Your Agent's API

You've seen tools—they give your agent abilities. Tasks are different: they're structured methods *on* your agent that feel like API endpoints. Where tools are discovered dynamically by the LLM, tasks are explicit, named, and callable like regular Python methods.

## The Problem: Ambiguous Tool Discovery

With tools, the LLM decides when to call what. This is powerful but can be unpredictable:
- "Should I use search or browse?"
- "Is calculator even available?"
- Users can't easily invoke specific capabilities

Tasks solve this by giving you explicit method names.

## The Solution: @task Decorator

The `@task` decorator marks a method as a callable task:

```python
from syrin import Agent, Model
from syrin.task import task

class MyAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")
    system_prompt = "You are a helpful research assistant."
    
    @task
    def summarize(self, text: str) -> str:
        """Summarize the given text in one sentence."""
        return self.run(f"Summarize: {text}").content
    
    @task
    def translate(self, text: str, language: str = "English") -> str:
        """Translate text to the specified language."""
        return self.run(f"Translate to {language}: {text}").content
```

Now call them like regular methods:

```python
agent = MyAgent()

# Call tasks directly
summary = agent.summarize("Long article about AI...")
translation = agent.translate("Hello world", language="Spanish")
```

## Tasks vs Tools

| Aspect | Tasks | Tools |
|--------|-------|-------|
| **Discovery** | Explicit, named | Dynamic, LLM-decided |
| **Interface** | Python method | Tool schema |
| **Parameters** | Type hints | JSON schema |
| **Use case** | Structured operations | Dynamic tool use |
| **User access** | Direct API | Implicit via prompt |

**Use tasks when:**
- You need explicit, discoverable capabilities
- Users should be able to call specific functions
- You're building an API or service

**Use tools when:**
- The LLM should decide when to use capabilities
- Tools are supplementary to conversation
- You want open-ended exploration

## Task Parameters

Tasks use Python type hints just like regular methods:

```python
@task
def analyze_sentiment(self, text: str) -> str:
    """Analyze the sentiment of text."""
    return self.run(f"Analyze sentiment: {text}").content

@task
def extract_entities(self, text: str, entity_type: str = "person") -> str:
    """Extract entities of a specific type."""
    return self.run(f"Extract {entity_type} entities: {text}").content

@task
def batch_process(self, items: list[str]) -> list[str]:
    """Process a batch of items."""
    results = []
    for item in items:
        result = self.run(f"Process: {item}").content
        results.append(result)
    return results
```

## Complete Example: Research Assistant

```python
from syrin import Agent, Model
from syrin.task import task

class ResearchAssistant(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")
    system_prompt = "You are a helpful research assistant."
    
    @task
    def search_topic(self, query: str) -> str:
        """Search for information on a topic."""
        return self.run(f"Search and summarize: {query}").content
    
    @task
    def compare(self, topic_a: str, topic_b: str) -> str:
        """Compare two topics side by side."""
        return self.run(
            f"Compare and contrast {topic_a} vs {topic_b}"
        ).content
    
    @task
    def fact_check(self, claim: str) -> str:
        """Check if a claim is factual."""
        return self.run(f"Fact check: {claim}").content

# Use it
assistant = ResearchAssistant()

# Direct task calls
summary = assistant.search_topic("quantum computing")
comparison = assistant.compare("Python", "JavaScript")
verdict = assistant.fact_check("The earth is flat")
```

## Tasks with Tools

Tasks and tools work together:

```python
from syrin import Agent, Model, tool
from syrin.task import task

@tool
def web_search(query: str) -> str:
    """Search the web."""
    return f"Results for: {query}"

class ResearchAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")
    tools = [web_search]
    
    @task
    def deep_research(self, topic: str) -> str:
        """Perform deep research on a topic."""
        # This task uses the web_search tool internally
        return self.run(
            f"Research {topic} thoroughly and provide a detailed summary"
        ).content
```

## Observability: Task Tracking

Track task execution with hooks:

```python
from syrin import Hook

def on_agent_run_end(ctx: dict) -> None:
    task = ctx.get("task_name")
    if task:
        print(f"Task '{task}' completed")

agent.events.on(Hook.AGENT_RUN_END, on_agent_run_end)
```

## Task Metadata

The public task/types surface also includes `TaskSpec`, which is the metadata object attached to task-decorated methods and useful when you need to inspect or generate task contracts programmatically.

## What's Next?

- [Tools](/agent-kit/agent/tools) — Dynamic tool calling
- [Structured Output](/agent-kit/agent/structured-output) — Typed task responses
- [Loop Strategies](/agent-kit/agent/running-agents) — How tasks execute

## See Also

- [Running Agents](/agent-kit/agent/running-agents) — How to execute agents
- [Agent Anatomy](/agent-kit/agent/anatomy) — Components overview
- [Guardrails](/agent-kit/agent/guardrails) — Safety for tasks
