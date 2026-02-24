"""Tests for checkpoint system - TDD approach."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime

import pytest

from syrin.checkpoint import (
    BACKENDS,
    CheckpointConfig,
    Checkpointer,
    CheckpointState,
    MemoryCheckpointBackend,
    SQLiteCheckpointBackend,
    get_checkpoint_backend,
)
from syrin.enums import CheckpointBackend, CheckpointStrategy


class TestCheckpointState:
    """Tests for CheckpointState model."""

    def test_checkpoint_state_defaults(self):
        """Test CheckpointState has proper defaults."""
        state = CheckpointState(
            agent_name="test_agent",
            checkpoint_id="test_agent_1",
        )
        assert state.agent_name == "test_agent"
        assert state.checkpoint_id == "test_agent_1"
        assert state.messages == []
        assert state.memory_data == {}
        assert state.budget_state is None
        assert state.iteration == 0
        assert state.metadata == {}

    def test_checkpoint_state_with_data(self):
        """Test CheckpointState with full data."""
        state = CheckpointState(
            agent_name="test_agent",
            checkpoint_id="test_agent_1",
            messages=[{"role": "user", "content": "hello"}],
            memory_data={"key": "value"},
            budget_state={"remaining": 10.0},
            iteration=5,
            metadata={"step": "tool_execution"},
        )
        assert state.messages == [{"role": "user", "content": "hello"}]
        assert state.memory_data == {"key": "value"}
        assert state.budget_state == {"remaining": 10.0}
        assert state.iteration == 5
        assert state.metadata == {"step": "tool_execution"}

    def test_checkpoint_state_created_at_auto(self):
        """Test CheckpointState auto-fills created_at."""
        before = datetime.now()
        state = CheckpointState(agent_name="test", checkpoint_id="test_1")
        after = datetime.now()
        assert before <= state.created_at <= after

    def test_checkpoint_state_serialization(self):
        """Test CheckpointState can be serialized to JSON."""
        state = CheckpointState(
            agent_name="test_agent",
            checkpoint_id="test_agent_1",
            messages=[{"role": "user", "content": "hello"}],
            iteration=3,
        )
        json_str = state.model_dump_json()
        assert "test_agent" in json_str
        assert "test_agent_1" in json_str
        loaded = CheckpointState.model_validate_json(json_str)
        assert loaded.agent_name == "test_agent"
        assert loaded.checkpoint_id == "test_agent_1"


class TestMemoryCheckpointBackend:
    """Tests for MemoryCheckpointBackend."""

    def test_save_and_load(self):
        """Test basic save and load operations."""
        backend = MemoryCheckpointBackend()
        state = CheckpointState(
            agent_name="test_agent",
            checkpoint_id="test_agent_1",
            iteration=5,
        )
        backend.save(state)
        loaded = backend.load("test_agent_1")
        assert loaded is not None
        assert loaded.agent_name == "test_agent"
        assert loaded.iteration == 5

    def test_load_nonexistent(self):
        """Test loading nonexistent checkpoint returns None."""
        backend = MemoryCheckpointBackend()
        result = backend.load("nonexistent")
        assert result is None

    def test_list_checkpoints(self):
        """Test listing checkpoints for an agent."""
        backend = MemoryCheckpointBackend()
        backend.save(CheckpointState(agent_name="agent1", checkpoint_id="a1_1"))
        backend.save(CheckpointState(agent_name="agent1", checkpoint_id="a1_2"))
        backend.save(CheckpointState(agent_name="agent2", checkpoint_id="a2_1"))

        agent1_checkpoints = backend.list("agent1")
        assert len(agent1_checkpoints) == 2
        assert "a1_1" in agent1_checkpoints
        assert "a1_2" in agent1_checkpoints

        agent2_checkpoints = backend.list("agent2")
        assert len(agent2_checkpoints) == 1

    def test_delete_checkpoint(self):
        """Test deleting a checkpoint."""
        backend = MemoryCheckpointBackend()
        backend.save(CheckpointState(agent_name="test", checkpoint_id="test_1"))
        assert backend.load("test_1") is not None

        backend.delete("test_1")
        assert backend.load("test_1") is None

    def test_delete_nonexistent(self):
        """Test deleting nonexistent checkpoint doesn't error."""
        backend = MemoryCheckpointBackend()
        backend.delete("nonexistent")  # Should not raise

    def test_multiple_agents_isolation(self):
        """Test checkpoints are isolated between agents."""
        backend = MemoryCheckpointBackend()
        backend.save(CheckpointState(agent_name="agent1", checkpoint_id="a1_1"))
        backend.save(CheckpointState(agent_name="agent2", checkpoint_id="a2_1"))

        a1_state = backend.load("a1_1")
        a2_state = backend.load("a2_1")

        assert a1_state.agent_name == "agent1"
        assert a2_state.agent_name == "agent2"


