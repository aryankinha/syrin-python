---
title: Pipeline: Parallel
description: Run multiple agents simultaneously for faster results
weight: 93
---

## Speed vs Quality

Sequential pipelines are great when each step depends on the previous. But what when steps are independent?

Consider gathering information:

```
Gather news → Gather stock prices → Gather weather → Gather sports
```

Each of these could run simultaneously. Why wait 4 seconds sequentially when you could wait 1 second in parallel?

Parallel execution lets agents work simultaneously, then combines their results.

## The Parallel Pattern

Parallel pipelines run agents **at the same time**. Each agent gets the same input (not each other's output), and results are collected at the end.

```python
from syrin import Agent, Model, Pipeline

class NewsGatherer(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = "You find the latest news on a topic."

class PriceChecker(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = "You look up current prices."

class WeatherReporter(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = "You provide weather updates."

# Create pipeline
pipeline = Pipeline()

# Run in parallel - all agents execute simultaneously
results = pipeline.run([
    (NewsGatherer, "AI and technology news"),
    (PriceChecker, "Tech stock prices"),
    (WeatherReporter, "Weather in San Francisco"),
]).parallel()

# results is a list of Response objects
for r in results:
    print(f"Agent: {r.model}")
    print(f"Content: {r.content[:100]}...")
    print(f"Cost: ${r.cost:.6f}")
    print("---")

# Total cost across all agents
total = sum(r.cost for r in results)
print(f"Total cost: ${total:.6f}")
```

**What just happened:**
1. All three agents started at the same time
2. Each worked independently on its task
3. Results were collected into a list
4. You got all responses, with costs for each

## When Parallel Makes Sense

Parallel execution is ideal when:

1. **Tasks are independent** — No agent needs another agent's output
2. **Speed matters** — You want results as fast as possible
3. **Gathering multiple sources** — Collecting data from different places
4. **Fan-out/Fan-in patterns** — One task spawning many parallel subtasks

## Parallel vs Sequential: The Trade-off

| Factor | Sequential | Parallel |
|--------|------------|----------|
| **Dependencies** | Required between steps | Not needed |
| **Speed** | Sum of all agent times | Time of slowest agent |
| **Cost visibility** | Combined total | Per-agent breakdown |
| **Use when** | Steps build on each other | Steps are independent |

**Example timing:**

```
Sequential: Agent1 (1s) + Agent2 (1s) + Agent3 (1s) = 3 seconds
Parallel: max(Agent1, Agent2, Agent3) = ~1 second
```

## Real-World Example: Due Diligence

When researching a potential acquisition, you need to gather information from multiple sources simultaneously:

```python
from syrin import Agent, Model, Pipeline, Budget
from syrin.tool import tool

@tool
def search_legal(query: str) -> str:
    """Search legal databases."""
    return f"Legal info: {query}"

@tool
def search_financial(query: str) -> str:
    """Search financial databases."""
    return f"Financial info: {query}"

@tool
def search_news(query: str) -> str:
    """Search news archives."""
    return f"News info: {query}"

@tool
def search_compliance(query: str) -> str:
    """Search compliance records."""
    return f"Compliance info: {query}"

class LegalResearcher(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = "You research legal matters and litigation history."
    tools = [search_legal]

class FinancialResearcher(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = "You analyze financial statements and metrics."
    tools = [search_financial]

class NewsResearcher(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = "You find news coverage and public statements."
    tools = [search_news]

class ComplianceResearcher(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = "You research regulatory compliance and violations."
    tools = [search_compliance]

class DueDiligenceWriter(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")
    system_prompt = """
        You write comprehensive due diligence reports.
        Cover: Legal status, Financial health, Public perception, Compliance history.
    """

# Parallel research phase
research_pipeline = Pipeline(budget=Budget(max_cost=0.50))

research_results = research_pipeline.run([
    (LegalResearcher, f"Research {target_company} legal history"),
    (FinancialResearcher, f"Analyze {target_company} financials"),
    (NewsResearcher, f"Find news on {target_company}"),
    (ComplianceResearcher, f"Check {target_company} compliance"),
]).parallel()

# Compile findings
all_findings = "\n\n".join(r.content for r in research_results)

# Final synthesis (sequential, depends on research)
final_pipeline = Pipeline(budget=Budget(max_cost=0.50))
report = final_pipeline.run([
    (DueDiligenceWriter, f"Write due diligence report:\n{all_findings}"),
]).sequential()

print(report.content)
```

**Why this structure:**
1. Four researchers run in parallel (4x faster than sequential)
2. Each uses a smaller model (cost-effective)
3. Results compile into one context for the writer
4. Writer uses best model for final output (quality)

## Fan-Out/Fan-In Pattern

A powerful pattern: one agent decides what to do, then multiple agents work in parallel, then results combine:

```python
from syrin import Agent, Model, Pipeline, Budget
from syrin.enums import Hook

class Orchestrator(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")
    system_prompt = """
        You break complex tasks into parallel subtasks.
        For the user's request, identify what can be researched simultaneously.
    """

class SubTask1(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = "You handle subtask 1."

class SubTask2(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = "You handle subtask 2."

class SubTask3(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = "You handle subtask 3."

class Synthesizer(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")
    system_prompt = "You combine multiple inputs into one coherent output."

# Phase 1: Orchestrate
orchestrator = Orchestrator()
plan = orchestrator.run(user_input)

# Phase 2: Parallel execution based on plan
pipeline = Pipeline()
parallel_results = pipeline.run([
    (SubTask1, f"Task from plan: {plan}"),
    (SubTask2, f"Task from plan: {plan}"),
    (SubTask3, f"Task from plan: {plan}"),
]).parallel()

# Phase 3: Synthesize
combined = "\n".join(r.content for r in parallel_results)
synthesizer = Synthesizer()
final = synthesizer.run(f"Combine these findings:\n{combined}")

print(final.content)
```

## Accessing Results by Agent

When you need to know which result came from which agent:

```python
results = pipeline.run([
    (NewsGatherer, "Technology news"),
    (PriceChecker, "Stock prices"),
]).parallel()

# Results are in order of agents
news_result = results[0]
price_result = results[1]

# Or iterate with agent names
for i, (agent, _) in enumerate([(NewsGatherer, "..."), (PriceChecker, "...")]):
    print(f"{agent.__name__}: {results[i].content}")
```

## Combining with Sequential

You can mix and match:

```python
pipeline = Pipeline()

# Parallel research, then sequential synthesis
result = pipeline.run([
    (Researcher1, "Research aspect 1"),
    (Researcher2, "Research aspect 2"),
    (Researcher3, "Research aspect 3"),
]).parallel()

# Compile parallel results
compiled = "\n\n".join(r.content for r in result)

# Continue with sequential
final_result = pipeline.run([
    (Analyzer, f"Analyze:\n{compiled}"),
    (Writer, "Write the final report"),
]).sequential()

print(final_result.content)
```

## Shared Budget in Parallel

The shared budget applies across all parallel agents:

```python
pipeline = Pipeline(budget=Budget(max_cost=0.50))

results = pipeline.run([
    (ExpensiveAgent1, "Task 1"),
    (ExpensiveAgent2, "Task 2"),
    (ExpensiveAgent3, "Task 3"),
]).parallel()

# Total spent across all three
print(f"Total: ${sum(r.cost for r in results):.4f}")
print(f"Remaining: ${pipeline._budget.remaining:.4f}")
```

If the total would exceed the budget, the pipeline stops before running the next agent.

## Performance Considerations

### What Parallel Helps With

- **I/O-bound tasks** — When agents are waiting for external APIs
- **Independent computation** — When agents don't need each other's results
- **Time-critical results** — When latency matters more than sequential quality
- **Gathering scenarios** — Collecting data from multiple sources

### What Parallel Doesn't Help

- **CPU-bound tasks** — LLMs are I/O-bound, not CPU-bound
- **Dependent steps** — When step B needs step A's output
- **Cost minimization** — Running in parallel vs sequential costs the same (but saves time)
- **Debugging complexity** — Parallel execution can be harder to trace

## Observability Hooks

Pipeline hooks work the same for parallel:

```python
pipeline = Pipeline()

pipeline.events.on(Hook.PIPELINE_START, lambda ctx:
    print(f"Starting parallel execution of {ctx['agents']} agents")
)

pipeline.events.on(Hook.PIPELINE_AGENT_COMPLETE, lambda ctx:
    print(f"  {ctx['agent_type']} done - ${ctx['cost']:.6f}")
)

pipeline.events.on(Hook.PIPELINE_END, lambda ctx:
    print(f"All done - Total: ${ctx['total_cost']:.6f}")
)

results = pipeline.run([A1, A2, A3]).parallel()
```

## When to Choose Parallel Over Sequential

Ask yourself:

1. **Does any agent need another agent's output?**
   - Yes → Sequential
   - No → Parallel

2. **Is speed important?**
   - Yes, and tasks are independent → Parallel
   - No → Sequential

3. **Are you gathering data from multiple sources?**
   - Yes → Parallel

4. **Do you need specific intermediate results?**
   - Yes → Sequential (for easier access to each step)
   - No → Either works

## What's Next?

- [Dynamic Pipeline](/agent-kit/multi-agent/dynamic-pipeline) — Let the LLM decide which agents to spawn
- [Pipeline](/agent-kit/multi-agent/pipeline) — Sequential execution (the complement)
- [Handoff](/agent-kit/multi-agent/handoff) — Transfer control between agents mid-conversation

## See Also

- [Multi-Agent: Overview](/agent-kit/multi-agent/overview) — Introduction to multi-agent patterns
- [Multi-Agent: When to Use](/agent-kit/multi-agent/when-to-use) — Decision guide
- [Core Concepts: Budget](/agent-kit/core/budget) — Shared budget across agents
- [Agents: Spawn](/agent-kit/multi-agent/handoff) — Dynamically spawn child agents
