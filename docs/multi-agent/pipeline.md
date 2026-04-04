---
title: Pipeline
description: Run multiple agents in sequence or in parallel — each agent's output feeds the next
weight: 92
---

## What Is a Pipeline?

A pipeline is the simplest form of multi-agent coordination: agents run one after another. Each agent receives the previous agent's output as its input (or as additional context). The last agent's output becomes the final result.

Think of a content creation team: a researcher finds facts, a writer turns them into prose, an editor polishes the prose. Each step depends on the previous step's work. That is a pipeline.

## Sequential Pipeline

The `Pipeline` class runs agents in sequence:

```python
from syrin import Agent, Model, Pipeline

model = Model.mock()

class ResearchAgent(Agent):
    model = model
    system_prompt = "You research topics thoroughly."

class WriterAgent(Agent):
    model = model
    system_prompt = "You write clear, engaging summaries."

class EditorAgent(Agent):
    model = model
    system_prompt = "You edit and polish content."

pipeline = Pipeline()
result = pipeline.run([
    (ResearchAgent, "Research the history of Python programming language"),
    (WriterAgent, "Write a summary of Python's history"),
    (EditorAgent, "Polish and finalize the Python history article"),
])

print(f"Result: {result.content[:80]}")
print(f"Cost: ${result.cost:.6f}")
```

Output:

```
Result: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor i
Cost: $0.000062
```

Each step in the `run()` list is a tuple of `(AgentClass, task_description)`. The pipeline creates an instance of each class, runs it with the task, and passes the result forward to the next agent.

The `result` is the final agent's `Response` object: it has `content`, `cost`, `tokens`, and all the usual fields. The `cost` reflects the total cost of all agents in the pipeline combined.

## Parallel Utilities

Sometimes agents in a step do not depend on each other and can run at the same time. Syrin provides two utility functions:

```python
import asyncio
from syrin import Agent, Model
from syrin import parallel

model = Model.mock()

class ResearchAgent(Agent):
    model = model
    system_prompt = "You research topics."

class SummaryAgent(Agent):
    model = model
    system_prompt = "You summarize information."

async def main():
    results = await parallel([
        (ResearchAgent(), "Research quantum computing"),
        (SummaryAgent(), "Summarize AI trends"),
    ])
    print(f"Parallel results: {len(results)} responses")
    for r in results:
        print(f"  - {r.content[:50]}")

asyncio.run(main())
```

Output:

```
Parallel results: 2 responses
  - Lorem ipsum dolor sit amet, consectetur adipiscing
  - Lorem ipsum dolor sit amet, consectetur adipiscing
```

Note: `parallel()` takes **instances** (not classes), and requires `asyncio` because it runs agents concurrently. The return is a list of `Response` objects.

The `sequential()` utility does the same but with instance pairs, useful when you have agents already constructed:

```python
from syrin import sequential

result = sequential([
    (ResearchAgent(), "Research the topic"),
    (WriterAgent(), "Write about the topic"),
], pass_previous=True)
# pass_previous=True appends the previous output to each agent's input
```

## Pipeline With a Shared Budget

Add a budget to the pipeline to track total cost and enforce limits:

```python
from syrin import Agent, Budget, Model, Pipeline
from syrin.enums import ExceedPolicy

model = Model.mock()

class ResearchAgent(Agent):
    model = model
    system_prompt = "You research topics."

class WriterAgent(Agent):
    model = model
    system_prompt = "You write summaries."

pipeline = Pipeline(
    budget=Budget(max_cost=5.00, exceed_policy=ExceedPolicy.WARN)
)

result = pipeline.run([
    (ResearchAgent, "Research renewable energy"),
    (WriterAgent, "Write about renewable energy"),
])

print(f"Result: {result.content[:60]}")
print(f"Total cost: ${result.cost:.6f}")
```

The pipeline enforces the budget across all agents. If the accumulated cost hits the limit, the remaining agents are skipped.

## When to Use Pipeline vs. Swarm

Use **Pipeline** when:
- Each step genuinely depends on the previous step's output
- You want the simplest possible sequential workflow
- You do not need conditional logic or branching

Use **Swarm** (PARALLEL topology) when:
- Agents can work on the same goal independently
- Faster completion matters more than sequential dependency
- You need shared budget with per-agent limits

Use **Workflow** when:
- You need conditional logic ("if this, then route to agent A, else route to agent B")
- You need a mix of sequential and parallel steps
- You need a visualizable execution graph

## GitHub Examples

Full working examples with more patterns are in the GitHub repository:

- [`examples/07_multi_agent/pipeline.py`](https://github.com/syrin-labs/syrin-python/blob/main/examples/07_multi_agent/pipeline.py) — Basic pipeline with dynamic prompts
- [`examples/07_multi_agent/workflow_sequential.py`](https://github.com/syrin-labs/syrin-python/blob/main/examples/07_multi_agent/workflow_sequential.py) — Sequential workflow pattern
- [`examples/07_multi_agent/workflow_parallel.py`](https://github.com/syrin-labs/syrin-python/blob/main/examples/07_multi_agent/workflow_parallel.py) — Parallel within a workflow

## What's Next

- [Workflow](/agent-kit/multi-agent/workflow) — Conditional routing, parallel steps, visualization
- [Swarm](/agent-kit/multi-agent/swarm) — Shared goals, shared budgets, five topologies
- [Budget Delegation](/agent-kit/multi-agent/budget-delegation) — Cost control across multi-agent systems
