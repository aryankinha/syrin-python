---
title: Workflow
description: Declarative multi-step agent execution with sequential, parallel, and conditional steps
weight: 70
---

## Think of It as a Recipe

A `Workflow` is a recipe for agent execution. You write down the steps — "first plan, then research, then write" — and Syrin handles running each step, passing output from one to the next, and tracking the total cost across all of them.

The difference between a `Workflow` and a `Swarm` is philosophy. A Swarm is a group of agents that coordinates dynamically, often using an LLM to decide what to do next. A Workflow is a static recipe that you define upfront. You know exactly what runs, in what order, and under what conditions. That predictability makes workflows easier to test, debug, and reason about.

## The Simplest Workflow

Install the package and import `Workflow`:

```python
from syrin.workflow import Workflow
```

Then build the recipe:

```python
import asyncio
from syrin import Agent, Model, Budget
from syrin.workflow import Workflow

class PlannerAgent(Agent):
    model = Model.mock()
    system_prompt = "Create a research plan for the given topic."

class ResearchAgent(Agent):
    model = Model.mock()
    system_prompt = "Execute the research plan and gather key findings."

class SummarizerAgent(Agent):
    model = Model.mock()
    system_prompt = "Summarize the research findings in clear prose."

async def main():
    wf = (
        Workflow("research-pipeline", budget=Budget(max_cost=2.00))
        .step(PlannerAgent)
        .step(ResearchAgent)
        .step(SummarizerAgent)
    )
    result = await wf.run("AI trends in 2026")
    print(result.content[:60])
    print(f"Total cost: ${result.cost:.6f}")

asyncio.run(main())
```

Output:

```
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed
Total cost: $0.000054
```

Notice a few things. Workflows are `async` — `wf.run()` is a coroutine. The `result` is a `Response` object, exactly like what `agent.run()` returns. The `budget` is shared across all steps.

If you are in a non-async context (a script, a CLI, a test), use `run_sync()` instead:

```python
wf = Workflow("pipeline").step(ResearchAgent).step(WriterAgent)
result = wf.run_sync("renewable energy")
print(result.content)
```

`run_sync()` calls `asyncio.run()` internally. Do not call it from inside an existing event loop — use `await wf.run()` there.

## Step Types

### Sequential: `.step(AgentClass)`

The most common step type. The agent receives the previous step's output as its task, runs once, and passes its output to the next step.

```python
wf = (
    Workflow("pipeline")
    .step(PlannerAgent)                    # Receives the original input
    .step(ResearchAgent)                   # Receives PlannerAgent's output
    .step(SummarizerAgent)                 # Receives ResearchAgent's output
)
```

You can pin a step to a fixed task instead of receiving the previous output:

```python
wf = (
    Workflow("pipeline")
    .step(PlannerAgent, task="Create a 3-step research plan for the given topic")
    .step(ResearchAgent)
    .step(SummarizerAgent)
)
```

You can also give individual steps their own budget caps:

```python
wf = (
    Workflow("pipeline", budget=Budget(max_cost=5.00))
    .step(PlannerAgent)
    .step(ExpensiveResearcher, budget=Budget(max_cost=2.00))  # Capped at $2
    .step(SummarizerAgent)
)
```

### Parallel: `.parallel([A, B, C])`

