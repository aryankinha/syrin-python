"""Checkpoint examples for syrin.

This module demonstrates how to use the checkpoint system for:
- Saving and loading agent state
- Configuring checkpoint behavior
- Using different storage backends
- Automatic checkpoint triggers
"""

from pathlib import Path

from dotenv import load_dotenv
from examples.models.models import almock

from syrin import Agent, CheckpointConfig, CheckpointTrigger

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def example_basic_checkpointing():
    """Basic checkpoint usage with in-memory storage."""
    print("=" * 60)
    print("Example 1: Basic Checkpointing")
    print("=" * 60)

    agent = Agent(
        model=almock,
        system_prompt="You are a helpful research assistant.",
    )

    checkpoint_id = agent.save_checkpoint()
    print(f"Saved checkpoint: {checkpoint_id}")

    checkpoints = agent.list_checkpoints()
    print(f"Available checkpoints: {checkpoints}")


def example_auto_checkpoint_triggers():
    """Automatic checkpoint triggers - checkpoints happen automatically."""
    print("\n" + "=" * 60)
    print("Example 2: Automatic Checkpoint Triggers")
    print("=" * 60)

    # STEP: Auto-save after each agent step
    agent = Agent(
        model=almock,
        checkpoint=CheckpointConfig(
            storage="memory",
            trigger=CheckpointTrigger.STEP,
        ),
    )
    print(f"Agent with STEP trigger: {agent._checkpoint_config.trigger}")

    # TOOL: Auto-save after each tool call
    agent2 = Agent(
        model=almock,
        checkpoint=CheckpointConfig(
            storage="memory",
            trigger=CheckpointTrigger.TOOL,
        ),
    )
    print(f"Agent with TOOL trigger: {agent2._checkpoint_config.trigger}")

    # ERROR: Auto-save when errors occur
    agent3 = Agent(
        model=almock,
        checkpoint=CheckpointConfig(
            storage="memory",
            trigger=CheckpointTrigger.ERROR,
        ),
    )
    print(f"Agent with ERROR trigger: {agent3._checkpoint_config.trigger}")

    # BUDGET: Auto-save before budget exhaustion
    agent4 = Agent(
        model=almock,
        checkpoint=CheckpointConfig(
            storage="memory",
            trigger=CheckpointTrigger.BUDGET,
        ),
    )
    print(f"Agent with BUDGET trigger: {agent4._checkpoint_config.trigger}")

    # MANUAL: Only save when explicitly called
    agent5 = Agent(
        model=almock,
        checkpoint=CheckpointConfig(
            storage="memory",
            trigger=CheckpointTrigger.MANUAL,
        ),
    )
    print(f"Agent with MANUAL trigger: {agent5._checkpoint_config.trigger}")


def example_checkpoint_config():
    """Configure checkpoint behavior with CheckpointConfig."""
    print("\n" + "=" * 60)
    print("Example 2: Checkpoint Configuration")
    print("=" * 60)

    config = CheckpointConfig(
        enabled=True,
        storage="sqlite",
        path="/tmp/research_agent.db",
        trigger=CheckpointTrigger.STEP,
        max_checkpoints=5,
        compress=False,
    )

    agent = Agent(
        model=almock,
        checkpoint=config,
    )

    print(f"Checkpoint config: {config}")
    print(f"Checkpointer enabled: {agent._checkpointer is not None}")


def example_checkpoint_restore():
    """Save and restore checkpoint state."""
    print("\n" + "=" * 60)
    print("Example 3: Save and Restore")
    print("=" * 60)

    agent = Agent(
        model=almock,
    )

    checkpoint_id = agent.save_checkpoint("my_research")
    print(f"Created checkpoint: {checkpoint_id}")

    checkpoints = agent.list_checkpoints("my_research")
    print(f"Checkpoints for my_research: {checkpoints}")

    if checkpoints:
        success = agent.load_checkpoint(checkpoints[-1])
        print(f"Loaded checkpoint: {success}")


def example_different_backends():
    """Using different checkpoint backends."""
    print("\n" + "=" * 60)
    print("Example 4: Different Backends")
    print("=" * 60)

    memory_config = CheckpointConfig(
        enabled=True,
        storage="memory",
    )
    print(f"Memory backend: {memory_config}")

    sqlite_config = CheckpointConfig(
        enabled=True,
        storage="sqlite",
        path="/tmp/checkpoints.db",
    )
    print(f"SQLite backend: {sqlite_config}")

    filesystem_config = CheckpointConfig(
        enabled=True,
        storage="filesystem",
        path="/tmp/checkpoints",
    )
    print(f"Filesystem backend: {filesystem_config}")


def example_checkpoint_triggers():
    """Checkpoint trigger options."""
    print("\n" + "=" * 60)
    print("Example 5: Checkpoint Triggers")
    print("=" * 60)

    triggers = [
        CheckpointTrigger.MANUAL,
        CheckpointTrigger.STEP,
        CheckpointTrigger.TOOL,
        CheckpointTrigger.ERROR,
        CheckpointTrigger.BUDGET,
    ]

    for trigger in triggers:
        config = CheckpointConfig(trigger=trigger)
        print(f"Trigger: {trigger.value} -> config.trigger: {config.trigger}")


def example_checkpoint_report():
    """Access checkpoint report from response."""
    print("\n" + "=" * 60)
    print("Example 6: Checkpoint Report")
    print("=" * 60)

    agent = Agent(
        model=almock,
    )

    agent.save_checkpoint()
    agent.save_checkpoint()

    report = agent.get_checkpoint_report()
    print(f"Checkpoint report saves: {report.checkpoints.saves}")
    print(f"Checkpoint report loads: {report.checkpoints.loads}")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Syrin Checkpoint Examples")
    print("=" * 60)

    example_basic_checkpointing()
    example_auto_checkpoint_triggers()
    example_checkpoint_config()
    example_checkpoint_restore()
    example_different_backends()
    example_checkpoint_triggers()
    example_checkpoint_report()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
