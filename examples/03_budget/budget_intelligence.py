"""Budget Estimation — know your costs before you spend them.

Before your agents make a single LLM call, syrin can estimate what the run
will cost. This lets you catch budget problems at definition time, not after
spending money.

How it works
------------
Set ``estimation=True`` on any ``Budget``. Syrin reads each agent's
``output_tokens_estimate`` class attribute — a (p50, p95) token range you
declare on your agent — and converts it to a cost estimate using the model's
pricing. Then access ``.estimated_cost`` on any object that holds a budget:
agent, swarm, pipeline, or router.

Resolution order (highest priority first):
  1. ``output_tokens_estimate`` on the agent class (recommended)
  2. Cost history auto-recorded after each run (when estimation=True)
  3. Cost history from a custom store (if a custom estimator is configured)
  4. Built-in fallback: 500 tokens at $3/M  →  ``low_confidence=True``

Automatic cost recording
------------------------
When ``estimation=True``, syrin automatically records the actual run cost to
``~/.syrin/budget_stats.json`` after each successful ``run()`` / ``arun()``.
No manual ``store.record()`` call is needed. On subsequent ``estimated_cost``
accesses the estimate uses real historical data (``low_confidence=False``).

What you get back
-----------------
``CostEstimate`` has exactly four fields:
  - ``p50``             median expected cost in USD
  - ``p95``             95th-percentile expected cost in USD
  - ``sufficient``      True when budget.max_cost >= p95
  - ``low_confidence``  True when syrin used the fallback (no hint, no history)

Run:
    uv run python examples/03_budget/budget_intelligence.py
"""

from __future__ import annotations

import asyncio

from syrin import Agent, Budget, Model
from syrin.budget import CostEstimate, CostEstimator, InsufficientBudgetError
from syrin.enums import EstimationPolicy
from syrin.response import Response

# ── Agent definitions ─────────────────────────────────────────────────────────
#
# Declare output_tokens_estimate on your agent class.
# Use a (p50, p95) tuple when you know the distribution,
# or a single int when output length is predictable.


class ResearchAgent(Agent):
    """Searches and summarises research for a given topic."""

    model = Model.mock()
    system_prompt = "You are a thorough research assistant."
    output_tokens_estimate = (300, 900)  # most runs: ~300 tokens; worst case: ~900

    async def arun(self, input_text: str) -> Response[str]:
        return Response(content=f"Research findings on: {input_text}", cost=0.0027)


class WriterAgent(Agent):
    """Writes polished prose from research notes."""

    model = Model.mock()
    system_prompt = "You are a concise technical writer."
    output_tokens_estimate = 400  # predictable output length

    async def arun(self, input_text: str) -> Response[str]:
        return Response(content=f"Draft article: {input_text}", cost=0.0012)


class HeavyAgent(Agent):
    """Processes large documents — wide token range expected."""

    model = Model.mock()
    system_prompt = "You process large documents."
    output_tokens_estimate = (5_000, 50_000)  # high variance

    async def arun(self, input_text: str) -> Response[str]:
        return Response(content=f"Processed: {input_text}", cost=0.15)


class UnknownAgent(Agent):
    """New agent with no token hint — syrin uses a low-confidence fallback."""

    model = Model.mock()
    system_prompt = "A brand new agent."
    # No output_tokens_estimate → syrin falls back to 500 tokens, low_confidence=True

    async def arun(self, input_text: str) -> Response[str]:
        return Response(content="Result", cost=0.001)


# ── Example 1: Basic — check before you run ───────────────────────────────────


async def example_basic() -> None:
    print("── Example 1: Check estimated cost before running ──────────────────")

    agent = ResearchAgent(budget=Budget(max_cost=1.00, estimation=True))
    est = agent.estimated_cost

    # estimated_cost is None when estimation=False or no budget is set
    assert est is not None
    print(f"  p50 = ${est.p50:.6f}   (typical run)")
    print(f"  p95 = ${est.p95:.6f}   (worst case)")
    print(f"  sufficient    = {est.sufficient}    (budget covers p95)")
    print(f"  low_confidence= {est.low_confidence}  (has output_tokens_estimate hint)")
    print()


# ── Example 2: Tight budget — catch the problem before it happens ─────────────


async def example_tight_budget() -> None:
    print("── Example 2: Tight budget — estimation catches it early ───────────")

    agent = HeavyAgent(budget=Budget(max_cost=0.10, estimation=True))
    est = agent.estimated_cost
    assert est is not None
    print(f"  p50 = ${est.p50:.4f}   p95 = ${est.p95:.4f}   sufficient = {est.sufficient}")

    if not est.sufficient:
        print("  Budget may not cover the p95 estimate — consider raising max_cost.")
    print()


# ── Example 3: Low-confidence warning ────────────────────────────────────────


async def example_low_confidence() -> None:
    print("── Example 3: Agent with no hint → low_confidence fallback ─────────")

    agent = UnknownAgent(budget=Budget(max_cost=1.00, estimation=True))
    est = agent.estimated_cost
    assert est is not None
    print(f"  p50 = ${est.p50:.6f}   p95 = ${est.p95:.6f}")
    print(f"  low_confidence = {est.low_confidence}")
    print("  Tip: add output_tokens_estimate to your agent for a reliable estimate.")
    print()


