---
title: Agent Swarm with Observability
description: Build dynamic multi-agent swarms with full lifecycle hooks and tracing
weight: 400
---

## Agent Swarm with Observability

Build adaptive multi-agent systems where agents dynamically spawn based on tasks, with complete observability through hooks, tracing, and event logging.

## Architecture

```
User Request
    ↓
Orchestrator (LLM plans agent selection)
    ↓
Agent Swarm (parallel specialized agents)
    ↓
Hooks → Tracing → Metrics
    ↓
Synthesizer (aggregates results)
```

## Dynamic Pipeline with Agent Swarm

```python
from syrin import Agent, Model, tool
from syrin.agent.multi_agent import DynamicPipeline
from syrin.enums import Hook

# Orchestrator decides which agents to spawn
orchestrator_model = Model.Almock(
    response_mode="custom",
    custom_response='[{"type":"researcher","task":"Research AI trends"},'
                     '{"type":"analyst","task":"Analyze market data"},'
                     '{"type":"writer","task":"Write report"}]',
)

# Specialized agents
class Researcher(Agent):
    _agent_name = "researcher"
    model = Model.Almock()
    system_prompt = "You research topics thoroughly."
    tools = [search_web]

class Analyst(Agent):
    _agent_name = "analyst"
    model = Model.Almock()
    system_prompt = "You analyze data critically."
    tools = [analyze_data]

class Writer(Agent):
    _agent_name = "writer"
    model = Model.Almock()
    system_prompt = "You write clear reports."
    tools = [export_report]

# Dynamic pipeline spawns agents based on orchestrator plan
pipeline = DynamicPipeline(
    agents=[Researcher, Analyst, Writer],
    model=orchestrator_model,
    max_parallel=3,
)
```

**What just happened:**
1. Orchestrator analyzes the task and decides agent composition
2. Agents spawn dynamically based on the plan
3. Parallel execution maximizes throughput
4. Results synthesized by the orchestrator

## Complete Observability Setup

Track every lifecycle event with a debugger class:

```python
from datetime import datetime
from syrin.enums import Hook

class SwarmDebugger:
    def __init__(self):
        self.events = []
        self.start_time = 0
    
    def log(self, ctx) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        event = {
            "timestamp": timestamp,
            "hook": ctx.get("_hook", "unknown"),
            "data": dict(ctx),
        }
        self.events.append(event)
        print(f"  [{timestamp}] {event['hook']}")
    
    def on(self, pipeline, *hooks: Hook) -> None:
        for hook in hooks:
            pipeline.events.on(hook, self.log)

debugger = SwarmDebugger()
debugger.on(pipeline,
    Hook.DYNAMIC_PIPELINE_START,
    Hook.DYNAMIC_PIPELINE_PLAN,
    Hook.DYNAMIC_PIPELINE_EXECUTE,
    Hook.DYNAMIC_PIPELINE_AGENT_SPAWN,
    Hook.DYNAMIC_PIPELINE_AGENT_COMPLETE,
    Hook.DYNAMIC_PIPELINE_END,
)
```

## Dynamic Pipeline Hooks

The pipeline emits these lifecycle hooks:

| Hook | When | Context Fields |
| --- | --- | --- |
| `DYNAMIC_PIPELINE_START` | Pipeline begins | `task`, `mode`, `model`, `available_agents`, `budget_remaining` |
| `DYNAMIC_PIPELINE_PLAN` | Plan generated | `task`, `plan` (list), `plan_count` |
| `DYNAMIC_PIPELINE_EXECUTE` | Execution starts | `plan`, `plan_count`, `mode` |
| `DYNAMIC_PIPELINE_AGENT_SPAWN` | Agent spawned | `agent_type`, `task`, `spawn_time`, `execution_mode` |
| `DYNAMIC_PIPELINE_AGENT_COMPLETE` | Agent finished | `agent_type`, `task`, `result_preview`, `cost`, `tokens`, `duration` |
| `DYNAMIC_PIPELINE_END` | Pipeline done | `task`, `mode`, `agents_spawned`, `total_cost`, `total_tokens`, `duration`, `result_preview` |
| `DYNAMIC_PIPELINE_ERROR` | Error occurred | `task`, `mode`, `error`, `error_type`, `agents_spawned`, `total_cost` |

## Hook Reference

