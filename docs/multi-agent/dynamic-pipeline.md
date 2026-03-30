---
title: Dynamic Pipeline
description: Let the LLM decide which agents to spawn for each task
weight: 94
---

## The Problem with Static Pipelines

Regular pipelines work when you know the steps ahead of time:

```python
# You know the steps: research → analyze → write
pipeline.run([
    (Researcher, "Research topic"),
    (Analyzer, "Analyze findings"),
    (Writer, "Write report"),
])
```

But what when you don't know?

A user asks: *"Compare Python and Rust for building web APIs."*

What should happen? Maybe:
- Researcher gathers info on Python
- Researcher gathers info on Rust
- Analyst compares pros/cons
- Writer drafts the comparison

Or maybe just:
- Researcher gathers both
- Writer drafts the comparison

The point is: **you don't know what the user will ask**. A static pipeline locks you into a fixed sequence.

## The Solution: Let the LLM Decide

Dynamic pipelines let the LLM analyze the task and decide:

1. Which specialized agents are needed?
2. How many agents to spawn?
3. What should each agent do?
4. In what order?

```python
from syrin import Agent, Model
from syrin.agent.multi_agent import DynamicPipeline

# Define your specialized agents
class Researcher(Agent):
    _agent_name = "researcher"
    _agent_description = "Researches topics and gathers information"
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = "You research topics. Use for: finding facts, investigating questions."

class Analyst(Agent):
    _agent_name = "analyst"
    _agent_description = "Analyzes data and provides structured reasoning"
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = "You analyze data. Use for: comparing options, pros/cons, evaluation."

class Writer(Agent):
    _agent_name = "writer"
    _agent_description = "Writes clear, engaging content"
    model = Model.OpenAI("gpt-4o", api_key="your-key")  # Best model for writing
    system_prompt = "You write content. Use for: drafting text, creative writing."

# Create the dynamic pipeline
pipeline = DynamicPipeline(
    agents=[Researcher, Analyst, Writer],
    model=Model.OpenAI("gpt-4o-mini", api_key="your-key"),  # Orchestrator model
    max_parallel=5,
)

# Just give it a task - it figures out the rest
result = pipeline.run("Compare Python and Rust for web APIs")
print(result.content)
```

**What just happened:**
1. The orchestrator (a separate LLM call) analyzed the task
2. It decided which agents to spawn based on available agents and the task
3. It spawned the appropriate agents and ran them
4. Results were combined and returned

## How It Works

Under the hood, a dynamic pipeline does this:

```
1. User: "Compare Python and Rust for web APIs"

2. Orchestrator LLM thinks:
   "This needs research on both, then analysis, then writing.
    I'll spawn researcher (twice for each language), 
    analyst, and writer."

3. Orchestrator returns a plan:
   [
     {"type": "researcher", "task": "Research Python web frameworks"},
     {"type": "researcher", "task": "Research Rust web frameworks"},
     {"type": "analyst", "task": "Compare the research findings"},
     {"type": "writer", "task": "Write the comparison"}
   ]

4. Pipeline executes the plan
```

The orchestrator is a separate, lightweight LLM (like gpt-4o-mini) that plans which agents to use. The actual work is done by your specialized agents.

## Why This Matters

### Before: Rigid Workflows

```python
# You had to hardcode everything
pipeline.run([
    (Researcher, "Research Python"),
    (Researcher, "Research Rust"),
    (Analyzer, "Compare"),
    (Writer, "Write"),
])
```

This breaks when:
- User asks something simpler: "What is Rust?"
- User asks something complex: "Compare 5 programming languages"
- User asks something unexpected: "Should I learn Python or Rust?"

### After: Adaptive Workflows

```python
# Let the LLM decide
pipeline.run("What is Rust?")  # Maybe just researcher + writer
pipeline.run("Compare Python and Rust")  # Researcher, analyst, writer
pipeline.run("Compare 5 languages")  # Multiple researchers, one analyzer, writer
```

The same pipeline handles all cases intelligently.

## The Two-Step Process

A dynamic pipeline runs in two phases:

### Phase 1: Planning (Orchestrator)

The orchestrator LLM receives:
- The user's task
- Descriptions of available agents
- Maximum agents it can spawn

It returns a plan as JSON:

```json
[
  {"type": "researcher", "task": "Research Python web frameworks"},
  {"type": "researcher", "task": "Research Rust web frameworks"},
  {"type": "analyst", "task": "Compare Python vs Rust for web APIs"},
  {"type": "writer", "task": "Write a comparison report"}
]
```

### Phase 2: Execution (Pipeline)

The pipeline parses the plan and:
- Spawns the specified agents
- Passes tasks to each agent
- Collects results
- Combines everything

## Agent Naming

The orchestrator picks agents by name. You control names with `_agent_name`:

```python
class MyAgent(Agent):
    _agent_name = "researcher"  # This is how the orchestrator refers to it
    _agent_description = "Researches topics"  # Shown to orchestrator
    model = Model.OpenAI("gpt-4o-mini")
    system_prompt = "You research topics..."
```

