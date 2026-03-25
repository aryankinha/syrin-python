---
title: Collaboration Patterns
description: Advanced multi-agent patterns for complex workflows
weight: 97
---

## Beyond Simple Handoffs

Single-agent workflows handle straightforward tasks well. But complex real-world problems often need more sophisticated collaboration. Multiple agents might need to work in parallel, vote on answers, or coordinate through a supervisor.

This page covers advanced collaboration patterns that combine Syrin's primitives—Pipeline, Handoff, Spawn, and AgentTeam—into proven architectures.

## The Team Pattern

Group related agents that share context and budget:

```python
from syrin import Agent, Budget, Model
from syrin.agent.multi_agent import AgentTeam

model = Model.OpenAI("gpt-4o", api_key="your-api-key")


class Researcher(Agent):
    model = model
    system_prompt = "You research topics thoroughly."


class Writer(Agent):
    model = model
    system_prompt = "You write clear, engaging content."


class Editor(Agent):
    model = model
    system_prompt = "You edit and polish content."


# Create a team with shared budget
team = AgentTeam(
    agents=[Researcher(), Writer(), Editor()],
    budget=Budget(max_cost=5.00, shared=True),  # All agents share this budget
    shared_memory=True,  # Agents share persistent memory
)

# Automatic agent selection based on task keywords
result = team.run_task("Research and write about renewable energy")
```

**What just happened**: The team selected the appropriate agent based on task keywords. All agents share the same budget and memory, enabling fluid collaboration.

## Agent Selection

Teams can automatically route tasks to the best agent:

```python
from syrin import Agent, Model
from syrin.agent.multi_agent import AgentTeam

model = Model.OpenAI("gpt-4o", api_key="your-api-key")


class CodeAgent(Agent):
    _agent_name = "coder"
    model = model
    system_prompt = "You write code."


class DebugAgent(Agent):
    _agent_name = "debugger"
    model = model
    system_prompt = "You find bugs."


class TestAgent(Agent):
    _agent_name = "tester"
    model = model
    system_prompt = "You write tests."


team = AgentTeam(agents=[CodeAgent(), DebugAgent(), TestAgent()])

# Automatic routing based on keywords
selected = team.select_agent("write a function to parse JSON")
print(selected.__class__.__name__)  # CodeAgent

selected = team.select_agent("find the bug in my code")
print(selected.__class__.__name__)  # DebugAgent

selected = team.select_agent("add test coverage")
print(selected.__class__.__name__)  # TestAgent
```

**What just happened**: `select_agent()` matched task keywords to agent names and descriptions, routing to the most appropriate specialist.

## Supervisor Pattern

One agent coordinates others through structured handoffs:

```python
from syrin import Agent, Budget, Model

model = Model.OpenAI("gpt-4o", api_key="your-api-key")


class SupervisorAgent(Agent):
    model = model
    system_prompt = """You are a supervisor. Your job is to:
1. Triage incoming requests
2. Route to the appropriate specialist
3. Aggregate results
Never do the work yourself—always delegate."""

    def handle_request(self, request: str) -> str:
        triage = self.handoff(TriageAgent, f"Triage: {request}")
        
        if "technical" in triage.content.lower():
            result = self.handoff(
                TechSupportAgent,
                f"Tech issue: {request}",
                transfer_context=True,
            )
        elif "billing" in triage.content.lower():
            result = self.handoff(
                BillingAgent,
                f"Billing issue: {request}",
                transfer_context=True,
            )
        else:
            result = self.handoff(
                GeneralAgent,
                f"General request: {request}",
                transfer_context=True,
            )
        
        return self.handoff(AggregatorAgent, f"Aggregate: {result.content}")


class TriageAgent(Agent):
    model = model
    system_prompt = "Classify as: technical, billing, or general."


class TechSupportAgent(Agent):
    model = model
    system_prompt = "Provide technical support."


class BillingAgent(Agent):
    model = model
    system_prompt = "Handle billing inquiries."


class GeneralAgent(Agent):
    model = model
    system_prompt = "Handle general requests."


class AggregatorAgent(Agent):
    model = model
    system_prompt = "Combine and summarize responses."""


supervisor = SupervisorAgent()
response = supervisor.handle_request("My bill is wrong")
```