Subscribe to pipeline lifecycle events:

```python
# Pipeline lifecycle
def on_start(ctx):
    print(f"Pipeline started: {ctx.task}")
    print(f"Available agents: {ctx.available_agents}")

pipeline.events.on(Hook.DYNAMIC_PIPELINE_START, on_start)

def on_plan(ctx):
    print(f"Plan: {ctx.plan_count} agents")
    for step in ctx.plan:
        print(f"  - {step['type']}: {step['task']}")

pipeline.events.on(Hook.DYNAMIC_PIPELINE_PLAN, on_plan)

def on_execute(ctx):
    print(f"Executing {ctx.plan_count} agents in {ctx.mode} mode")

pipeline.events.on(Hook.DYNAMIC_PIPELINE_EXECUTE, on_execute)

# Agent lifecycle
def on_spawn(ctx):
    print(f"Spawned: {ctx.agent_type}")
    print(f"  Task: {ctx.task}")
    print(f"  Mode: {ctx.execution_mode}")

pipeline.events.on(Hook.DYNAMIC_PIPELINE_AGENT_SPAWN, on_spawn)

def on_complete(ctx):
    print(f"Completed: {ctx.agent_type}")
    print(f"  Cost: ${ctx.cost:.4f}")
    print(f"  Tokens: {ctx.tokens}")

pipeline.events.on(Hook.DYNAMIC_PIPELINE_AGENT_COMPLETE, on_complete)

def on_end(ctx):
    print(f"Pipeline complete!")
    print(f"  Total cost: ${ctx.total_cost:.4f}")
    print(f"  Total tokens: {ctx.total_tokens}")
    print(f"  Duration: {ctx.duration:.2f}s")
    print(f"  Agents spawned: {ctx.agents_spawned}")

pipeline.events.on(Hook.DYNAMIC_PIPELINE_END, on_end)

# Error handling
def on_error(ctx):
    print(f"Error: {ctx.error_type}")
    print(f"  {ctx.error}")

pipeline.events.on(Hook.DYNAMIC_PIPELINE_ERROR, on_error)
```

## Tool Execution Hooks (Per-Agent)

Track tool calls on individual agents using agent-level hooks:

```python
# Attach tool hooks to individual agent classes
def tool_start(ctx):
    print(f"  TOOL: {ctx.tool_name}")

def tool_end(ctx):
    print(f"  DONE: {ctx.tool_name}")

def tool_error(ctx):
    print(f"  ERROR: {ctx.tool_name} - {ctx.error}")

for agent_class in [Researcher, Analyst, Writer]:
    agent_class.events.on(Hook.TOOL_CALL_START, tool_start)
    agent_class.events.on(Hook.TOOL_CALL_END, tool_end)
    agent_class.events.on(Hook.TOOL_ERROR, tool_error)
```

## Cost Aggregation

Track spending across the swarm:

```python
class CostAggregator:
    def __init__(self):
        self.total = 0.0
        self.by_agent: dict[str, float] = {}
    
    def on_spawn(self, ctx) -> None:
        print(f"Spawning: {ctx.agent_type}")
    
    def on_complete(self, ctx) -> None:
        self.total += ctx.cost
        agent_type = ctx.agent_type
        self.by_agent[agent_type] = self.by_agent.get(agent_type, 0) + ctx.cost
        print(f"  {agent_type} completed: ${ctx.cost:.4f}")
    
    def on_end(self, ctx) -> None:
        print(f"\n=== COST SUMMARY ===")
        print(f"Total: ${self.total:.4f}")
        for agent, cost in sorted(self.by_agent.items(), key=lambda x: -x[1]):
            print(f"  {agent}: ${cost:.4f}")
        print(f"Pipeline total: ${ctx.total_cost:.4f}")

aggregator = CostAggregator()
pipeline.events.on(Hook.DYNAMIC_PIPELINE_AGENT_SPAWN, aggregator.on_spawn)
pipeline.events.on(Hook.DYNAMIC_PIPELINE_AGENT_COMPLETE, aggregator.on_complete)
pipeline.events.on(Hook.DYNAMIC_PIPELINE_END, aggregator.on_end)

result = pipeline.run("Market research on AI")
```

## Execution Summary Report

Generate a complete execution report:

