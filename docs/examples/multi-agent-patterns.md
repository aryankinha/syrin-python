---
title: Multi-Agent Patterns
description: Pipeline, handoff, spawning, and team collaboration
weight: 330
---

## Multi-Agent Patterns

Build sophisticated workflows by combining multiple agents. Syrin provides several patterns for agent collaboration.

## Sequential Pipeline

Run agents in sequence, passing output from one to the next.

```python
from syrin import Agent, Model, Pipeline, prompt

model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")

@prompt
def researcher_prompt(domain: str) -> str:
    return f"You are a researcher specializing in {domain}."

@prompt
def writer_prompt(style: str) -> str:
    return f"You are a writer with a {style} style."

class Researcher(Agent):
    model = model
    system_prompt = researcher_prompt(domain="technology")

class Writer(Agent):
    model = model
    system_prompt = writer_prompt(style="professional")

pipeline = Pipeline()
result = pipeline.run([
    (Researcher, "Find information about renewable energy"),
    (Writer, "Write about renewable energy"),
])

print(f"Final output: {result.content[:100]}...")
print(f"Total cost: ${result.cost:.6f}")
```

**What just happened:**
1. Defined two agents with different roles
2. Created a pipeline that runs them sequentially
3. Writer receives Researcher's output as context
4. Got aggregated cost for the entire pipeline

## Agent Handoff

One agent delegates to another while maintaining context.

```python
from syrin import Agent, Model

model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")

class Analyzer(Agent):
    model = model
    system_prompt = "You analyze information and provide key findings."

class Presenter(Agent):
    model = model
    system_prompt = "You present information clearly and concisely."

# Step 1: Analyzer processes the request
analyzer = Analyzer()
analysis = analyzer.run("Analyze the benefits of renewable energy")
print(f"Analysis: {analysis.content[:80]}...")

# Step 2: Hand off to Presenter
presentation = analyzer.handoff(
    Presenter,
    "Present the analysis",
    context={"analysis": analysis.content}
)
print(f"Presentation: {presentation.content[:80]}...")
```

**What just happened:**
1. Analyzer processes input and generates findings
2. `handoff()` transfers to Presenter with context
3. Presenter has full access to Analyzer's output
4. Each agent contributes its specialty

## Spawn Sub-Agents

Create child agents for parallel subtasks.

```python
from syrin import Agent, Model
import asyncio

model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")

class ResearchTeam(Agent):
    model = model
    system_prompt = "You coordinate a research team."

async def main():
    team = ResearchTeam()
    
    # Spawn parallel research tasks
    results = await team.spawn(
        [
            Agent(
                model=model,
                system_prompt="Research AI trends in healthcare.",
            ),
            Agent(
                model=model,
                system_prompt="Research AI trends in finance.",
            ),
            Agent(
                model=model,
                system_prompt="Research AI trends in education.",
            ),
        ]
    )
    
    for result in results:
        print(f"- {result.content[:60]}...")

asyncio.run(main())
```

**What just happened:**
1. Parent agent spawns multiple child agents
2. Children run in parallel for speed
3. Results collected and returned to parent
4. Parent can synthesize findings

## Dynamic Pipeline with LLM Routing

Let the LLM decide which agents to use.

```python
from syrin import Agent, Model, DynamicPipeline

model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")

class Researcher(Agent):
    model = model
    system_prompt = "You research topics thoroughly."
    _agent_name = "researcher"

class Writer(Agent):
    model = model
    system_prompt = "You write clear, engaging content."
    _agent_name = "writer"

class Critic(Agent):
    model = model
    system_prompt = "You provide constructive criticism."
    _agent_name = "critic"

pipeline = DynamicPipeline(agents=[Researcher, Writer, Critic])
result = pipeline.run("Write a blog post about quantum computing")
```

**What just happened:**
1. Defined three specialized agents
2. DynamicPipeline lets the LLM choose agents
3. LLM decides order and which agents to use
4. Workflow adapts to the task

## Team Collaboration with Roles

Multiple agents work together with defined responsibilities.