**What just happened**: The supervisor delegated to specialists based on triage results. Each handoff transferred context so the aggregator could synthesize a coherent final response.

## Debate Pattern

Multiple agents argue different perspectives, then vote or synthesize:

```python
from syrin import Agent, Model
from syrin.agent.multi_agent import parallel


model = Model.OpenAI("gpt-4o", api_key="your-api-key")


class ProAgent(Agent):
    model = model
    system_prompt = "Argue for the proposal. Be persuasive."


class ConAgent(Agent):
    model = model
    system_prompt = "Argue against the proposal. Be critical."


class JudgeAgent(Agent):
    model = model
    system_prompt = """You are a judge. Review arguments for and against.
Provide a balanced verdict with reasoning."""


async def run_debate(proposal: str) -> str:
    pro = ProAgent()
    con = ConAgent()
    judge = JudgeAgent()

    pro_args, con_args = await parallel([
        (pro, f"Argue for: {proposal}"),
        (con, f"Argue against: {proposal}"),
    ])

    verdict = judge.run(
        f"Proposal: {proposal}\n\nArguments for: {pro_args.content}\n\nArguments against: {con_args.content}"
    )
    
    return verdict.content


result = run_debate("Should we adopt microservices?")
```

**What just happened**: Pro and Con agents argued in parallel. The judge synthesized both perspectives into a balanced verdict. This pattern works well for decision-making and risk assessment.

## Fan-Out, Fan-In Pattern

Spawn multiple agents to work on parts of a problem, then aggregate:

```python
from syrin import Agent, Model, Budget

model = Model.OpenAI("gpt-4o", api_key="your-api-key")


class AnalyzerAgent(Agent):
    model = model
    system_prompt = "Analyze data and provide insights."


class AggregatorAgent(Agent):
    model = model
    system_prompt = """You receive multiple analyses. Synthesize them into a coherent report."""


class DataAnalysisOrchestrator(Agent):
    model = model
    budget = Budget(max_cost=2.00)
    system_prompt = "You coordinate parallel data analysis."

    def analyze_large_dataset(self, dataset: str) -> str:
        parts = dataset.split_chunks(4)  # Split into 4 parts
        
        # Fan-out: spawn parallel analysis
        results = self.spawn_parallel([
            (AnalyzerAgent, f"Analyze this data: {part}")
            for part in parts
        ])
        
        # Fan-in: aggregate results
        combined = "\n\n".join(r.content for r in results)
        return self.handoff(
            AggregatorAgent,
            f"Synthesize these analyses:\n{combined}"
        )


orchestrator = DataAnalysisOrchestrator()
report = orchestrator.analyze_large_dataset(large_dataset)
```

**What just happened**: The orchestrator split work into chunks, spawned parallel agents to analyze each chunk (sharing the budget), then aggregated results. This scales analysis across large datasets.

## Pipeline with Conditional Branching

Combine pipeline execution with dynamic routing:

```python
from syrin import Agent, Model
from syrin.agent.multi_agent import Pipeline, DynamicPipeline

model = Model.OpenAI("gpt-4o", api_key="your-api-key")


class ValidatorAgent(Agent):
    model = model
    system_prompt = "Validate input. Output 'valid' or 'invalid'."


class ProcessorAgent(Agent):
    model = model
    system_prompt = "Process validated input."


class ErrorHandlerAgent(Agent):
    model = model
    system_prompt = "Handle invalid input gracefully."


class QualityAgent(Agent):
    model = model
    system_prompt = "Quality check the output."


class ConditionalPipeline:
    def __init__(self):
        self.validator = ValidatorAgent()
        self.processor = ProcessorAgent()
        self.error_handler = ErrorHandlerAgent()
        self.quality = QualityAgent()

    def run(self, input_data: str) -> str:
        validation = self.validator.run(f"Validate: {input_data}")
        
        if "invalid" in validation.content.lower():
            return self.error_handler.run(f"Handle: {input_data}").content
        
        processed = self.processor.run(f"Process: {input_data}").content
        quality = self.quality.run(f"Check: {processed}").content
        
        return f"{processed}\n\nQuality: {quality}"


pipeline = ConditionalPipeline()
result = pipeline.run("some input")
```