```python
import time

class ExecutionReport:
    def __init__(self):
        self.events = []
        self.start_time = 0
    
    def log(self, ctx) -> None:
        self.events.append({
            "hook": ctx.get("_hook", "unknown"),
            "data": dict(ctx),
        })
    
    def on(self, pipeline) -> None:
        hooks = [
            Hook.DYNAMIC_PIPELINE_START,
            Hook.DYNAMIC_PIPELINE_PLAN,
            Hook.DYNAMIC_PIPELINE_EXECUTE,
            Hook.DYNAMIC_PIPELINE_AGENT_SPAWN,
            Hook.DYNAMIC_PIPELINE_AGENT_COMPLETE,
            Hook.DYNAMIC_PIPELINE_END,
        ]
        for hook in hooks:
            pipeline.events.on(hook, self.log)
    
    def generate(self, duration: float) -> dict:
        spawn_count = len([e for e in self.events 
                          if e["hook"] == Hook.DYNAMIC_PIPELINE_AGENT_SPAWN])
        complete_count = len([e for e in self.events 
                             if e["hook"] == Hook.DYNAMIC_PIPELINE_AGENT_COMPLETE])
        end_event = next((e for e in self.events 
                         if e["hook"] == Hook.DYNAMIC_PIPELINE_END), None)
        
        return {
            "duration_s": duration,
            "events_total": len(self.events),
            "agents_spawned": spawn_count,
            "agents_completed": complete_count,
            "total_cost": end_event["data"].get("total_cost", 0) if end_event else 0,
            "total_tokens": end_event["data"].get("total_tokens", 0) if end_event else 0,
        }

report = ExecutionReport()
report.on(pipeline)

start = time.time()
result = pipeline.run("Comprehensive AI market analysis")
elapsed = time.time() - start

stats = report.generate(elapsed)
print(f"""
========================================
EXECUTION REPORT
========================================
Duration: {stats['duration_s']:.2f}s
Total Cost: ${stats['total_cost']:.4f}
Total Tokens: {stats['total_tokens']}
Agents Spawned: {stats['agents_spawned']}
Agents Completed: {stats['agents_completed']}
Events Logged: {stats['events_total']}
========================================
""")
```

## Complete Example: Research Swarm

```python
from syrin import Agent, Model, tool
from syrin.agent.multi_agent import DynamicPipeline
from syrin.enums import Hook
import time
from datetime import datetime

@tool(name="search_web", description="Search the web")
def search_web(query: str) -> str:
    return f"[SIMULATED] Search results for: {query}"

@tool(name="analyze_data", description="Analyze data")
def analyze_data(data: str) -> str:
    return f"[SIMULATED] Analysis complete. Trend: Upward"

@tool(name="fetch_news", description="Fetch latest news")
def fetch_news(topic: str) -> str:
    return f"[SIMULATED] Latest news on: {topic}"

class TechResearcher(Agent):
    _agent_name = "tech_researcher"
    model = Model.Almock()
    system_prompt = "You research technology topics."
    tools = [search_web, fetch_news]

class MarketAnalyst(Agent):
    _agent_name = "market_analyst"
    model = Model.Almock()
    system_prompt = "You analyze market trends."
    tools = [analyze_data, fetch_news]

class Writer(Agent):
    _agent_name = "writer"
    model = Model.Almock()
    system_prompt = "You write clear executive summaries."

orchestrator = Model.Almock(
    response_mode="custom",
    custom_response='[{"type":"tech_researcher","task":"Research AI technologies"},'
                     '{"type":"market_analyst","task":"Analyze AI market size and growth"},'
                     '{"type":"writer","task":"Write executive summary"}]',
)

pipeline = DynamicPipeline(
    agents=[TechResearcher, MarketAnalyst, Writer],
    model=orchestrator,
    max_parallel=3,
)

# Debugger
class Debugger:
    def __init__(self):
        self.events = []
    
    def log(self, ctx):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        hook = ctx.get("_hook", "unknown")
        self.events.append({"time": ts, "hook": hook, "data": ctx})
        print(f"[{ts}] {hook}")

debugger = Debugger()

pipeline.events.on(Hook.DYNAMIC_PIPELINE_START, debugger.log)
pipeline.events.on(Hook.DYNAMIC_PIPELINE_PLAN, debugger.log)
pipeline.events.on(Hook.DYNAMIC_PIPELINE_EXECUTE, debugger.log)
pipeline.events.on(Hook.DYNAMIC_PIPELINE_AGENT_SPAWN, debugger.log)
pipeline.events.on(Hook.DYNAMIC_PIPELINE_AGENT_COMPLETE, debugger.log)
pipeline.events.on(Hook.DYNAMIC_PIPELINE_END, debugger.log)

if __name__ == "__main__":
    print("=" * 60)
    print("AGENT SWARM EXECUTION")
    print("=" * 60)
    
    start = time.time()
    result = pipeline.run("Comprehensive AI market research report")
    elapsed = time.time() - start
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Duration: {elapsed:.2f}s")
    print(f"Total Cost: ${result.cost:.4f}")
    print(f"Preview: {result.content[:200]}...")
```

