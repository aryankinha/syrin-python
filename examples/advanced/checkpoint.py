"""Checkpoint Example.

Demonstrates:
- Saving agent state checkpoints
- Loading checkpoints to resume agent execution
- Listing and managing checkpoints
- Different checkpoint strategies

Run: python -m examples.advanced.checkpoint
"""

from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent
from syrin.checkpoint import Checkpointer, CheckpointState
from syrin.enums import CheckpointStrategy

logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def example_basic_checkpoint() -> None:
    """Basic checkpoint save and load."""
    print("\n" + "=" * 50)
    print("Basic Checkpoint Example")
    print("=" * 50)

    checkpointer = Checkpointer()

    class StatefulAgent(Agent):
        model = almock
        system_prompt = "You are a helpful assistant."

    StatefulAgent()

    # Simulate some state
    state = {
        "messages": ["Hello", "How can I help?"],
        "iteration": 5,
        "custom_data": {"key": "value"},
    }

    # Save checkpoint
    checkpoint_id = checkpointer.save("MyAgent", state)
    print(f"Saved checkpoint: {checkpoint_id}")

    # Load checkpoint
    loaded = checkpointer.load(checkpoint_id)
    print(f"Loaded checkpoint: {loaded.checkpoint_id}")
    print(f"State: {loaded.metadata}")


def example_checkpoint_with_agent() -> None:
    """Saving actual agent state to checkpoint."""
    print("\n" + "=" * 50)
    print("Checkpoint with Agent State")
    print("=" * 50)

    checkpointer = Checkpointer()

    class ResearchAgent(Agent):
        model = almock
        system_prompt = "You are a research assistant."

    agent = ResearchAgent()

    # Make some progress
    agent.response("What is machine learning?")

    # Capture current agent state (use conversation history if available)
    state = {
        "messages": [msg.model_dump() for msg in agent.messages],
        "iteration": agent.iteration,
    }

    # Save checkpoint
    checkpoint_id = checkpointer.save("ResearchAgent", state)
    print(f"Saved checkpoint with {len(state['messages'])} messages")

    # Simulate resuming
    ResearchAgent()
    loaded = checkpointer.load(checkpoint_id)

    if loaded:
        print(f"Resumed from checkpoint: {loaded.checkpoint_id}")
        print(f"Messages in checkpoint: {len(loaded.metadata.get('messages', []))}")


def example_checkpoint_listing() -> None:
    """Listing and managing checkpoints."""
    print("\n" + "=" * 50)
    print("Checkpoint Listing")
    print("=" * 50)

    checkpointer = Checkpointer()

    # Save multiple checkpoints
    for i in range(3):
        state = {"iteration": i, "data": f"step_{i}"}
        checkpointer.save("MultiAgent", state)

    # List checkpoints
    checkpoints = checkpointer.list_checkpoints("MultiAgent")
    print(f"Checkpoints: {checkpoints}")

    # Delete a checkpoint
    if checkpoints:
        checkpointer.delete(checkpoints[0])
        print(f"Deleted: {checkpoints[0]}")

        # List again
        remaining = checkpointer.list_checkpoints("MultiAgent")
        print(f"Remaining: {remaining}")


def example_checkpoint_strategy() -> None:
    """Different checkpoint strategies."""
    print("\n" + "=" * 50)
    print("Checkpoint Strategies")
    print("=" * 50)

    # Full strategy - saves complete state
    full_checkpointer = Checkpointer(strategy=CheckpointStrategy.FULL)
    print(f"Full strategy: {full_checkpointer._strategy}")

    # Incremental - only saves changes
    incremental_checkpointer = Checkpointer(strategy=CheckpointStrategy.INCREMENTAL)
    print(f"Incremental strategy: {incremental_checkpointer._strategy}")

    # Event-sourced - saves events
    event_checkpointer = Checkpointer(strategy=CheckpointStrategy.EVENT_SOURCED)
    print(f"Event-sourced strategy: {event_checkpointer._strategy}")

    # Hybrid - combines approaches
    hybrid_checkpointer = Checkpointer(strategy=CheckpointStrategy.HYBRID)
    print(f"Hybrid strategy: {hybrid_checkpointer._strategy}")


def example_checkpoint_state_details() -> None:
    """Working with CheckpointState details."""
    print("\n" + "=" * 50)
    print("Checkpoint State Details")
    print("=" * 50)

    checkpointer = Checkpointer()

    # Create detailed state
    state = CheckpointState(
        agent_name="DetailedAgent",
        checkpoint_id="detailed_001",
        messages=["Hello", "World"],
        memory_data={"key": "value"},
        budget_state={"current_run_cost": 0.05, "limit": 0.10},
        iteration=10,
        metadata={"custom": "data"},
    )

    checkpointer._backend.save(state)

    # Load and inspect
    loaded = checkpointer.load("detailed_001")
    if loaded:
        print(f"Agent: {loaded.agent_name}")
        print(f"Created: {loaded.created_at}")
        print(f"Messages: {loaded.messages}")
        print(f"Budget state: {loaded.budget_state}")
        print(f"Iteration: {loaded.iteration}")
        print(f"Metadata: {loaded.metadata}")


def example_checkpoint_resume_simulation() -> None:
    """Simulating checkpoint resume."""
    print("\n" + "=" * 50)
    print("Checkpoint Resume Simulation")
    print("=" * 50)

    checkpointer = Checkpointer()

    class LongRunningAgent(Agent):
        model = almock
        system_prompt = "You are a helpful assistant that provides detailed information."

    # Phase 1: Start task
    agent1 = LongRunningAgent()
    agent1.response("Tell me about Python")

    # Save progress
    conv1 = agent1.conversation_memory
    msgs = [m.model_dump() for m in conv1.get_messages()] if conv1 else []
    state = {
        "messages": msgs,
        "budget_state": {
            "current_run_cost": agent1.budget_summary.get("current_run_cost", 0)
            if hasattr(agent1, "budget_summary")
            else 0
        }
        if hasattr(agent1, "budget_summary")
        else None,
    }
    checkpoint_id = checkpointer.save("LongTask", state)
    print(f"Phase 1 complete, saved checkpoint: {checkpoint_id}")

    # Phase 2: Resume from checkpoint
    loaded = checkpointer.load(checkpoint_id)
    if loaded:
        agent2 = LongRunningAgent()
        # Restore messages (simplified)
        print(f"Resumed with {len(loaded.metadata.get('messages', []))} previous messages")

        # Continue task
        response2 = agent2.response("Tell me more about it")
        print(f"Phase 2 complete: {response2.content[:50]}...")


if __name__ == "__main__":
    example_basic_checkpoint()
    example_checkpoint_with_agent()
    example_checkpoint_listing()
    example_checkpoint_strategy()
    example_checkpoint_state_details()
    example_checkpoint_resume_simulation()