If you don't set `_agent_name`, it defaults to the lowercase class name: `MyAgent` → `myagent`.

**Important:** The orchestrator uses `_agent_name` to match the plan's `type` field. Case doesn't matter ("researcher" matches "Researcher").

## Agent Descriptions

The `_agent_description` (or `system_prompt`) is shown to the orchestrator. Make it clear when to use each agent:

```python
class Researcher(Agent):
    _agent_name = "researcher"
    model = Model.OpenAI("gpt-4o-mini")
    system_prompt = """
        You research topics and gather information.
        Use for: finding facts, searching for data, investigating questions.
        Be thorough and cite sources.
    """
```

The orchestrator reads this to decide when to spawn the researcher.

## Modes: Parallel vs Sequential

### Parallel Mode (Default)

Agents run simultaneously:

```python
result = pipeline.run("Compare Python and Rust", mode="parallel")
```

**Best when:** Agents can work independently (gathering separate information).

**Timeline:**
```
Researcher1 ──┐
Researcher2 ──┼──→ Writer
Analyst ──────┘

Total time ≈ max(agents) + writer
```

### Sequential Mode

Agents run one after another, each getting previous output:

```python
result = pipeline.run("Compare Python and Rust", mode="sequential")
```

**Best when:** Each step depends on the previous (e.g., analysis needs research first).

**Timeline:**
```
Researcher1 → Researcher2 → Analyst → Writer

Total time ≈ sum(all agents)
```

## Shared Budget

All spawned agents share one budget:

```python
from syrin import Budget

pipeline = DynamicPipeline(
    agents=[Researcher, Analyst, Writer],
    model=Model.OpenAI("gpt-4o-mini"),
    budget=Budget(max_cost=2.00),  # $2 total for all agents + orchestrator
)

result = pipeline.run("Compare Python and Rust")

# Check what was spent
print(f"Total cost: ${result.cost:.4f}")
```

**Budget breakdown:**
- Orchestrator planning call: ~$0.001
- Spawned agents: varies by what was spawned
- Total capped at your budget limit

## Observability with Hooks

Every phase emits hooks for monitoring:

```python
from syrin.enums import Hook

pipeline = DynamicPipeline(
    agents=[Researcher, Analyst, Writer],
    model=Model.OpenAI("gpt-4o-mini"),
)

# Task received, planning starting
pipeline.events.on(Hook.DYNAMIC_PIPELINE_START, lambda ctx:
    print(f"Task: {ctx['task'][:50]}...")
)

# Plan generated
pipeline.events.on(Hook.DYNAMIC_PIPELINE_PLAN, lambda ctx:
    print(f"Plan: {ctx['plan_count']} agents will be spawned")
)

# Agent spawning
pipeline.events.on(Hook.DYNAMIC_PIPELINE_AGENT_SPAWN, lambda ctx:
    print(f"  → Spawning {ctx['agent_type']}: {ctx['task'][:40]}...")
)

# Agent completed
pipeline.events.on(Hook.DYNAMIC_PIPELINE_AGENT_COMPLETE, lambda ctx:
    print(f"    ✓ {ctx['agent_type']} done - Cost: ${ctx['cost']:.6f}")
)

# All done
pipeline.events.on(Hook.DYNAMIC_PIPELINE_END, lambda ctx:
    print(f"All done! Total: ${ctx['total_cost']:.4f}")
)

result = pipeline.run("Compare Python and Rust")
```

**Sample output:**
```
Task: Compare Python and Rust for web APIs...
Plan: 4 agents will be spawned
  → Spawning researcher: Research Python web frameworks...
    ✓ researcher done - Cost: $0.0023
  → Spawning researcher: Research Rust web frameworks...
    ✓ researcher done - Cost: $0.0021
  → Spawning analyst: Compare the findings...
    ✓ analyst done - Cost: $0.0018
  → Spawning writer: Write the comparison...
    ✓ writer done - Cost: $0.0156
All done! Total: $0.0268
```

## Hook Reference

| Hook | When | Key Fields |
|------|-------|------------|
| `DYNAMIC_PIPELINE_START` | Planning begins | `task`, `model`, `available_agents`, `budget_remaining` |
| `DYNAMIC_PIPELINE_PLAN` | Plan generated | `plan` (array), `plan_count` |
| `DYNAMIC_PIPELINE_EXECUTE` | Execution starts | `plan`, `mode` |
| `DYNAMIC_PIPELINE_AGENT_SPAWN` | Agent spawning | `agent_type`, `task`, `execution_mode` |
| `DYNAMIC_PIPELINE_AGENT_COMPLETE` | Agent finishes | `agent_type`, `cost`, `duration`, `result_preview` |
| `DYNAMIC_PIPELINE_END` | Pipeline done | `total_cost`, `duration`, `agents_spawned` |
| `DYNAMIC_PIPELINE_ERROR` | Something failed | `error`, `agents_spawned` |

## Debug Mode

Enable colored console output:

