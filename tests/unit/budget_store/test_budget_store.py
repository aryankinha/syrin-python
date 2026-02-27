"""Tests for budget store (budget_store.py)."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from syrin.budget import BudgetTracker
from syrin.budget_store import FileBudgetStore, InMemoryBudgetStore
from syrin.types import CostInfo, TokenUsage


def test_in_memory_store_save_load() -> None:
    store = InMemoryBudgetStore()
    tracker = BudgetTracker()
    tracker.record(CostInfo(cost_usd=0.5, token_usage=TokenUsage()))
    store.save("agent1", tracker)
    loaded = store.load("agent1")
    assert loaded is not None
    assert loaded.current_run_cost == 0.5
    assert store.load("nonexistent") is None


def test_file_store_save_load() -> None:
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "budget.json"
        store = FileBudgetStore(path, single_file=True)
        tracker = BudgetTracker()
        tracker.record(CostInfo(cost_usd=0.25, token_usage=TokenUsage()))
        store.save("default", tracker)
        loaded = store.load("default")
        assert loaded is not None
        assert loaded.current_run_cost == 0.25
        assert path.exists()


def test_file_store_save_load_uses_locking_on_all_platforms() -> None:
    """FileBudgetStore uses fcntl (Unix) or msvcrt (Windows) when saving single_file.

    Save then load must succeed and preserve state on all platforms.
    """
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "budget.json"
        store = FileBudgetStore(path, single_file=True)
        tracker = BudgetTracker()
        tracker.record(CostInfo(cost_usd=1.5, token_usage=TokenUsage()))
        store.save("key1", tracker)
        loaded = store.load("key1")
        assert loaded is not None
        assert loaded.current_run_cost == 1.5


def test_file_store_concurrent_save_single_file() -> None:
    """Concurrent saves to the same file (different keys) should not corrupt state."""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "budget.json"
        store = FileBudgetStore(path, single_file=True)
        errors: list[Exception] = []

        def save_key(key: str, cost: float) -> None:
            try:
                t = BudgetTracker()
                t.record(CostInfo(cost_usd=cost, token_usage=TokenUsage()))
                for _ in range(20):
                    store.save(key, t)
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=save_key, args=("a", 1.0))
        t2 = threading.Thread(target=save_key, args=("b", 2.0))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        assert not errors, errors
        # Retry loads; concurrent writes can delay visibility on some platforms (NFS, CI).
        la, lb = None, None
        for _ in range(30):
            la = store.load("a")
            lb = store.load("b")
            if la is not None and lb is not None:
                break
            time.sleep(0.1)
        assert la is not None, "load('a') failed after retries"
        assert lb is not None, "load('b') failed after retries"
        assert la.current_run_cost == 1.0
        assert lb.current_run_cost == 2.0


def test_file_store_save_invalid_key_raises_or_succeeds() -> None:
    """Save with empty key is allowed (implementation-defined)."""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "budget.json"
        store = FileBudgetStore(path, single_file=True)
        tracker = BudgetTracker()
        store.save("", tracker)
        loaded = store.load("")
        assert loaded is not None


# =============================================================================
# BUDGET STORE EDGE CASES - TRY TO BREAK FUNCTIONALITY
# =============================================================================


def test_in_memory_store_multiple_agents() -> None:
    """Store budgets for multiple agents."""
    store = InMemoryBudgetStore()

    tracker1 = BudgetTracker()
    tracker1.record(CostInfo(cost_usd=1.0, token_usage=TokenUsage()))
    store.save("agent1", tracker1)

    tracker2 = BudgetTracker()
    tracker2.record(CostInfo(cost_usd=2.0, token_usage=TokenUsage()))
    store.save("agent2", tracker2)

    loaded1 = store.load("agent1")
    loaded2 = store.load("agent2")

    assert loaded1.current_run_cost == 1.0
    assert loaded2.current_run_cost == 2.0


def test_in_memory_store_overwrite() -> None:
    """Overwrite existing budget."""
    store = InMemoryBudgetStore()

    tracker1 = BudgetTracker()
    tracker1.record(CostInfo(cost_usd=1.0, token_usage=TokenUsage()))
    store.save("agent", tracker1)

    tracker2 = BudgetTracker()
    tracker2.record(CostInfo(cost_usd=3.0, token_usage=TokenUsage()))
    store.save("agent", tracker2)

    loaded = store.load("agent")
    assert loaded.current_run_cost == 3.0


def test_in_memory_store_empty_tracker() -> None:
    """Store empty tracker."""
    store = InMemoryBudgetStore()
    tracker = BudgetTracker()

    store.save("agent", tracker)
    loaded = store.load("agent")

    assert loaded.current_run_cost == 0.0


def test_in_memory_store_zero_cost() -> None:
    """Store tracker with zero cost."""
    store = InMemoryBudgetStore()
    tracker = BudgetTracker()
    tracker.record(CostInfo(cost_usd=0.0, token_usage=TokenUsage()))

    store.save("agent", tracker)
    loaded = store.load("agent")

    assert loaded.current_run_cost == 0.0


def test_in_memory_store_very_high_cost() -> None:
    """Store tracker with very high cost."""
    store = InMemoryBudgetStore()
    tracker = BudgetTracker()
    tracker.record(CostInfo(cost_usd=1_000_000.0, token_usage=TokenUsage()))

    store.save("agent", tracker)
    loaded = store.load("agent")

    assert loaded.current_run_cost == 1_000_000.0


def test_in_memory_store_many_records() -> None:
    """Store tracker with many records."""
    store = InMemoryBudgetStore()
    tracker = BudgetTracker()

    for _i in range(1000):
        tracker.record(CostInfo(cost_usd=0.001, token_usage=TokenUsage()))

    store.save("agent", tracker)
    loaded = store.load("agent")

    assert loaded.current_run_cost == pytest.approx(1.0)


def test_file_store_nonexistent_path() -> None:
    """Load from nonexistent path."""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "nonexistent" / "budget.json"
        store = FileBudgetStore(path, single_file=True)
        loaded = store.load("agent")
        assert loaded is None


def test_file_store_persistence() -> None:
    """Test budget persists across store instances."""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "budget.json"

        # First store instance
        store1 = FileBudgetStore(path, single_file=True)
        tracker = BudgetTracker()
        tracker.record(CostInfo(cost_usd=5.0, token_usage=TokenUsage()))
        store1.save("agent", tracker)

        # Second store instance
        store2 = FileBudgetStore(path, single_file=True)
        loaded = store2.load("agent")

        assert loaded.current_run_cost == 5.0


def test_file_store_multiple_agents() -> None:
    """Store multiple agents in single file."""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "budget.json"
        store = FileBudgetStore(path, single_file=True)

        for i in range(5):
            tracker = BudgetTracker()
            tracker.record(CostInfo(cost_usd=float(i), token_usage=TokenUsage()))
            store.save(f"agent{i}", tracker)

        for i in range(5):
            loaded = store.load(f"agent{i}")
            assert loaded.current_run_cost == float(i)


def test_file_store_clear() -> None:
    """Clear stored budget by saving empty tracker."""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "budget.json"
        store = FileBudgetStore(path, single_file=True)

        tracker = BudgetTracker()
        tracker.record(CostInfo(cost_usd=1.0, token_usage=TokenUsage()))
        store.save("agent", tracker)

        # Verify saved
        assert store.load("agent") is not None

        # Clear by saving empty tracker
        empty_tracker = BudgetTracker()
        store.save("agent", empty_tracker)

        # Verify cleared
        loaded = store.load("agent")
        assert loaded.current_run_cost == 0.0


def test_file_store_corrupted_file() -> None:
    """Handle corrupted budget file."""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "budget.json"
        path.write_text("not valid json")

        store = FileBudgetStore(path, single_file=True)
        # Should handle gracefully
        loaded = store.load("agent")
        assert loaded is None


def test_file_store_empty_file() -> None:
    """Handle empty budget file."""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "budget.json"
        path.write_text("")

        store = FileBudgetStore(path, single_file=True)
        loaded = store.load("agent")
        assert loaded is None


def test_budget_tracker_with_token_usage() -> None:
    """Store tracker with detailed token usage."""
    store = InMemoryBudgetStore()
    tracker = BudgetTracker()
    tracker.record(
        CostInfo(
            cost_usd=1.0,
            token_usage=TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150),
        )
    )

    store.save("agent", tracker)
    loaded = store.load("agent")

    # Verify cost is preserved
    assert loaded.current_run_cost == 1.0