**What just happened**: The pipeline validated input first, branching to error handling if invalid. Valid input proceeded through processing and quality checks.

## Consensus Pattern

Multiple agents generate solutions, then vote on the best:

```python
from syrin import Agent, Model, Response
from syrin.types import TokenUsage


model = Model.OpenAI("gpt-4o", api_key="your-api-key")


class SolutionAgent(Agent):
    model = model
    system_prompt = "Generate a solution. Be thorough but concise."


class VoterAgent(Agent):
    model = model
    system_prompt = """You vote on the best solution. Consider:
- Correctness
- Efficiency
- Clarity

Output only the number (1, 2, or 3) of your chosen solution."""


def run_consensus(problem: str, n_solutions: int = 3) -> str:
    solutions = []
    
    for i in range(n_solutions):
        agent = SolutionAgent()
        result = agent.run(f"Solve: {problem}")
        solutions.append(f"Solution {i+1}:\n{result.content}")
    
    votes = []
    for i, sol in enumerate(solutions):
        voter = VoterAgent()
        vote = voter.run(f"Problem: {problem}\n\n{sol}")
        try:
            votes.append(int(vote.content.strip()[-1]))
        except ValueError:
            votes.append(i)
    
    winner_idx = max(set(votes), key=votes.count)
    return solutions[winner_idx]


winner = run_consensus("Optimize a database query")
```

**What just happened**: Multiple agents generated independent solutions. A voting agent ranked each solution. The most-voted solution was selected as the consensus answer.

## Hooks for Collaboration

Monitor multi-agent interactions with hooks:

| Hook | When | Useful For |
|------|------|------------|
| `HANDOFF_START/END` | Agent transfers control | Tracking delegation chains |
| `SPAWN_START/END` | Child agent created | Monitoring fan-out |
| `AGENT_RUN_START/END` | Agent execution | Measuring agent contribution |
| `DYNAMIC_PIPELINE_*` | Pipeline phases | Observing planning vs execution |

```python
from syrin import Agent, Hook, Model
from syrin.agent.multi_agent import AgentTeam

model = Model.OpenAI("gpt-4o", api_key="your-api-key")


class MonitoredAgent(Agent):
    model = model


team = AgentTeam(agents=[MonitoredAgent() for _ in range(3)])

for agent in team.agents:
    agent.events.on(Hook.HANDOFF_START, lambda ctx: print(f"Handoff: {ctx.source_agent} -> {ctx.target_agent}"))
    agent.events.on(Hook.HANDOFF_END, lambda ctx: print(f"Cost: ${ctx.cost:.4f}"))
```

## Pattern Selection Guide

| Pattern | Use When | Key Primitive |
|---------|----------|---------------|
| **Team** | Related agents share resources | `AgentTeam` |
| **Supervisor** | One agent coordinates specialists | `Handoff` |
| **Debate** | Multiple perspectives needed | `parallel()` |
| **Fan-Out/In** | Divide and conquer | `spawn_parallel()` |
| **Pipeline** | Ordered stages | `Pipeline` |
| **Consensus** | Vote on best solution | Multiple agents + voting |

## See Also

- [Pipeline](/multi-agent/pipeline) — Sequential and parallel execution
- [Dynamic Pipeline](/multi-agent/dynamic-pipeline) — LLM-driven routing
- [Handoff](/multi-agent/handoff) — Transfer control between agents
- [Spawn](/multi-agent/handoff) — Create child agents
- [Hooks Reference](/debugging/hooks) — Monitor agent interactions