```python
pipeline = DynamicPipeline(
    agents=[Researcher, Analyst, Writer],
    model=Model.OpenAI("gpt-4o-mini"),
    debug=True,  # Prints all events with colors
)
```

**Debug output:**
```
▶ 14:32:01.123 dynamic.pipeline.start
     Task: Compare Python and Rust for web APIs
     Model: gpt-4o-mini

◉ 14:32:01.456 dynamic.pipeline.plan
     Plan: 4 agents

→ 14:32:01.500 dynamic.pipeline.agent.spawn
     Agent: researcher

✓ 14:32:02.123 dynamic.pipeline.agent.complete
     Cost: $0.0023

→ 14:32:02.200 dynamic.pipeline.agent.spawn
     Agent: researcher
     ...

✓ 14:32:03.456 dynamic.pipeline.end
     Total cost: $0.0268
```

## Output Formats

### Clean Mode (Default)

Concatenates agent outputs with double newlines:

```python
pipeline = DynamicPipeline(
    # ...
    output_format="clean",  # Default
)

result = pipeline.run("Compare Python and Rust")
# result.content = "Research on Python...\n\nResearch on Rust...\n\nAnalysis...\n\nFinal report..."
```

Best for API/chat responses.

### Verbose Mode

Includes headers and cost breakdown:

```python
pipeline = DynamicPipeline(
    # ...
    output_format="verbose",  # Debug-friendly
)

result = pipeline.run("Compare Python and Rust")
```

**Output:**
```
=== AGENT RESULTS ===

--- Agent 1 ---
[Research on Python frameworks]
Cost: $0.0023

--- Agent 2 ---
[Research on Rust frameworks]
Cost: $0.0021
...

=== TOTAL: 4 agents ===
Total cost: $0.0268
Total tokens: 1234
```

Best for debugging and understanding what happened.

## Real-World Example: Research Assistant

A complete example with 5 specialized agents:

```python
from syrin import Agent, Model, Budget
from syrin.agent.multi_agent import DynamicPipeline
from syrin.enums import Hook

class Researcher(Agent):
    _agent_name = "researcher"
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = """
        You research topics thoroughly.
        Use for: finding information, investigating questions, gathering data.
    """

class Analyst(Agent):
    _agent_name = "analyst"
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = """
        You analyze information and identify patterns.
        Use for: comparing options, evaluating data, structured reasoning.
    """

class Writer(Agent):
    _agent_name = "writer"
    model = Model.OpenAI("gpt-4o", api_key="your-key")  # Best model for writing
    system_prompt = """
        You write clear, engaging content.
        Use for: drafting reports, creative writing, formatting text.
    """

class FactChecker(Agent):
    _agent_name = "fact_checker"
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = """
        You verify claims and check accuracy.
        Use for: fact-checking, validating sources, catching errors.
    """

class Summarizer(Agent):
    _agent_name = "summarizer"
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = """
        You distill information to key points.
        Use for: executive summaries, condensing text, key takeaways.
    """

# Create pipeline with shared budget
pipeline = DynamicPipeline(
    agents=[Researcher, Analyst, Writer, FactChecker, Summarizer],
    model=Model.OpenAI("gpt-4o-mini", api_key="your-key"),
    budget=Budget(max_cost=1.00),  # $1 max for all work
    max_parallel=5,
)

# Attach hooks for monitoring
pipeline.events.on(Hook.DYNAMIC_PIPELINE_END, lambda ctx:
    print(f"Completed! Agents used: {ctx['agents_spawned']}")
)

# Handle errors
pipeline.events.on(Hook.DYNAMIC_PIPELINE_ERROR, lambda ctx:
    print(f"Error: {ctx['error']}")
)

# Run
result = pipeline.run("What are the key differences between REST and GraphQL APIs?")
print(result.content)
```

## When to Use Dynamic Pipeline

| Use Case | Dynamic Pipeline | Static Pipeline |
|----------|-----------------|----------------|
| Unknown task complexity | ✅ | ❌ |
| Varying agent combinations | ✅ | ❌ |
| Ad-hoc research | ✅ | ❌ |
| Known fixed workflow | ❌ | ✅ |
| Performance-critical (faster) | ❌ | ✅ |

**Use dynamic pipeline when:**
- Tasks vary significantly
- You want the LLM to optimize the workflow
- You're building research/analysis tools
- You can't predict user requests

**Use static pipeline when:**
- Workflow is always the same
- Performance matters (no planning overhead)
- You need predictable execution order

## What's Next?

- [Handoff](/agent-kit/multi-agent/handoff) — Transfer control between agents mid-conversation
- [Pipeline](/agent-kit/multi-agent/pipeline) — Static sequential execution
- [Pipeline: Parallel](/agent-kit/multi-agent/pipeline-parallel) — Static parallel execution

## See Also

- [Multi-Agent: Overview](/agent-kit/multi-agent/overview) — Introduction to multi-agent patterns
- [Multi-Agent: When to Use](/agent-kit/multi-agent/when-to-use) — Decision guide
- [Core Concepts: Budget](/agent-kit/core/budget) — Shared budget across agents
