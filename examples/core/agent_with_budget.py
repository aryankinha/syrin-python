"""Agent with Budget Example.

Demonstrates:
- Creating an Agent with a Budget
- Budget tracking via response.budget and agent.budget_summary
- Budget limits and exceeded handling
- get_budget_tracker() for inspection or reservation (reserve/commit/rollback)

Run: python -m examples.core.agent_with_budget
"""

from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent, Budget, warn_on_exceeded

logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def example_agent_with_budget() -> None:
    """Agent with budget tracking."""
    print("\n" + "=" * 50)
    print("Agent with Budget Example")
    print("=" * 50)

    class Assistant(Agent):
        model = almock
        system_prompt = "You are a helpful assistant."
        budget = Budget(run=0.10, on_exceeded=warn_on_exceeded)

    assistant = Assistant()

    print(f"1. Created agent with budget: ${assistant.budget.run}")
    print(f"   Budget: {assistant.budget}")

    result = assistant.response("Explain quantum computing in detail")

    print("\n2. Response received:")
    print(f"   Content: {result.content[:80]}...")
    print(f"   Cost: ${result.cost:.6f}")

    if result.budget:
        print("\n3. Budget tracking via response.budget:")
        print(f"   Remaining: ${result.budget.remaining:.4f}")
        print(f"   Used: ${result.budget.used:.4f}")
        print(f"   Total: ${result.budget.total:.4f}")

    print("\n4. Budget summary:")
    print(f"   {assistant.budget_summary}")

    # get_budget_tracker() returns the tracker when agent has a budget (for reservation or inspection)
    tracker = assistant.get_budget_tracker()
    if tracker:
        print(
            f"\n5. Tracker (for reserve/commit/rollback or inspection): run cost=${tracker.current_run_cost:.6f}"
        )


def example_shared_budget() -> None:
    """Shared budget with parent-child agents."""
    print("\n" + "=" * 50)
    print("Shared Budget Example")
    print("=" * 50)

    class Manager(Agent):
        model = almock
        system_prompt = "You are a manager that coordinates tasks."
        budget = Budget(run=0.50, shared=True)

    class Worker(Agent):
        model = almock
        system_prompt = "You are a worker that executes tasks."
        budget = Budget(run=0.15)

    manager = Manager()
    print(f"1. Parent agent with shared budget: {manager.budget}")

    print("\n2. Spawning child agent...")
    result = manager.spawn(Worker, task="What is AI?")

    print(f"   Result: {result.content[:60]}...")
    print(f"   Cost: ${result.cost:.6f}")

    if result.budget:
        print(f"   Budget remaining: ${result.budget.remaining:.4f}")
        print(f"   Budget used: ${result.budget.used:.4f}")

    print("\n3. Parent budget after child completes:")
    print(f"   Remaining: ${manager.budget.remaining:.4f}")


if __name__ == "__main__":
    example_agent_with_budget()
    example_shared_budget()
