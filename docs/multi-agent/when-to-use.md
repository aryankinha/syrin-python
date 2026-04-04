---
title: When to Use Multi-Agent
description: A decision framework for when one agent is enough vs. when you need multiple
weight: 91
---

## Start with One Agent

Before you add a second agent, make sure you actually need one. A single agent with the right tools and a well-written system prompt can handle surprising complexity. Multi-agent systems are more expensive, harder to debug, and harder to test.

Ask yourself these questions first:

Could better tools solve this? If the agent needs to search the web, call an API, or run code, give it tools — not more agents.

Could a better system prompt solve this? A clear, specific prompt with examples often eliminates the need for orchestration.

Could memory solve this? If the agent forgets context across sessions, add `Memory()`. That's one agent, not two.

If none of these work, then you probably need multiple agents.

## When Multiple Agents Make Sense

### Different tasks need different expertise

Some work naturally divides into areas that benefit from specialized agents. Research requires different behavior than writing. Triage requires different behavior than billing support.

```python
from syrin import Agent, Model
from syrin.multi_agent import Pipeline

class Researcher(Agent):
    model = Model.mock()
    system_prompt = "You find and summarize information. Be factual, cite sources."

class Writer(Agent):
    model = Model.mock()
    system_prompt = "You write compelling content. Use the research as your foundation."

# Sequential: writer receives researcher's output
pipeline = Pipeline()
result = pipeline.run([
    (Researcher, "Find key facts about AI adoption in healthcare"),
    (Writer, "Write a 500-word article based on the research"),
])
```

The researcher and writer have genuinely different jobs. One is optimized for gathering; the other for crafting.

### Different tasks justify different models

Using GPT-4o for every step is expensive. Extraction and classification tasks work well on cheaper models. Use the expensive model only where quality matters most.

```python
from syrin import Agent, Model
from syrin.multi_agent import Pipeline

class ExtractorAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")  # Cheap + fast
    system_prompt = "Extract key data points from the text. Return JSON."

class SynthesizerAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")  # Best quality
    system_prompt = "Synthesize the extracted data into a strategic recommendation."

pipeline = Pipeline()
result = pipeline.run([
    (ExtractorAgent, "Extract from this earnings call transcript: ..."),
    (SynthesizerAgent, "Based on these data points, what should we do?"),
])
```

This costs roughly half as much as running both steps with GPT-4o, with most of the quality.

### Independent work can run in parallel

If multiple tasks don't depend on each other, run them at the same time.

```python
from syrin.multi_agent import parallel

class NewsAgent(Agent):
    model = Model.mock()
    system_prompt = "Summarize AI news."

class StockAgent(Agent):
    model = Model.mock()
    system_prompt = "Report on AI stock performance."

class ResearchAgent(Agent):
    model = Model.mock()
    system_prompt = "Find recent AI research papers."

# All three run simultaneously — wall time is max of the three, not their sum
result = parallel([NewsAgent(), StockAgent(), ResearchAgent()], goal="AI morning briefing")
```

### You need verification or consensus

For high-stakes outputs — content moderation, fact-checking, financial recommendations — multiple independent agents looking at the same thing gives you corroboration. If two out of three agents disagree, you know to escalate.

## When to Stick with One Agent

**Chat-like interactions.** A conversation flows naturally. There's no "pipeline" — just messages and responses.

**Low latency requirements.** Every agent adds overhead. If you need responses in under 200ms, fewer agents is better.

**Simple, contained tasks.** "Translate this" or "summarize this paragraph" doesn't improve with three agents. It just costs three times as much.

**Prototypes.** Start simple. Add complexity only when you've proven a single agent isn't enough.

## The Migration Path

Most successful multi-agent systems start as single agents and evolve:

**Stage 1: Single agent with tools.** This handles most use cases.

```python
class Assistant(Agent):
    model = Model.mock()
    system_prompt = "You are a technical support specialist."
    tools = [search, lookup, calculate]
```

**Stage 2: Better prompting + memory.** Before adding agents, optimize the single-agent setup.

```python
class Assistant(Agent):
    model = Model.mock()
    memory = Memory()
    system_prompt = """You are a senior technical support specialist with 10 years
    of experience. You have access to search and lookup tools. Always check the
    knowledge base before asking clarifying questions."""
```

**Stage 3: Multiple agents only when needed.** When you hit genuine limitations of the single-agent approach.

```python
class TriageAgent(Agent):
    system_prompt = "Classify the issue and route to the right specialist."

class BillingAgent(Agent):
    system_prompt = "Handle billing and subscription questions."

class TechAgent(Agent):
    system_prompt = "Handle technical debugging and configuration."
```

## Quick Decision Guide

If the task requires different expertise → use specialized agents.

If the task can use cheaper models for parts → use a pipeline with mixed models.

If subtasks are independent → use parallel execution.

If you need verification → use consensus topology.

If you need iterative improvement → use reflection topology.

If the task is a conversation → use one agent.

If you're prototyping → use one agent.

If latency matters most → use one agent.

## What's Next

- [Pipeline](/agent-kit/multi-agent/pipeline) — Sequential multi-agent execution
- [Swarm](/agent-kit/multi-agent/swarm) — Parallel, consensus, and reflection topologies
- [AgentRouter](/agent-kit/multi-agent/agent-router) — LLM-driven dynamic orchestration
