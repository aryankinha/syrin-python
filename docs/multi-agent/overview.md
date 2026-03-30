---
title: Multi-Agent Overview
description: Why and how to coordinate multiple AI agents to work together
weight: 90
---

## One Agent Can't Do Everything

Your customer support needs a technical expert, a refund specialist, and a billing analyst. Your research pipeline needs a searcher, an analyzer, and a writer. A single agent that does everything ends up doing everything mediocre.

Multi-agent systems solve this. Multiple specialized agents, each focused on what they do best, working together to solve complex problems.

## What Multi-Agent Means in Syrin

Syrin gives you three ways to coordinate agents:

1. **Pipeline** — Agents run in sequence, each passing results to the next
2. **Parallel** — Multiple agents work on different parts simultaneously
3. **Dynamic** — An LLM decides which agents to spawn and when

Each approach serves different needs. Let's see when to use which.

## The Patterns at a Glance

| Pattern | When to Use | Example |
|---------|-------------|---------|
| **Pipeline** | Fixed workflow, known steps | Research → Analyze → Write |
| **Parallel** | Independent tasks, speed matters | Gather data from multiple sources |
| **Dynamic** | Unknown requirements, LLM decides | Complex queries needing flexible approach |

## See It in Action

```python
from syrin import Agent, Model, Pipeline

class Researcher(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = "You find relevant information."

class Writer(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")
    system_prompt = "You write clear reports."

pipeline = Pipeline()

# Sequential: Researcher runs first, Writer gets the results
result = pipeline.run([
    (Researcher, "Research AI trends in healthcare"),
    (Writer, "Write a summary based on the research"),
])

print(result.content)  # Writer's final output
```

**What just happened:** The researcher gathered information, then passed it to the writer. The writer synthesized everything into a clean report.

## Shared Budget Across Agents

All agents in a pipeline share the same budget:

```python
from syrin import Budget

pipeline = Pipeline(
    budget=Budget(max_cost=1.00),  # Shared $1 budget for all agents
)

result = pipeline.run([
    (Researcher, "Research AI"),
    (Writer, "Write report"),
])

print(f"Total spent: ${result.cost:.4f}")  # Combined cost from both agents
```

## Agents That Talk to Each Other

Beyond pipelines, agents can hand off tasks mid-conversation:

```python
class TriageAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")
    system_prompt = "You route requests to the right specialist."

class BillingAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = "You handle billing questions."

triage = TriageAgent()

# Triage decides to hand off to Billing
result = triage.handoff(
    BillingAgent,
    "User asked about their invoice #12345"
)
```

## When It Makes Sense

Multi-agent shines when:

- **Tasks are fundamentally different** — Research vs. writing vs. coding
- **Specialization matters** — One model excels at search, another at creative writing
- **Workflows are predictable** — You know the steps, just need automation
- **Cost needs control** — Smaller models for simple tasks, larger for complex ones

## When to Stick with One Agent

Don't reach for multi-agent when:

- **Simple Q&A** — One agent handles it fine
- **Linear conversation** — The task flows naturally in one exchange
- **Low latency matters** — Multiple agents add overhead
- **You're prototyping** — Start simple, add complexity when needed

## What's Next?

- [When to Use Multi-Agent](/agent-kit/multi-agent/when-to-use) — Decision guide for your use case
- [Pipeline](/agent-kit/multi-agent/pipeline) — Sequential agent execution
- [Dynamic Pipeline](/agent-kit/multi-agent/dynamic-pipeline) — Let the LLM decide

## See Also

- [Agents: Overview](/agent-kit/agent/overview) — Single agent fundamentals
- [Agents: Handoff](/agent-kit/multi-agent/handoff) — Transfer control between agents
- [Core Concepts: Budget](/agent-kit/core/budget) — Cost control across agents
