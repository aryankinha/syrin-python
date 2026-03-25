"""Budget Persistence Example.

Demonstrates:
- FileBudgetStore for persisting budget state across restarts
- budget_store_key for per-user/per-org isolation
- Rate limits that survive process restarts

Run: python -m examples.03_budget.budget_persistence
Visit: http://localhost:8000/playground

Requires: uv pip install syrin[serve]
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent, Budget, RateLimit, raise_on_exceeded
from syrin.budget_store import FileBudgetStore

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


# 1. FileBudgetStore — persist to disk
store_path = Path(__file__).resolve().parent.parent / "data" / "budget_example.json"
store_path.parent.mkdir(parents=True, exist_ok=True)


class PersistentAgent(Agent):
    _agent_name = "persistent-budget"
    _agent_description = "Agent with FileBudgetStore (persists across restarts)"
    model = almock
    system_prompt = "You are concise."
    budget = Budget(
        max_cost=0.10,
        rate_limits=RateLimit(day=5.00, month=50.00, month_days=30),
        on_exceeded=raise_on_exceeded,
    )


agent = PersistentAgent(
    budget_store=FileBudgetStore(store_path, single_file=True),
    budget_store_key="example_user",
)
result = agent.run("Summarize Python in two sentences.")
print(f"Cost: ${result.cost:.6f}")
print(f"Budget state: {agent.budget_state}")

# 2. Per-user isolation via budget_store_key
agent_alice = PersistentAgent(
    budget_store=FileBudgetStore(store_path, single_file=True),
    budget_store_key="alice",
)
agent_bob = PersistentAgent(
    budget_store=FileBudgetStore(store_path, single_file=True),
    budget_store_key="bob",
)
agent_alice.run("Hello from Alice")
agent_bob.run("Hello from Bob")
print(f"Alice budget: {agent_alice.budget_state}")
print(f"Bob budget: {agent_bob.budget_state}")


if __name__ == "__main__":
    agent = PersistentAgent(
        budget_store=FileBudgetStore(store_path, single_file=True),
        budget_store_key="example_user",
    )
    print("Serving at http://localhost:8000/playground")
    agent.serve(port=8000, enable_playground=True, debug=True)
