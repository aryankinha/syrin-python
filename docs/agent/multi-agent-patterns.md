# Multi-Agent Patterns

Orchestrate multiple agents with pipelines, teams, and dynamic workflows.

## Pipeline

Run agents sequentially or in parallel with shared budget.

### Sequential

```python
from syrin import Pipeline
from syrin.budget import Budget

pipeline = Pipeline(budget=Budget(run=1.0))

result = pipeline.run([
    (ResearcherAgent, "Research quantum computing"),
    (WriterAgent, "Write a summary"),
]).sequential()

print(result.content)  # Output from WriterAgent
```

Each agent receives the previous agent’s output as context (except the first).

### Parallel

```python
results = pipeline.run([
    (ResearcherAgent, "Research topic A"),
    (ResearcherAgent, "Research topic B"),
]).parallel()

for r in results:
    print(r.content)
```

### Fluent API

```python
result = pipeline.run(agents).sequential()
results = pipeline.run(agents).parallel()
content = pipeline.run(agents).content
cost = pipeline.run(agents).cost
```

### Async

```python
result = await pipeline.run_sequential_async(agents)
results = await pipeline.run_parallel_async(agents)
```

---

## AgentTeam

Group agents that share budget and optionally memory.

```python
from syrin import AgentTeam

team = AgentTeam(
    agents=[researcher, writer, analyst],
    budget=Budget(run=1.0, shared=True),
    shared_memory=False,
    max_agents=10,
)

response = team.run_task("Research and write report")
response = team.run_task("Analyze data", agent=analyst)

agent = team.select_agent("research something")  # Keyword-based selection
```

### select_agent()

Picks an agent by task keywords (research, write, code, review). Can be overridden for LLM-based selection.

---

## DynamicPipeline

Let the LLM decide which agents to use and in what order.

```python
from syrin import DynamicPipeline

pipeline = DynamicPipeline(
    agents=[ResearcherAgent, AnalystAgent, WriterAgent],
    model=Model.OpenAI("gpt-4o-mini"),
    budget=Budget(run=1.0),
    max_parallel=5,
    debug=True,
)

result = pipeline.run("Research AI market and create a report", mode="parallel")
```

### Agent Names

- Use `_syrin_name = "research"` on the class for custom names.
- Default: lowercase class name (e.g. `ResearcherAgent` → `"researcheragent"`).

### Hooks

```python
pipeline.events.on(Hook.DYNAMIC_PIPELINE_START, lambda ctx: ...)
pipeline.events.on(Hook.DYNAMIC_PIPELINE_AGENT_SPAWN, lambda ctx: ...)
pipeline.events.on(Hook.DYNAMIC_PIPELINE_END, lambda ctx: ...)
```

---

## parallel() and sequential()

Low-level helpers for running agents:

```python
from syrin.agent.multi_agent import parallel, sequential

# Parallel
results = await parallel([
    (agent1, "Task 1"),
    (agent2, "Task 2"),
])

# Sequential
result = sequential(
    [(agent1, "Task 1"), (agent2, "Task 2")],
    pass_previous=True,
)
```

---

## See Also

- [Multi-Agent Use Case](../multi-agent.md)
- [Dynamic Pipeline](../dynamic-pipeline.md)
- [Handoff & Spawn](handoff-spawn.md)