# ── Example 4: EstimationPolicy — control what happens on tight budgets ───────


async def example_policy() -> None:
    print("── Example 4: EstimationPolicy ─────────────────────────────────────")

    # WARN_ONLY (default): returns the estimate, logs a warning, never raises.
    agent_warn = HeavyAgent(
        budget=Budget(
            max_cost=0.10,
            estimation=True,
            estimation_policy=EstimationPolicy.WARN_ONLY,
        )
    )
    est = agent_warn.estimated_cost
    assert est is not None
    print(
        f"  WARN_ONLY: p95=${est.p95:.4f} > budget=$0.10  →  sufficient={est.sufficient}, no exception"
    )

    # RAISE: raises InsufficientBudgetError before the run even starts.
    agent_raise = HeavyAgent(
        budget=Budget(
            max_cost=0.10,
            estimation=True,
            estimation_policy=EstimationPolicy.RAISE,
        )
    )
    try:
        # Accessing estimated_cost with RAISE policy raises if p95 > max_cost.
        _ = agent_raise.estimated_cost
        print("  RAISE: budget sufficient, no exception raised")
    except InsufficientBudgetError as e:
        print(
            f"  RAISE: InsufficientBudgetError — "
            f"p95=${e.total_p95:.4f} exceeds budget=${e.budget_configured:.2f}"
        )
    print()


# ── Example 5: Custom estimator ───────────────────────────────────────────────
#
# Inherit CostEstimator and override estimate_agent() to plug in your own
# cost model — pricing sheets, provider quotes, historical benchmarks, etc.
# The rest of the system (aggregation, policy enforcement, .estimated_cost)
# works exactly the same.


class TieredEstimator(CostEstimator):
    """Estimates cost from a simple tier table instead of token counts."""

    _TIERS: dict[str, tuple[float, float]] = {
        "ResearchAgent": (0.05, 0.12),
        "WriterAgent": (0.02, 0.04),
        "HeavyAgent": (0.50, 2.00),
    }

    def estimate_agent(self, agent_class: type) -> CostEstimate:
        p50, p95 = self._TIERS.get(agent_class.__name__, (0.01, 0.03))
        return CostEstimate(p50=p50, p95=p95, sufficient=True, low_confidence=False)


async def example_custom_estimator() -> None:
    print("── Example 5: Custom CostEstimator ───────────────────────────────")

    budget = Budget(max_cost=5.00, estimation=True, estimator=TieredEstimator())

    for AgentClass in [ResearchAgent, WriterAgent, HeavyAgent]:
        agent = AgentClass(budget=budget)
        est = agent.estimated_cost
        assert est is not None
        print(f"  {AgentClass.__name__:15s}  p50=${est.p50:.2f}  p95=${est.p95:.2f}")
    print()


# ── Example 6: Swarm — aggregate across all agents ────────────────────────────


async def example_swarm() -> None:
    from syrin.swarm import Swarm

    print("── Example 6: Swarm estimated_cost aggregates all agents ───────────")

    budget = Budget(max_cost=2.00, estimation=True)
    swarm = Swarm(
        agents=[ResearchAgent(), WriterAgent(), ResearchAgent()],
        goal="Summarise AI trends",
        budget=budget,
    )
    est = swarm.estimated_cost
    assert est is not None
    print(f"  3-agent swarm  p50=${est.p50:.6f}  p95=${est.p95:.6f}")
    print(f"  sufficient = {est.sufficient}  (budget $2.00 vs p95 ${est.p95:.4f})")
    print()


# ── Example 7: Automatic cost history — no store.record() needed ─────────────
#
# When estimation=True, syrin auto-records the actual run cost after every
# successful run() / arun() call. The first access returns low_confidence=True
# (no history yet). After the run, the next access returns low_confidence=False
# with real p50/p95 from your history.


async def example_auto_recording() -> None:
    print("── Example 7: Automatic cost history (no manual store.record()) ────")

    agent = UnknownAgent(budget=Budget(max_cost=1.00, estimation=True))

    # First access: no history yet → low_confidence=True
    est_before = agent.estimated_cost
    assert est_before is not None
    print(f"  Before run: low_confidence={est_before.low_confidence}  (no history)")

    # Run the agent — cost is auto-recorded to ~/.syrin/budget_stats.json
    result = await agent.arun("Hello")
    print(f"  Run cost: ${result.cost:.6f}  (auto-recorded)")

    # Second access: history now available → low_confidence=False
    est_after = agent.estimated_cost
    assert est_after is not None
    print(f"  After run:  low_confidence={est_after.low_confidence}  (real history)")
    print(f"  p50=${est_after.p50:.6f}   p95=${est_after.p95:.6f}")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────


async def main() -> None:
    await example_basic()
    await example_tight_budget()
    await example_low_confidence()
    await example_policy()
    await example_custom_estimator()
    await example_swarm()
    await example_auto_recording()
    print("All estimation examples complete.")


if __name__ == "__main__":
    asyncio.run(main())