```python
from syrin import Agent, Model

model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")

class ProductManager(Agent):
    model = model
    system_prompt = "You define product requirements and priorities."
    _agent_name = "pm"

class Engineer(Agent):
    model = model
    system_prompt = "You design and implement technical solutions."
    _agent_name = "engineer"

class Designer(Agent):
    model = model
    system_prompt = "You create intuitive user experiences."
    _agent_name = "designer"

class QA(Agent):
    model = model
    system_prompt = "You ensure quality and find issues."
    _agent_name = "qa"

# Team works on a feature
team = [ProductManager(), Engineer(), Designer(), QA()]
result = team[0].spawn([
    Agent(model=model, system_prompt="Define requirements for login feature."),
    Agent(model=model, system_prompt="Design database schema for users."),
    Agent(model=model, system_prompt="Create wireframes for login page."),
])
```

**What just happened:**
1. Defined agents with distinct roles
2. Spawned parallel work items
3. Each agent contributes expertise
4. Results can be synthesized by a coordinator

## Handoff with Context Visibility

Children see parent context during handoff.

```python
from syrin import Agent, Model

model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")

class SeniorDev(Agent):
    model = model
    system_prompt = "You are a senior developer. Delegate appropriately."

class JuniorDev(Agent):
    model = model
    system_prompt = "You implement tasks given to you."

class TechLead(Agent):
    model = model
    system_prompt = "You review code and provide feedback."

senior = SeniorDev()
task = "Implement user authentication"

# Senior decides to delegate to Junior
junior_result = senior.handoff(
    JuniorDev,
    task,
    context={"urgency": "high", "skill_level": "mid"}
)

# TechLead reviews Junior's work
review = senior.handoff(
    TechLead,
    f"Review this implementation: {junior_result.content}",
    context={"pr_number": 123, "reviewer": "tech-lead"}
)
```

**What just happened:**
1. SeniorDev analyzes task and delegates
2. Context passed helps JuniorDev prioritize
3. TechLead sees full context including previous work
4. Workflow adapts based on task complexity

## Intercepting Handoffs

Add hooks to monitor or modify handoffs.

```python
from syrin import Agent, Model
from syrin.enums import Hook

model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")

class Analyzer(Agent):
    model = model
    system_prompt = "You analyze data and hand off to presenters."

class ChartPresenter(Agent):
    model = model
    system_prompt = "You present data as charts."

class TextPresenter(Agent):
    model = model
    system_prompt = "You present data as text."

def on_handoff(ctx):
    print(f"Handoff from {ctx.source} to {ctx.target}")
    print(f"Task: {ctx.task[:50]}...")

Analyzer.events.on(Hook.HANDOFF_START, on_handoff)

def on_handoff_complete(ctx):
    print(f"Handoff complete. Cost: ${ctx.get('cost', 0):.4f}")

Analyzer.events.on(Hook.HANDOFF_END, on_handoff_complete)

analyzer = Analyzer()
result = analyzer.handoff(
    ChartPresenter if "chart" in analyzer.run("Show revenue data").content 
    else TextPresenter,
    "Present the analysis"
)
```

**What just happened:**
1. Hooks fire before and after each handoff
2. Can inspect or modify handoff parameters
3. Track costs and timing across agents
4. Make routing decisions based on context

## Running the Examples

```bash
# Sequential pipeline
PYTHONPATH=. python examples/07_multi_agent/pipeline.py

# Agent handoff
PYTHONPATH=. python examples/07_multi_agent/handoff.py

# Dynamic pipeline
PYTHONPATH=. python examples/07_multi_agent/dynamic_pipeline_basic.py
```

## What's Next?

- Learn about [human-in-the-loop patterns](/multi-agent/human-in-loop)
- Explore [agent swarm with observability](/examples/agent-swarm)
- Understand [dynamic pipeline](/multi-agent/dynamic-pipeline)

## See Also

- [Multi-agent overview](/multi-agent/overview)
- [Pipeline patterns](/multi-agent/pipeline)
- [Agent handoff](/multi-agent/handoff)
- [Agent Swarm example](/examples/agent-swarm) for dynamic multi-agent with hooks
