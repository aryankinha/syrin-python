---
title: When to Use Multi-Agent
description: Should you use multiple agents? A decision guide
weight: 91
---

## The Question Everyone Asks

"Should I use one agent or multiple?"

The honest answer: it depends. But here's a framework to decide.

## Start with One Agent

Most tasks don't need multiple agents. A single well-prompted agent with the right tools can handle surprising complexity.

Before adding agents, ask:

1. Can one agent with better tools solve this?
2. Can one agent with better prompting solve this?
3. Can one agent with memory solve this?

If yes to any, start there. Complexity has a cost.

## Signs You Need Multiple Agents

### 1. Distinct Skill Sets Required

The task naturally divides into areas requiring different expertise:

| Task | Agents |
|------|--------|
| Research report | Searcher + Writer |
| Code review | Coder + Security expert |
| Customer support | Triage + Billing + Tech support |
| Data analysis | Collector + Analyzer + Visualizer |

```python
class Searcher(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = "You find relevant data online."

class Writer(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")
    system_prompt = "You write compelling content."

class Visualizer(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")
    system_prompt = "You create data visualizations."
```

### 2. Different Models Make Sense

Some tasks are simple. Others need the best model available. Using one expensive model for everything wastes money.

- **Simple extraction? Use gpt-4o-mini**
- **Creative writing? Use gpt-4o**
- **Complex reasoning? Use claude-3-5-sonnet**

```python
class CheapResearcher(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    # Fast, cheap for searching

class ExpensiveWriter(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")
    # Best quality for final output

pipeline = Pipeline(budget=Budget(max_cost=0.50))
pipeline.run([
    (CheapResearcher, "Find information on X"),
    (ExpensiveWriter, "Write the article"),
])
```

### 3. Tasks Must Happen in Order

Some workflows have dependencies. The output of step one feeds step two.

```
Analyze market → Research competitors → Write strategy → Create presentation
```

### 4. Parallelism Saves Time

Multiple independent tasks can run simultaneously:

```
Fetch news → Fetch stock prices → Fetch weather → Fetch sports
```

## Signs You Should Stick with One

### 1. Chat-like Interaction

Users ask questions, get answers. The conversation flows naturally without structured steps.

### 2. Low Latency Required

Every agent adds network hops and processing time. If responses need to be instant, fewer agents is better.

### 3. Simple Task Scope

"Translate this text" doesn't become better with three agents.

### 4. Tight Budget

Each agent costs money. Two agents doing one job is wasteful.

## Decision Checklist

Ask yourself:

| Question | Multi-Agent | Single Agent |
|----------|-------------|--------------|
| Do tasks require different expertise? | Yes | No |
| Do you need different model tiers? | Yes | No |
| Are tasks independent? | Parallel | One agent |
| Are tasks sequential? | Pipeline | One agent |
| Is response time critical? | Reconsider | Go for it |
| Is this a prototype? | Reconsider | Start simple |

## Migration Path

Start simple. Add complexity when needed:

**Phase 1: Single agent with tools**
```python
class Assistant(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")
    tools = [search, calculate, lookup]
```

**Phase 2: Single agent, better prompting**
```python
class Assistant(Agent):
    system_prompt = "You are a technical support specialist..."
```

**Phase 3: Multiple agents if needed**
```python
class TriageAgent(Agent): ...
class BillingAgent(Agent): ...
class TechAgent(Agent): ...
```

## Cost Comparison

| Setup | Example Cost |
|-------|-------------|
| Single gpt-4o | $0.01 per query |
| Single gpt-4o-mini | $0.0001 per query |
| Pipeline (mini + 4o) | $0.005 per query |
| Parallel (3x mini) | $0.0003 per query |

Budget-conscious systems can use smaller models for grunt work, saving the expensive model for final output.

## What's Next?

- [Pipeline](/agent-kit/multi-agent/pipeline) — Sequential execution
- [Pipeline: Parallel](/agent-kit/multi-agent/pipeline-parallel) — Simultaneous execution
- [Dynamic Pipeline](/agent-kit/multi-agent/dynamic-pipeline) — LLM decides

## See Also

- [Multi-Agent: Overview](/agent-kit/multi-agent/overview) — Introduction to multi-agent
- [Core Concepts: Budget](/agent-kit/core/budget) — Cost control
- [Agents: Handoff](/agent-kit/multi-agent/handoff) — Agent-to-agent transfer