Run multiple agents at the same time. All agents receive the same input (the previous step's output). Their outputs are joined together and passed to the next step.

```python
import asyncio
from syrin import Agent, Model
from syrin.workflow import Workflow

class RedditAgent(Agent):
    model = Model.mock()
    system_prompt = "Summarize Reddit discussions on the topic."

class ArxivAgent(Agent):
    model = Model.mock()
    system_prompt = "Summarize academic papers on the topic."

class WriterAgent(Agent):
    model = Model.mock()
    system_prompt = "Synthesize all the research into a coherent report."

async def main():
    wf = (
        Workflow("parallel-research")
        .parallel([RedditAgent, ArxivAgent])  # Run concurrently
        .step(WriterAgent)                    # Gets merged output from both
    )
    result = await wf.run("Large language model efficiency")
    print(f"Result: {result.content[:50]}")
    print(f"Cost: ${result.cost:.6f}")

asyncio.run(main())
```

Output:

```
Result: Lorem ipsum dolor sit amet, consectetur adipiscing
Cost: $0.000066
```

The parallel step uses `asyncio.gather` under the hood, so the wall time is roughly the duration of the slowest agent, not the sum of all agents.

### Conditional: `.branch(condition, if_true, if_false)`

Route execution to different agents based on the content of the previous step's output. The `condition` is a Python function that receives a `HandoffContext` and returns a boolean.

```python
import asyncio
from syrin import Agent, Model
from syrin.workflow import Workflow

class FastResponder(Agent):
    model = Model.mock()
    system_prompt = "Give a brief, direct answer. No preamble."

class DetailedResponder(Agent):
    model = Model.mock()
    system_prompt = "Give a thorough, detailed response with examples."

async def main():
    wf = (
        Workflow("smart-router")
        .branch(
            condition=lambda ctx: "urgent" in ctx.content.lower(),
            if_true=FastResponder,
            if_false=DetailedResponder,
        )
    )

    r1 = await wf.run("This is urgent! Quick summary of Python.")
    print(f"Urgent path: {r1.content[:40]}")

    r2 = await wf.run("Explain Python decorators in depth.")
    print(f"Normal path: {r2.content[:40]}")

asyncio.run(main())
```

Output:

```
Urgent path: Lorem ipsum dolor sit amet, consectetur
Normal path: Lorem ipsum dolor sit amet, consectetur
```

The `HandoffContext` object has these fields you can inspect in conditions:

- `ctx.content` — the output of the previous step (or the original input on the first step)
- `ctx.data` — structured output from the previous step, if it used `Output()`
- `ctx.history` — tuple of all previous step outputs in order
- `ctx.budget_remaining` — remaining budget in USD
- `ctx.step_index` — which step we're on (zero-based)
- `ctx.workflow_name` — the workflow's name
- `ctx.run_id` — unique identifier for this execution

## Nesting Workflows

Pass a `Workflow` instance to `.step()` to compose sub-workflows. The outer workflow treats the inner one like any other agent:

```python
import asyncio
from syrin import Agent, Model
from syrin.workflow import Workflow

class PlannerAgent(Agent):
    model = Model.mock()
    system_prompt = "Plan the work."

class ResearchAgent(Agent):
    model = Model.mock()
    system_prompt = "Research the topic."

class WriterAgent(Agent):
    model = Model.mock()
    system_prompt = "Write based on research."

class SummaryAgent(Agent):
    model = Model.mock()
    system_prompt = "Summarize everything."

async def main():
    # Inner workflow handles the research-and-write cycle
    inner = (
        Workflow("research-and-write")
        .step(ResearchAgent)
        .step(WriterAgent)
    )

    # Outer workflow coordinates the whole thing
    outer = (
        Workflow("full-pipeline")
        .step(PlannerAgent)
        .step(inner)        # Entire inner workflow runs as one step
        .step(SummaryAgent)
    )

    result = await outer.run("Python ecosystem overview")
    print(f"Result: {result.content[:50]}")
    print(f"Cost: ${result.cost:.6f}")

asyncio.run(main())
```

Output:

```
Result: Lorem ipsum dolor sit amet, consectetur adipiscing
Cost: $0.000053
```

## Lifecycle Events

Every workflow moment fires a hook. Subscribe to observe execution:

```python
import asyncio
from syrin import Agent, Model
from syrin.workflow import Workflow
from syrin.enums import Hook

class StepA(Agent):
    model = Model.mock()
    system_prompt = "Step A."

class StepB(Agent):
    model = Model.mock()
    system_prompt = "Step B."

async def main():
    events_log = []

    wf = Workflow("event-demo").step(StepA).step(StepB)

    wf.events.on(
        Hook.WORKFLOW_STARTED,
        lambda ctx: events_log.append(
            f"STARTED: {ctx['workflow_name']} ({ctx['step_count']} steps, budget=${ctx['budget_total']})"
        )
    )
    wf.events.on(
        Hook.WORKFLOW_STEP_END,
        lambda ctx: events_log.append(
            f"STEP_END: step {ctx['step_index']}"
        )
    )
    wf.events.on(
        Hook.WORKFLOW_COMPLETED,
        lambda ctx: events_log.append(
            f"COMPLETED: {ctx['steps_completed']} steps, total=${ctx['cost']:.6f}"
        )
    )

    await wf.run("Hello!")
    for e in events_log:
        print(e)

asyncio.run(main())
```

Output:

```
STARTED: event-demo (2 steps, budget=None)
STEP_END: step 0
STEP_END: step 1
COMPLETED: 2 steps, total=$0.000096
```

Context keys by hook:

`WORKFLOW_STARTED` fires when the workflow begins:
- `ctx['run_id']` — unique execution ID
- `ctx['workflow_name']` — the workflow name
- `ctx['input']` — the original input text
- `ctx['step_count']` — how many steps are defined
- `ctx['budget_total']` — the total budget (or `None` if no budget)

`WORKFLOW_STEP_END` fires after each step completes:
- `ctx['step_index']` — zero-based step number
- `ctx['step_type']` — e.g. `"SequentialStep"`, `"ParallelStep"`
- `ctx['cost']` — cost of this specific step

`WORKFLOW_COMPLETED` fires when all steps finish:
- `ctx['run_id']` — the execution ID
- `ctx['cost']` — total cost across all steps
- `ctx['steps_completed']` — how many steps ran

`WORKFLOW_FAILED` fires if an unhandled exception occurs:
- `ctx['error']` — the error message
- `ctx['cost']` — cost before the failure

## Serving a Workflow as an HTTP API

Like a single agent, a workflow can be served as an HTTP endpoint:

```python
wf.serve(port=8080)  # Starts a blocking HTTP server
```

This exposes `POST /chat` (run the workflow with `{"message": "..."}`) and `GET /graph` (returns the execution graph as a Mermaid string).

Requires `syrin[serve]`: `pip install "syrin[serve]"`.

## When to Use Workflow vs. Swarm vs. Pipeline

Use a **Workflow** when you know the steps upfront and want declarative, testable execution. It has conditional branching (`.branch()`), parallel steps (`.parallel()`), and nested composition, while staying completely predictable.

Use a **Swarm** when you need dynamic orchestration — an LLM decides what agents run next based on the conversation. Less predictable, more flexible.

Use a **Pipeline** when you need simple sequential execution with minimal ceremony. If you're just chaining a few agents one after another and don't need branching or parallel steps, `Pipeline` is lighter.

## What's Next

- [Swarm](/agent-kit/multi-agent/swarm) — Dynamic multi-agent coordination
- [Pipeline](/agent-kit/multi-agent/pipeline) — Simple sequential chaining
- [Budget Delegation](/agent-kit/multi-agent/budget-delegation) — Shared budgets across workflows
- [Hooks Reference](/agent-kit/debugging/hooks-reference) — Complete hook list
