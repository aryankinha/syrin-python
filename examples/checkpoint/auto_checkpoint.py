"""Checkpoint example demonstrating auto-triggers and recovery.

This example shows how to:
1. Configure automatic checkpoint triggers
2. Save state during long-running tasks
3. Recover from failures using checkpoints
4. Track checkpoint operations in reports

Run with: python examples/checkpoint/auto_checkpoint.py

Note: This example uses mock model and won't make actual API calls.
"""

import os
import tempfile

from syrin import Agent, CheckpointConfig, CheckpointTrigger, Model


def example_with_step_trigger():
    """Example: Auto-save checkpoint after each step."""
    print("=" * 70)
    print("Example 1: STEP Trigger - Auto-save after each step")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.db")

        agent = Agent(
            model=Model(provider="mock", model_id="test"),
            checkpoint=CheckpointConfig(
                storage="sqlite",
                path=db_path,
                trigger=CheckpointTrigger.STEP,
            ),
        )

        print(f"Checkpoint trigger: {agent._checkpoint_config.trigger}")
        print(f"Checkpointer: {agent._checkpointer is not None}")
        print()

        # Manually trigger checkpoint logic to demonstrate
        print("Simulating step completion...")
        agent._maybe_checkpoint("step")
        print(f"  Checkpoints: {agent.list_checkpoints(agent._agent_name)}")

        agent._maybe_checkpoint("step")
        print(f"  Checkpoints: {agent.list_checkpoints(agent._agent_name)}")

        print(f"Total checkpoints saved: {agent.get_checkpoint_report().checkpoints.saves}")


def example_with_tool_trigger():
    """Example: Auto-save checkpoint after each tool call."""
    print("\n" + "=" * 70)
    print("Example 2: TOOL Trigger - Auto-save after each tool call")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "tool_checkpoints.db")

        agent = Agent(
            model=Model(provider="mock", model_id="test"),
            checkpoint=CheckpointConfig(
                storage="sqlite",
                path=db_path,
                trigger=CheckpointTrigger.TOOL,
            ),
        )

        print(f"Checkpoint trigger: {agent._checkpoint_config.trigger}")
        agent_name = agent._agent_name
        print()

        # Simulate tool call checkpointing
        agent._maybe_checkpoint("tool")
        print(f"  After tool: {agent.list_checkpoints(agent_name)}")

        agent._maybe_checkpoint("tool")
        print(f"  After another tool: {agent.list_checkpoints(agent_name)}")

        print(f"  Saves: {agent.get_checkpoint_report().checkpoints.saves}")


def example_manual_checkpoint():
    """Example: Manual checkpoint saving."""
    print("\n" + "=" * 70)
    print("Example 3: MANUAL Trigger - Save checkpoints manually")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "manual_checkpoints.db")

        agent = Agent(
            model=Model(provider="mock", model_id="test"),
            checkpoint=CheckpointConfig(
                storage="sqlite",
                path=db_path,
                trigger=CheckpointTrigger.MANUAL,
            ),
        )

        print(f"Checkpoint trigger: {agent._checkpoint_config.trigger}")
        print()

        # Manual checkpoints work even with MANUAL trigger
        checkpoint_id = agent.save_checkpoint("important_milestone")
        print(f"  Saved manual checkpoint: {checkpoint_id}")

        checkpoint_id2 = agent.save_checkpoint("another_milestone")
        print(f"  Saved manual checkpoint: {checkpoint_id2}")

        print(f"  Total checkpoints: {agent.list_checkpoints()}")
        print(f"  Saves: {agent.get_checkpoint_report().checkpoints.saves}")


def example_no_checkpoint_when_disabled():
    """Example: Checkpoint disabled."""
    print("\n" + "=" * 70)
    print("Example 4: Disabled Checkpoint")
    print("=" * 70)

    agent = Agent(
        model=Model(provider="mock", model_id="test"),
        checkpoint=CheckpointConfig(enabled=False),
    )

    print(f"Checkpointer: {agent._checkpointer}")

    # These should all return None/empty
    cid = agent.save_checkpoint("test")
    print(f"save_checkpoint result: {cid}")

    checkpoints = agent.list_checkpoints()
    print(f"list_checkpoints result: {checkpoints}")

    loaded = agent.load_checkpoint("test_1")
    print(f"load_checkpoint result: {loaded}")