class TestSQLiteCheckpointBackend:
    """Tests for SQLiteCheckpointBackend."""

    def test_save_and_load(self):
        """Test basic save and load with SQLite."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            backend = SQLiteCheckpointBackend(db_path)

            state = CheckpointState(
                agent_name="test_agent",
                checkpoint_id="test_1",
                iteration=5,
            )
            backend.save(state)

            loaded = backend.load("test_1")
            assert loaded is not None
            assert loaded.agent_name == "test_agent"
            assert loaded.iteration == 5

    def test_persistence_across_instances(self):
        """Test checkpoint persists across backend instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")

            state = CheckpointState(
                agent_name="test_agent",
                checkpoint_id="test_1",
                iteration=10,
            )
            backend1 = SQLiteCheckpointBackend(db_path)
            backend1.save(state)

            backend2 = SQLiteCheckpointBackend(db_path)
            loaded = backend2.load("test_1")
            assert loaded is not None
            assert loaded.iteration == 10

    def test_list_checkpoints(self):
        """Test listing checkpoints."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            backend = SQLiteCheckpointBackend(db_path)

            backend.save(CheckpointState(agent_name="agent1", checkpoint_id="a1_1"))
            backend.save(CheckpointState(agent_name="agent1", checkpoint_id="a1_2"))
            backend.save(CheckpointState(agent_name="agent2", checkpoint_id="a2_1"))

            assert len(backend.list("agent1")) == 2
            assert len(backend.list("agent2")) == 1

    def test_delete_checkpoint(self):
        """Test deleting checkpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            backend = SQLiteCheckpointBackend(db_path)

            backend.save(CheckpointState(agent_name="test", checkpoint_id="test_1"))
            assert backend.load("test_1") is not None

            backend.delete("test_1")
            assert backend.load("test_1") is None


class TestCheckpointer:
    """Tests for Checkpointer class."""

    def test_save_returns_id(self):
        """Test save returns a checkpoint ID."""
        checkpointer = Checkpointer()
        state = {"iteration": 5, "messages": []}
        checkpoint_id = checkpointer.save("test_agent", state)
        assert checkpoint_id == "test_agent_1"

    def test_save_increments_counter(self):
        """Test multiple saves increment counter."""
        checkpointer = Checkpointer()
        id1 = checkpointer.save("test_agent", {"n": 1})
        id2 = checkpointer.save("test_agent", {"n": 2})
        id3 = checkpointer.save("test_agent", {"n": 3})

        assert id1 == "test_agent_1"
        assert id2 == "test_agent_2"
        assert id3 == "test_agent_3"

    def test_load_by_id(self):
        """Test loading checkpoint by ID."""
        checkpointer = Checkpointer()
        state = {"iteration": 5, "messages": ["hello"]}
        checkpoint_id = checkpointer.save("test_agent", state)

        loaded = checkpointer.load(checkpoint_id)
        assert loaded is not None
        assert loaded.metadata == state

    def test_list_checkpoints(self):
        """Test listing checkpoints."""
        checkpointer = Checkpointer()
        checkpointer.save("agent1", {"n": 1})
        checkpointer.save("agent1", {"n": 2})
        checkpointer.save("agent2", {"n": 3})

        assert len(checkpointer.list_checkpoints("agent1")) == 2
        assert len(checkpointer.list_checkpoints("agent2")) == 1

    def test_delete_checkpoint(self):
        """Test deleting a checkpoint."""
        checkpointer = Checkpointer()
        checkpoint_id = checkpointer.save("test_agent", {"n": 1})
        assert checkpointer.load(checkpoint_id) is not None

        checkpointer.delete(checkpoint_id)
        assert checkpointer.load(checkpoint_id) is None

    def test_load_nonexistent_returns_none(self):
        """Test loading nonexistent ID returns None."""
        checkpointer = Checkpointer()
        result = checkpointer.load("nonexistent")
        assert result is None