**Output:**

```
============================================================
AGENT SWARM EXECUTION
============================================================
[14:23:01] dynamic.pipeline.start
[14:23:01] dynamic.pipeline.plan
[14:23:02] dynamic.pipeline.execute
[14:23:02] dynamic.pipeline.agent.spawn (tech_researcher)
[14:23:02] dynamic.pipeline.agent.spawn (market_analyst)
[14:23:03] dynamic.pipeline.agent.complete (tech_researcher)
[14:23:03] dynamic.pipeline.agent.complete (market_analyst)
[14:23:04] dynamic.pipeline.agent.spawn (writer)
[14:23:05] dynamic.pipeline.agent.complete (writer)
[14:23:05] dynamic.pipeline.end

============================================================
RESULTS
============================================================
Duration: 4.23s
Total Cost: $0.0123
Preview: Based on comprehensive research and analysis...
```

## Serving with Playground

Expose the swarm via HTTP with the debug UI:

```python
if __name__ == "__main__":
    print("Swarm running at http://localhost:8000/playground")
    pipeline.serve(
        port=8000,
        enable_playground=True,
        debug=True,
    )
```

The playground shows:
- Agent spawning in real-time
- Tool execution traces
- Cost accumulation
- Full event timeline

## Key Hooks Summary

| Hook | When | Context Fields |
| --- | --- | --- |
| `DYNAMIC_PIPELINE_START` | Pipeline begins | `task`, `mode`, `model`, `available_agents`, `budget_remaining` |
| `DYNAMIC_PIPELINE_PLAN` | Plan generated | `task`, `plan` (list), `plan_count` |
| `DYNAMIC_PIPELINE_EXECUTE` | Execution starts | `plan`, `plan_count`, `mode` |
| `DYNAMIC_PIPELINE_AGENT_SPAWN` | Agent spawned | `agent_type`, `task`, `spawn_time`, `execution_mode` |
| `DYNAMIC_PIPELINE_AGENT_COMPLETE` | Agent finished | `agent_type`, `task`, `result_preview`, `cost`, `tokens`, `duration` |
| `DYNAMIC_PIPELINE_END` | Pipeline done | `task`, `mode`, `agents_spawned`, `total_cost`, `total_tokens`, `duration`, `result_preview` |
| `DYNAMIC_PIPELINE_ERROR` | Error occurred | `task`, `mode`, `error`, `error_type`, `agents_spawned`, `total_cost` |
| `TOOL_CALL_START` | Tool called (per-agent) | `tool_name`, `arguments` |
| `TOOL_CALL_END` | Tool finished (per-agent) | `tool_name`, `result` |
| `TOOL_ERROR` | Tool error (per-agent) | `tool_name`, `error` |

## Running the Example

```bash
# Full observability example
PYTHONPATH=. python examples/07_multi_agent/dynamic_pipeline_full.py

# Team with shared budget
PYTHONPATH=. python examples/07_multi_agent/team.py

# Comprehensive tracing
PYTHONPATH=. python -m examples.10_observability.comprehensive_tracing
```

## What's Next?

- Learn about [multi-agent patterns](/examples/multi-agent-patterns)
- Explore [observability basics](/examples/observability)
- Understand [production serving](/production/serving)

## See Also

- [Multi-agent documentation](/multi-agent/overview)
- [Dynamic pipeline](/multi-agent/dynamic-pipeline)
- [Debugging overview](/debugging/overview)
- [Hooks reference](/debugging/hooks-reference)
