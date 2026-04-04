---
title: Budget Delegation
description: How agents carve budget slices for child agents — self.spawn(), self.spawn_many(), SpawnResult, and BudgetAllocationError
weight: 74
---

## Budget Flows Downward

When an agent spawns a child, it carves a slice of its remaining budget for that child. The child cannot spend more than its allocation. Any unused budget flows back to the parent's pool when the child finishes.

This creates a hierarchy of budget control — an orchestrator can spawn ten analysts and guarantee total cost never exceeds its budget, regardless of what each analyst does.

## Spawning a Single Child

Use `self.spawn()` inside any agent method:

```python
from syrin import Agent, Budget, Model
from syrin.response import Response
from syrin.swarm._spawn import SpawnResult

class OrchestratorAgent(Agent):
    model = Model.mock()
    system_prompt = "Decompose tasks and delegate to specialists."

    async def arun(self, input_text: str) -> Response[str]:
        result: SpawnResult = await self.spawn(
            AnalysisAgent,
            task="Analyse the market data",
            budget=1.00,
        )
        print(result.content)
        print(f"Spent: ${result.cost:.4f}")
        print(f"Pool remaining: ${result.budget_remaining:.4f}")
        return Response(content=result.content, cost=result.cost)
```

When you pass `budget=1.00`, Syrin allocates $1.00 from the parent's remaining pool, runs the child with that allocation, and returns any unused portion to the pool when the child finishes.

If `budget` exceeds the parent's remaining balance, `ValueError` is raised immediately — no LLM call is made.

When `budget` is omitted and the parent has a budget, the child borrows the full remaining balance and returns unused funds automatically.

`SpawnResult` has five attributes:

`content` — The child agent's output text.

`cost` — Actual cost incurred by the child in USD.

`budget_remaining` — Remaining pool balance after the child completes, in USD.

`stop_reason` — Why the child terminated (`END_TURN`, `BUDGET`, etc.).

`child_agent_id` — Unique ID in `"parent::child::uuid"` format.

## Spawning Multiple Children Concurrently

Use `self.spawn_many()` with a list of `SpawnSpec` objects to run children in parallel:

```python
from syrin.swarm._spawn import SpawnResult, SpawnSpec

class OrchestratorAgent(Agent):
    model = Model.mock()

    async def arun(self, input_text: str) -> Response[str]:
        specs = [
            SpawnSpec(agent=ResearchAgent, task="Find papers on topic A", budget=0.50),
            SpawnSpec(agent=ResearchAgent, task="Find papers on topic B", budget=0.50),
            SpawnSpec(agent=SummaryAgent,  task="Summarise all findings",  budget=0.25),
        ]
        results: list[SpawnResult] = await self.spawn_many(specs)

        combined = "\n\n".join(r.content for r in results)
        total_cost = sum(r.cost for r in results)
        return Response(content=combined, cost=total_cost)
```

Budget allocations happen concurrently from the pool. If any allocation fails (not enough budget), the others still proceed. Partial failure is the default behavior.

`SpawnSpec` has four fields: `agent` (the agent class to instantiate, required), `task` (the task string, required), `budget` (the allocation in USD, required), and `timeout` (optional per-child timeout in seconds).

## Budget Pool in a Swarm

When you pass a `Budget` to a `Swarm`, budget sharing is automatic — every agent in the swarm draws from the same pool. No extra flags needed:

```python
from syrin import Budget
from syrin.swarm import Swarm

budget = Budget(max_cost=10.00)

swarm = Swarm(
    agents=[OrchestratorAgent()],
    goal="...",
    budget=budget,
)
```

If a child agent's requested allocation exceeds the pool's remaining balance, `BudgetAllocationError` is raised:

```python
from syrin.budget._pool import BudgetAllocationError

try:
    result = await self.spawn(HeavyAgent, task="...", budget=5.00)
except BudgetAllocationError as e:
    print(f"Cannot allocate ${e.requested:.2f}; pool has ${e.available:.2f}")
```

## How Budget Flows

Here's the flow for a two-child spawn with a $10 pool:

```
Pool: $10.00
  └── OrchestratorAgent borrows from pool:
        ├── ChildA allocated $2.00 → spends $1.50 → returns $0.50 to pool
        └── ChildB allocated $1.50 → spends $1.50 → returns $0.00 to pool
  Pool remaining: $10.00 - $1.50 - $1.50 = $7.00
```

Unused budget from each child returns to the pool automatically after the child completes.

## Hooks

```python
from syrin.enums import Hook

agent.events.on(Hook.SPAWN_START, lambda ctx: print(
    f"Spawning {ctx['child_agent']} with budget ${ctx['child_budget']:.2f}"
))

agent.events.on(Hook.SPAWN_END, lambda ctx: print(
    f"Child done: cost=${ctx['cost']:.4f}, duration={ctx['duration']:.1f}s"
))
```

`Hook.SPAWN_START` context includes `source_agent`, `child_agent`, `child_task`, and `child_budget`.

`Hook.SPAWN_END` context includes `source_agent`, `child_agent`, `child_task`, `cost`, and `duration`.

## Cross-Swarm Budget

Budget delegation is scoped to the owning swarm's `BudgetPool`. Agents from different swarms don't share pools. If you need cross-swarm budgeting, create a single swarm with a shared budget and structure your agents as a hierarchy within it.

## See Also

- [Swarm](/multi-agent/swarm) — Swarm topologies
- [Hierarchy](/multi-agent/hierarchy) — Multi-level agent hierarchies
- [Budget](/core/budget) — Budget configuration