class TestCheckpointConfig:
    """Tests for CheckpointConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = CheckpointConfig()
        assert config.enabled is True
        assert config.trigger == "step"
        assert config.storage == "memory"
        assert config.max_checkpoints == 10
        assert config.compress is False

    def test_custom_config(self):
        """Test custom configuration."""
        config = CheckpointConfig(
            enabled=False,
            trigger="tool",
            storage="sqlite",
            max_checkpoints=5,
            compress=True,
            path="/tmp/checkpoints.db",
        )
        assert config.enabled is False
        assert config.trigger == "tool"
        assert config.storage == "sqlite"
        assert config.max_checkpoints == 5
        assert config.compress is True
        assert config.path == "/tmp/checkpoints.db"

    def test_trigger_validation(self):
        """Test trigger accepts valid values."""
        valid_triggers = ["manual", "step", "tool", "error", "budget"]
        for trigger in valid_triggers:
            config = CheckpointConfig(trigger=trigger)
            assert config.trigger == trigger

    def test_trigger_validation_invalid(self):
        """Test trigger rejects invalid values."""
        with pytest.raises(ValueError):
            CheckpointConfig(trigger="invalid_trigger")

    def test_storage_validation(self):
        """Test storage accepts valid values."""
        valid_storages = ["memory", "sqlite", "postgres", "filesystem"]
        for storage in valid_storages:
            config = CheckpointConfig(storage=storage)
            assert config.storage == storage

    def test_max_checkpoints_validation(self):
        """Test max_checkpoints validates range."""
        with pytest.raises(ValueError):
            CheckpointConfig(max_checkpoints=0)
        with pytest.raises(ValueError):
            CheckpointConfig(max_checkpoints=-1)


class TestGetCheckpointBackend:
    """Tests for get_checkpoint_backend factory."""

    def test_get_memory_backend(self):
        """Test getting memory backend."""
        backend = get_checkpoint_backend(CheckpointBackend.MEMORY)
        assert isinstance(backend, MemoryCheckpointBackend)

    def test_get_sqlite_backend(self):
        """Test getting sqlite backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            backend = get_checkpoint_backend(
                CheckpointBackend.SQLITE,
                path=db_path,
            )
            assert isinstance(backend, SQLiteCheckpointBackend)

    def test_unknown_backend_raises(self):
        """Test unknown backend raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_checkpoint_backend("unknown_backend")
        assert "Unknown checkpoint backend" in str(exc_info.value)


class TestBackendsRegistry:
    """Tests for BACKENDS registry."""

    def test_memory_in_backends(self):
        """Test MEMORY is registered."""
        assert CheckpointBackend.MEMORY in BACKENDS

    def test_sqlite_in_backends(self):
        """Test SQLITE is registered."""
        assert CheckpointBackend.SQLITE in BACKENDS


class TestCheckpointIntegration:
    """Integration tests for checkpoint system."""

    def test_full_workflow(self):
        """Test complete checkpoint workflow."""
        checkpointer = Checkpointer()

        state1 = {
            "iteration": 1,
            "messages": [{"role": "user", "content": "Hello"}],
        }
        state2 = {
            "iteration": 2,
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ],
        }
        state3 = {
            "iteration": 3,
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
                {"role": "user", "content": "How are you?"},
            ],
        }

        checkpointer.save("research_agent", state1)
        id2 = checkpointer.save("research_agent", state2)
        checkpointer.save("research_agent", state3)

        checkpoints = checkpointer.list_checkpoints("research_agent")
        assert len(checkpoints) == 3

        loaded = checkpointer.load(id2)
        assert loaded is not None
        assert loaded.metadata["iteration"] == 2
        assert len(loaded.metadata["messages"]) == 2

        checkpointer.delete(id2)
        assert len(checkpointer.list_checkpoints("research_agent")) == 2

    def test_concurrent_checkpoint_ids(self):
        """Test checkpoint IDs are unique across different agents."""
        checkpointer = Checkpointer()

        agent1_id = checkpointer.save("agent1", {"agent": 1})
        agent2_id = checkpointer.save("agent2", {"agent": 2})
        agent1_id2 = checkpointer.save("agent1", {"agent": 1})

        assert agent1_id == "agent1_1"
        assert agent2_id == "agent2_1"
        assert agent1_id2 == "agent1_2"

    def test_checkpoint_state_with_complex_data(self):
        """Test checkpoint with complex nested data."""
        state = CheckpointState(
            agent_name="complex_agent",
            checkpoint_id="complex_1",
            messages=[
                {"role": "user", "content": "Hello"},
                {
                    "role": "assistant",
                    "content": "Hi",
                    "tool_calls": [{"name": "tool1", "arguments": {"arg1": "value1"}}],
                },
            ],
            memory_data={
                "episodic": [{"content": "remember this", "importance": 0.8}],
                "semantic": [{"fact": "world is round", "confidence": 0.95}],
            },
            budget_state={
                "remaining": 45.50,
                "used": 4.50,
                "total": 50.00,
            },
            iteration=10,
            metadata={"step": "tool_execution", "tool_name": "search"},
        )

        backend = MemoryCheckpointBackend()
        backend.save(state)

        loaded = backend.load("complex_1")
        assert loaded is not None
        assert len(loaded.messages) == 2
        assert len(loaded.messages[1]["tool_calls"]) == 1
        assert loaded.memory_data["episodic"][0]["importance"] == 0.8
        assert loaded.budget_state["remaining"] == 45.50


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_state(self):
        """Test checkpoint with empty metadata."""
        checkpointer = Checkpointer()
        checkpoint_id = checkpointer.save("agent", {})
        loaded = checkpointer.load(checkpoint_id)
        assert loaded is not None
        assert loaded.metadata == {}

    def test_special_characters_in_agent_name(self):
        """Test agent names with special characters."""
        checkpointer = Checkpointer()
        special_names = ["agent-with-dash", "agent_with_underscore", "agent.special.chars"]
        for name in special_names:
            cid = checkpointer.save(name, {"test": True})
            assert checkpointer.load(cid) is not None

    def test_large_messages_list(self):
        """Test checkpoint with large messages list."""
        messages = [{"role": f"role_{i}", "content": f"message_{i}" * 100} for i in range(1000)]
        state = CheckpointState(
            agent_name="large_agent",
            checkpoint_id="large_1",
            messages=messages,
        )
        backend = MemoryCheckpointBackend()
        backend.save(state)

        loaded = backend.load("large_1")
        assert loaded is not None
        assert len(loaded.messages) == 1000

    def test_none_values_in_metadata(self):
        """Test checkpoint metadata with None values."""
        state = {
            "string": "value",
            "none": None,
            "number": 42,
            "nested": {"key": None, "value": "test"},
        }
        checkpointer = Checkpointer()
        cid = checkpointer.save("test_agent", state)
        loaded = checkpointer.load(cid)
        assert loaded is not None
        assert loaded.metadata["none"] is None
        assert loaded.metadata["nested"]["key"] is None

    def test_unicode_content(self):
        """Test checkpoint with unicode content."""
        state = {
            "messages": [
                {"role": "user", "content": "Hello 世界 🌍"},
                {"role": "assistant", "content": "Hi 你好 👋"},
            ],
        }
        checkpointer = Checkpointer()
        cid = checkpointer.save("unicode_agent", state)
        loaded = checkpointer.load(cid)
        assert loaded is not None
        assert "世界" in loaded.metadata["messages"][0]["content"]


class TestCheckpointerWithStrategy:
    """Tests for Checkpointer with different strategies."""

    def test_incremental_strategy(self):
        """Test checkpointer with incremental strategy."""
        checkpointer = Checkpointer(strategy=CheckpointStrategy.INCREMENTAL)
        assert checkpointer._strategy == CheckpointStrategy.INCREMENTAL

    def test_full_strategy(self):
        """Test checkpointer with full strategy."""
        checkpointer = Checkpointer(strategy=CheckpointStrategy.FULL)
        assert checkpointer._strategy == CheckpointStrategy.FULL

    def test_custom_backend(self):
        """Test checkpointer with custom backend."""
        custom_backend = MemoryCheckpointBackend()
        checkpointer = Checkpointer(backend=custom_backend)
        assert checkpointer._backend is custom_backend


class TestCheckpointerAutoPruning:
    """Tests for automatic checkpoint pruning."""

    def test_max_checkpoints_not_enforced_by_default(self):
        """Test default Checkpointer doesn't enforce max."""
        checkpointer = Checkpointer(max_checkpoints=3)
        # Save 5 checkpoints
        for i in range(5):
            checkpointer.save("agent", {"iteration": i})

        # All should exist (no auto-pruning in current implementation)
        checkpoints = checkpointer.list_checkpoints("agent")
        # Current implementation doesn't auto-prune, but config is stored
        assert len(checkpoints) >= 3
