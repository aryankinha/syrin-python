---
title: Pipeline
description: Run multiple agents in sequence, passing output from one to the next
weight: 92
---

## When One Agent Isn't Enough

Your task has a natural flow. Research first, then analyze, then write. A single agent trying to do everything does each step okay—but never great.

You could chain prompts manually:

```python
# The manual approach - tedious and error-prone
researcher = Researcher()
analyst = Analyst()
writer = Writer()

research = researcher.run(f"Research: {topic}")
analysis = analyst.run(f"Analyze: {research}")
final = writer.run(f"Write: {analysis}")
```

This works. But now you have three agents with three budgets, no shared context, no observability, and no way to add a fourth step without more manual wiring.

Pipelines solve this. One declaration, one shared budget, full visibility.

## The Pipeline Pattern

A pipeline runs agents **in sequence**. Each agent's output becomes context for the next. The pipeline manages the handoff, budgets, and observability for you.

```python
from syrin import Agent, Model, Pipeline

# Define specialized agents
class Researcher(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = "You research topics thoroughly. Cite your sources."

class Analyst(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = "You analyze data and identify key insights."

class Writer(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")  # Best model for final output
    system_prompt = "You write clear, engaging content."

# Create pipeline
pipeline = Pipeline()

# Run sequentially - each agent gets previous output
result = pipeline.run([
    (Researcher, f"Research {topic}"),
    (Analyst, f"Analyze the research findings"),
    (Writer, f"Write an article about the analysis"),
])

print(result.content)  # Writer's final output
```

**What just happened:**
1. Researcher runs first, produces research findings
2. Analyst receives those findings + its task, produces analysis
3. Writer receives the analysis + its task, produces final article
4. Pipeline returns Writer's output, but tracks all costs

The output from each agent is automatically prepended with "Previous context:" and passed to the next agent.

## Why Sequential?

Sequential execution matters when:

1. **Each step depends on the previous** — You can't analyze until you've researched
2. **Quality compounds** — A great writer needs great research
3. **Specialization saves money** — Smaller models for research, best model for final output
4. **Context must flow** — Each step builds on what came before

## Shared Budget Across All Agents

Every agent in the pipeline shares one budget. Spend accumulates across agents.

```python
from syrin import Budget

pipeline = Pipeline(
    budget=Budget(max_cost=1.00),  # $1 total for all agents
)

result = pipeline.run([
    (Researcher, "Research AI trends"),
    (Writer, "Write the article"),
])

# Combined cost from both agents
print(f"Total spent: ${result.cost:.4f}")

# Check remaining budget
print(f"Remaining: ${pipeline._budget.remaining:.4f}")
```

This is powerful. You set one budget limit, and all agents share it. The pipeline stops if any agent's cost would exceed the limit.

## The Fluent API

Pipeline uses a fluent builder pattern:

```python
# Default: sequential execution
result = pipeline.run([Agent1, Agent2, Agent3])

# Explicit sequential
result = pipeline.run([Agent1, Agent2, Agent3]).sequential()

# Parallel execution
results = pipeline.run([Agent1, Agent2, Agent3]).parallel()
```

The `run()` method returns a `PipelineBuilder`. By default it executes sequentially. Call `.parallel()` when agents can run independently.

## Real-World Example: Market Research Pipeline

Here's a production-grade pipeline for market research:

```python
from syrin import Agent, Model, Pipeline, Budget
from syrin.tool import tool

@tool
def search_web(query: str) -> str:
    """Search for current information online."""
    # Real implementation: call your search API
    return f"Search results for: {query}"

@tool
def fetch_financials(company: str) -> str:
    """Get financial data for a company."""
    # Real implementation: call financial data API
    return f"Financial data for {company}"

class IndustryResearcher(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = "You research industry trends and market dynamics."
    tools = [search_web]

class FinancialAnalyst(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = "You analyze financial data and identify risks."
    tools = [fetch_financials]

class CompetitorResearcher(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = "You research competitor landscape and positioning."
    tools = [search_web]

class ReportWriter(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")  # Best model for final output
    system_prompt = """
        You write executive-level market research reports.
        Structure: Executive Summary, Market Analysis, Competitive Landscape,
        Financial Insights, Recommendations.
    """

# Budget: $0.50 for research (divided among researchers), 
# $0.50 for final report
pipeline = Pipeline(
    budget=Budget(max_cost=1.00),
)

company = "Acme Corp"
result = pipeline.run([
    (IndustryResearcher, f"Research the {company} industry"),
    (FinancialAnalyst, f"Get and analyze {company} financials"),
    (CompetitorResearcher, f"Research {company} competitors"),
    (ReportWriter, f"Compile all research into an executive report on {company}"),
])

print(result.content)
```

