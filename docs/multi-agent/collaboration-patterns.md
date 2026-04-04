---
title: Collaboration Patterns
description: Advanced multi-agent patterns for complex workflows
weight: 97
---

## Beyond Simple Handoffs

Single-agent workflows handle straightforward tasks well. But complex real-world problems often need more sophisticated collaboration. Multiple agents might need to work in parallel, vote on answers, or coordinate through a supervisor.

This page covers advanced collaboration patterns that combine Syrin's primitives—Workflow, Swarm, Handoff, and Spawn—into proven architectures.

## The Swarm Pattern

Group related agents that share context and budget using a `Swarm`:

```python
import asyncio
from syrin import Agent, Budget, Model
from syrin.swarm import Swarm, SwarmConfig
from syrin.enums import SwarmTopology

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


async def main() -> None:
    swarm = Swarm(
        agents=[Researcher, Writer, Editor],
        config=SwarmConfig(
            topology=SwarmTopology.ORCHESTRATOR,
            budget=Budget(max_cost=5.00),
        ),
    )
    result = await swarm.run("Research and write about renewable energy")
    print(result.content)

asyncio.run(main())
```

**What just happened**: The orchestrator agent delegated sub-tasks to specialists. All agents share the same budget, enabling fluid collaboration.

## Swarm Agent Routing

Give agents descriptive names and descriptions — the orchestrator uses them to route tasks:

```python
from syrin import Agent, Model

model = Model.OpenAI("gpt-4o", api_key="your-api-key")


class CodeAgent(Agent):
    name = "coder"
    description = "Writes clean, correct code"
    model = model
    system_prompt = "You write code."


class DebugAgent(Agent):
    name = "debugger"
    description = "Finds and fixes bugs"
    model = model
    system_prompt = "You find bugs."


class TestAgent(Agent):
    name = "tester"
    description = "Writes comprehensive tests"
    model = model
    system_prompt = "You write tests."
```

**What just happened**: `name` and `description` are the signals the orchestrator uses to decide which specialist to call for a given sub-task.

## Supervisor Pattern

One agent coordinates others by spawning specialists:

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
        triage = self.spawn(TriageAgent, f"Triage: {request}")
        
        if "technical" in triage.content.lower():
            result = self.spawn(
                TechSupportAgent,
                f"Tech issue: {request}",
                transfer_context=True,
            )
        elif "billing" in triage.content.lower():
            result = self.spawn(
                BillingAgent,
                f"Billing issue: {request}",
                transfer_context=True,
            )
        else:
            result = self.spawn(
                GeneralAgent,
                f"General request: {request}",
                transfer_context=True,
            )
        
        return self.spawn(AggregatorAgent, f"Aggregate: {result.content}")


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

**What just happened**: The supervisor delegated to specialists based on triage results. Each spawn transferred context so the aggregator could synthesize a coherent final response.

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
        return self.spawn(
            AggregatorAgent,
            f"Synthesize these analyses:\n{combined}"
        )


orchestrator = DataAnalysisOrchestrator()
report = orchestrator.analyze_large_dataset(large_dataset)
```

**What just happened**: The orchestrator split work into chunks, spawned parallel agents to analyze each chunk (sharing the budget), then aggregated results. This scales analysis across large datasets.

## Workflow with Conditional Branching

Combine sequential workflow steps with dynamic routing using `BranchStep`:

```python
import asyncio
from syrin import Agent, Model
from syrin.workflow import Workflow

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


async def run_conditional(input_data: str) -> str:
    validator = ValidatorAgent()
    validation = validator.run(f"Validate: {input_data}")

    if "invalid" in (validation.content or "").lower():
        return ErrorHandlerAgent().run(f"Handle: {input_data}").content or ""

    wf = Workflow("process-and-check").step(ProcessorAgent).step(QualityAgent)
    result = await wf.run(input_data)
    return result.content or ""


result = asyncio.run(run_conditional("some input"))
```

**What just happened**: Validation ran inline; the Workflow handled the sequential process + quality steps for valid input.

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

Four hook groups are particularly useful for monitoring multi-agent interactions. `SPAWN_START` and `SPAWN_END` fire when an agent delegates to another, making them ideal for tracking delegation chains. `AGENT_RUN_START` and `AGENT_RUN_END` cover the full execution of any agent and help measure each agent's contribution. The `DYNAMIC_PIPELINE_*` family fires at distinct pipeline phases, letting you observe planning versus execution separately.

```python
from syrin import Agent, Hook, Model
from syrin.swarm import Swarm, SwarmConfig

model = Model.OpenAI("gpt-4o", api_key="your-api-key")


class MonitoredAgent(Agent):
    model = model


swarm = Swarm(agents=[MonitoredAgent, MonitoredAgent, MonitoredAgent], config=SwarmConfig())

swarm.events.on(Hook.SPAWN_START, lambda ctx: print(f"Spawn: {ctx.source_agent} -> {ctx.target_agent}"))
swarm.events.on(Hook.SPAWN_END, lambda ctx: print(f"Cost: ${ctx.cost:.4f}"))
```

## Pattern Selection Guide

Six patterns cover most multi-agent collaboration needs. Use the **Swarm** pattern when related agents need to share resources like budget and memory with LLM-driven routing. Use the **Supervisor** pattern (built on `Handoff`) when one agent should coordinate multiple specialists with explicit logic. Use the **Debate** pattern (built on `parallel()`) when you need multiple perspectives before reaching a conclusion. Use the **Fan-Out/In** pattern (built on `spawn_parallel()`) for divide-and-conquer problems where work can be split across many agents. Use the **Workflow** pattern when tasks must be processed in a fixed ordered sequence. Use the **Consensus** pattern (multiple agents plus a voting agent) when you want the system to vote on the best solution from several independent attempts.

## See Also

- [Workflow](/agent-kit/multi-agent/workflow) — Sequential and parallel execution
- [Swarm](/agent-kit/multi-agent/swarm) — LLM-driven multi-agent coordination
- [Spawn](/agent-kit/multi-agent/handoff) — Delegate tasks to specialized child agents
- [Hooks Reference](/agent-kit/debugging/hooks) — Monitor agent interactions