def example_checkpoint_recovery():
    """Example: Recover from failure using checkpoints."""
    print("\n" + "=" * 70)
    print("Example 5: Checkpoint Recovery (Persistence)")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "recovery_checkpoints.db")

        # Create agent and save checkpoint
        agent1 = Agent(
            model=Model(provider="mock", model_id="test"),
            checkpoint=CheckpointConfig(
                storage="sqlite",
                path=db_path,
                trigger=CheckpointTrigger.MANUAL,
            ),
        )

        print("Step 1: Save checkpoint...")
        agent_name = agent1._agent_name
        checkpoint_id = agent1.save_checkpoint(agent_name)
        print(f"  Saved checkpoint: {checkpoint_id}")
        print(f"  Checkpoints: {agent1.list_checkpoints(agent_name)}")

        # Create new agent instance with same database
        print("\nStep 2: New agent instance (simulating restart)...")
        agent2 = Agent(
            model=Model(provider="mock", model_id="test"),
            checkpoint=CheckpointConfig(
                storage="sqlite",
                path=db_path,
                trigger=CheckpointTrigger.MANUAL,
            ),
        )

        # Checkpoint persists across instances!
        checkpoints = agent2.list_checkpoints(agent_name)
        print(f"  Available checkpoints: {checkpoints}")

        # Resume from checkpoint
        if checkpoints:
            print("\nStep 3: Resuming from checkpoint...")
            loaded = agent2.load_checkpoint(checkpoints[-1])
            print(f"  Loaded checkpoint: {loaded}")
            print(f"  Loads count: {agent2.get_checkpoint_report().checkpoints.loads}")


def example_different_backends():
    """Example: Using different storage backends."""
    print("\n" + "=" * 70)
    print("Example 6: Different Storage Backends")
    print("=" * 70)

    # Memory backend
    agent1 = Agent(
        model=Model(provider="mock", model_id="test"),
        checkpoint=CheckpointConfig(storage="memory"),
    )
    agent1.save_checkpoint("mem_test")
    print(f"Memory backend: {agent1.list_checkpoints()}")

    # SQLite backend
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        agent2 = Agent(
            model=Model(provider="mock", model_id="test"),
            checkpoint=CheckpointConfig(storage="sqlite", path=db_path),
        )
        agent2.save_checkpoint("sqlite_test")
        print(f"SQLite backend: {agent2.list_checkpoints()}")

    # Filesystem backend
    with tempfile.TemporaryDirectory() as tmpdir:
        agent3 = Agent(
            model=Model(provider="mock", model_id="test"),
            checkpoint=CheckpointConfig(storage="filesystem", path=tmpdir),
        )
        agent3.save_checkpoint("fs_test")
        print(f"Filesystem backend: {agent3.list_checkpoints()}")


def example_checkpoint_report():
    """Example: Checkpoint report shows operations."""
    print("\n" + "=" * 70)
    print("Example 7: Checkpoint Report")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "report_checkpoints.db")

        agent = Agent(
            model=Model(provider="mock", model_id="test"),
            checkpoint=CheckpointConfig(
                storage="sqlite",
                path=db_path,
                trigger=CheckpointTrigger.MANUAL,
            ),
        )

        # Make some checkpoint operations
        agent.save_checkpoint("task1")
        agent.save_checkpoint("task1")
        agent.save_checkpoint("task2")
        agent.load_checkpoint("task1_1")

        # Get the report
        report = agent.get_checkpoint_report()
        print(f"Checkpoint saves: {report.checkpoints.saves}")
        print(f"Checkpoint loads: {report.checkpoints.loads}")


def example_trigger_comparison():
    """Example: Compare different trigger behaviors."""
    print("\n" + "=" * 70)
    print("Example 8: Trigger Comparison")
    print("=" * 70)

    triggers = [
        CheckpointTrigger.MANUAL,
        CheckpointTrigger.STEP,
        CheckpointTrigger.TOOL,
        CheckpointTrigger.ERROR,
        CheckpointTrigger.BUDGET,
    ]

    for trigger in triggers:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, f"{trigger}_checkpoints.db")

            agent = Agent(
                model=Model(provider="mock", model_id="test"),
                checkpoint=CheckpointConfig(
                    storage="sqlite",
                    path=db_path,
                    trigger=trigger,
                ),
            )

            # Simulate different events
            agent._maybe_checkpoint("step")
            agent._maybe_checkpoint("tool")
            agent._maybe_checkpoint("error")
            agent._maybe_checkpoint("budget")

            saves = agent.get_checkpoint_report().checkpoints.saves

            # STEP triggers on step events
            expected = 1 if trigger == CheckpointTrigger.STEP else 0

            print(f"  {trigger.value:10} trigger -> saves: {saves} (expected: {expected})")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("Syrin Checkpoint Examples - Auto-Triggers & Recovery")
    print("=" * 70)

    example_with_step_trigger()
    example_with_tool_trigger()
    example_manual_checkpoint()
    example_no_checkpoint_when_disabled()
    example_checkpoint_recovery()
    example_different_backends()
    example_checkpoint_report()
    example_trigger_comparison()

    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