**Why this structure works:**
- Each researcher uses a smaller model (cost savings)
- Report writer uses the best model (quality)
- All share the $1 budget
- Sequential ensures the writer has all research before writing

## Accessing Intermediate Results

Sometimes you need the output from every step, not just the final one:

```python
# Run each agent manually for access to intermediate results
pipeline = Pipeline()

researcher = Researcher()
analyst = Analyst()
writer = Writer()

# Run each step explicitly
research = researcher.run(f"Research: {topic}")
analysis = analyst.run(f"Analyze: {research.content}\n\nTask: {topic}")
final = writer.run(f"Write: {analysis.content}\n\nTask: {topic}")

# Now you have everything
print(f"Research: {research.content[:100]}...")
print(f"Analysis: {analysis.content[:100]}...")
print(f"Final: {final.content[:100]}...")
print(f"Total cost: ${research.cost + analysis.cost + final.cost:.4f}")
```

The declarative `pipeline.run()` is cleaner, but manual execution gives you access to every intermediate result.

## Pipeline Hooks for Observability

Every pipeline emits hooks for monitoring:

```python
from syrin.enums import Hook

pipeline = Pipeline()

# What runs when
pipeline.events.on(Hook.PIPELINE_START, lambda ctx: 
    print(f"Starting pipeline with {ctx['agents']} agents")
)

pipeline.events.on(Hook.PIPELINE_AGENT_START, lambda ctx:
    print(f"  Running {ctx['agent_type']}: {ctx['task'][:50]}...")
)

pipeline.events.on(Hook.PIPELINE_AGENT_COMPLETE, lambda ctx:
    print(f"    Completed {ctx['agent_type']} - Cost: ${ctx['cost']:.6f}")
)

pipeline.events.on(Hook.PIPELINE_END, lambda ctx:
    print(f"Pipeline complete - Total cost: ${ctx['total_cost']:.6f}")
)
```

**Sample output:**
```
Starting pipeline with 3 agents
  Running Researcher: Research AI trends in healthcare...
    Completed Researcher - Cost: $0.0023
  Running Analyst: Analyze the research findings...
    Completed Analyst - Cost: $0.0018
  Running Writer: Write an article about the analysis...
    Completed Writer - Cost: $0.0156
Pipeline complete - Total cost: $0.0197
```

## Serving Your Pipeline

Pipelines are servable—just like single agents:

```python
# Serve with HTTP API
pipeline.serve(port=8000, enable_playground=True)

# Or mount as a router in your FastAPI app
from fastapi import FastAPI

app = FastAPI()
router = pipeline.as_router()
app.include_router(router, prefix="/pipeline")
```

## Debug Mode

Enable debug output to see everything happening:

```python
pipeline = Pipeline(debug=True)

result = pipeline.run([
    (Researcher, "Research AI"),
    (Writer, "Write article"),
])
```

**Debug output shows:**
- Each agent starting and completing
- Tokens used per agent
- Costs accumulating
- Any errors that occur

## Traditional vs Fluent API

The fluent API (`pipeline.run(...).sequential()`) is cleaner, but traditional methods exist:

```python
# Fluent (recommended)
result = pipeline.run([A1, A2, A3]).sequential()
results = pipeline.run([A1, A2, A3]).parallel()

# Traditional
result = pipeline.run_sequential([A1, A2, A3])
results = pipeline.run_parallel([A1, A2, A3])

# Async versions
result = await pipeline.run_sequential_async([A1, A2, A3])
results = await pipeline.run_parallel_async([A1, A2, A3])
```

## When to Use Pipeline

| Use Case | Why Pipeline Works |
|----------|-------------------|
| Research → Analyze → Write | Each step builds on the previous |
| Extract → Transform → Load | Data flows through stages |
| Draft → Review → Edit | Quality improves with each pass |
| Gather → Summarize → Present | Data aggregation pipeline |

## What's Next?

- [Pipeline: Parallel](/multi-agent/pipeline-parallel) — Run agents simultaneously
- [Dynamic Pipeline](/multi-agent/dynamic-pipeline) — Let the LLM decide which agents to spawn
- [Handoff](/multi-agent/handoff) — Transfer control between agents mid-conversation

## See Also

- [Multi-Agent: Overview](/multi-agent/overview) — Introduction to multi-agent patterns
- [Multi-Agent: When to Use](/multi-agent/when-to-use) — Decision guide
- [Core Concepts: Budget](/core/budget) — Shared budget across agents
- [Agents: Handoff](/multi-agent/handoff) — Agent-to-agent transfer
