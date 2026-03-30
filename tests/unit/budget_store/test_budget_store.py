"""BudgetStore API: concrete class with backend parameter, pluggable backends, and edge cases."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from syrin.budget import BudgetTracker
from syrin.budget_store import BudgetStore
from syrin.types import CostInfo, TokenUsage


def _tracker(cost: float = 0.5) -> BudgetTracker:
    t = BudgetTracker()
    t.record(CostInfo(cost_usd=cost, token_usage=TokenUsage()))
    return t


def test_in_memory_store_save_load() -> None:
    store = BudgetStore(key="agent1")
    store.save(_tracker(0.5))
    loaded = store.load()
    assert loaded is not None
    assert loaded.current_run_cost == 0.5
    assert BudgetStore(key="nonexistent").load() is None


def test_file_store_save_load() -> None:
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "budget.json"
        store = BudgetStore(key="default", backend="file", path=path)
        store.save(_tracker(0.25))
        loaded = store.load()
        assert loaded is not None
        assert loaded.current_run_cost == 0.25
        assert path.exists()


def test_file_store_save_load_uses_locking_on_all_platforms() -> None:
    """BudgetStore(backend='file') uses fcntl (Unix) or msvcrt (Windows) when saving."""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "budget.json"
        store = BudgetStore(key="key1", backend="file", path=path)
        store.save(_tracker(1.5))
        loaded = store.load()
        assert loaded is not None
        assert loaded.current_run_cost == 1.5


def test_file_store_concurrent_save_single_file() -> None:
    """Concurrent saves to the same file (different keys) should not corrupt state."""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "budget.json"
        store_a = BudgetStore(key="a", backend="file", path=path)
        store_b = BudgetStore(key="b", backend="file", path=path)
        errors: list[Exception] = []

        def save_store(store: BudgetStore, cost: float) -> None:
            try:
                t = _tracker(cost)
                for _ in range(20):
                    store.save(t)
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=save_store, args=(store_a, 1.0))
        t2 = threading.Thread(target=save_store, args=(store_b, 2.0))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        assert not errors, errors
        # Retry loads; concurrent writes can delay visibility on some platforms (NFS, CI).
        la, lb = None, None
        for _ in range(30):
            la = store_a.load()
            lb = store_b.load()
            if la is not None and lb is not None:
                break
            time.sleep(0.1)
        assert la is not None, "load() for 'a' failed after retries"
        assert lb is not None, "load() for 'b' failed after retries"
        assert la.current_run_cost == 1.0
        assert lb.current_run_cost == 2.0


def test_file_store_save_invalid_key_raises() -> None:
    """Save with invalid key raises ValueError."""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "budget.json"
        with pytest.raises(ValueError, match="Invalid budget store key"):
            store = BudgetStore(key="../../etc/passwd", backend="file", path=path)
            store.save(BudgetTracker())


# =============================================================================
# BUDGET STORE EDGE CASES
# =============================================================================


def test_in_memory_store_multiple_agents() -> None:
    """Store budgets for multiple agents (different keys)."""
    s1 = BudgetStore(key="agent1")
    s2 = BudgetStore(key="agent2")
    s1.save(_tracker(1.0))
    s2.save(_tracker(2.0))
    assert s1.load().current_run_cost == 1.0
    assert s2.load().current_run_cost == 2.0


def test_in_memory_store_overwrite() -> None:
    """Overwrite existing budget."""
    store = BudgetStore(key="agent:overwrite")
    store.save(_tracker(1.0))
    store.save(_tracker(3.0))
    loaded = store.load()
    assert loaded is not None
    assert loaded.current_run_cost == 3.0


def test_in_memory_store_empty_tracker() -> None:
    """Store empty tracker."""
    store = BudgetStore(key="agent:empty")
    store.save(BudgetTracker())
    loaded = store.load()
    assert loaded is not None
    assert loaded.current_run_cost == 0.0


def test_in_memory_store_zero_cost() -> None:
    """Store tracker with zero cost."""
    store = BudgetStore(key="agent:zero")
    store.save(_tracker(0.0))
    loaded = store.load()
    assert loaded is not None
    assert loaded.current_run_cost == 0.0


def test_in_memory_store_very_high_cost() -> None:
    """Store tracker with very high cost."""
    store = BudgetStore(key="agent:high")
    store.save(_tracker(1_000_000.0))
    loaded = store.load()
    assert loaded is not None
    assert loaded.current_run_cost == 1_000_000.0


def test_in_memory_store_many_records() -> None:
    """Store tracker with many records."""
    store = BudgetStore(key="agent:many")
    t = BudgetTracker()
    for _ in range(1000):
        t.record(CostInfo(cost_usd=0.001, token_usage=TokenUsage()))
    store.save(t)
    loaded = store.load()
    assert loaded is not None
    assert loaded.current_run_cost == pytest.approx(1.0)


def test_file_store_nonexistent_path() -> None:
    """Load from nonexistent path returns None."""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "nonexistent" / "budget.json"
        store = BudgetStore(key="agent", backend="file", path=path)
        loaded = store.load()
        assert loaded is None


def test_file_store_persistence() -> None:
    """Budget persists across store instances."""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "budget.json"
        s1 = BudgetStore(key="agent", backend="file", path=path)
        s1.save(_tracker(5.0))
        s2 = BudgetStore(key="agent", backend="file", path=path)
        loaded = s2.load()
        assert loaded is not None
        assert loaded.current_run_cost == 5.0


def test_file_store_multiple_agents() -> None:
    """Store multiple agents in single file."""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "budget.json"
        for i in range(5):
            BudgetStore(key=f"agent{i}", backend="file", path=path).save(_tracker(float(i)))
        for i in range(5):
            loaded = BudgetStore(key=f"agent{i}", backend="file", path=path).load()
            assert loaded is not None
            assert loaded.current_run_cost == float(i)


def test_file_store_clear() -> None:
    """Clear stored budget by saving empty tracker."""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "budget.json"
        store = BudgetStore(key="agent", backend="file", path=path)
        store.save(_tracker(1.0))
        assert store.load() is not None
        store.save(BudgetTracker())
        loaded = store.load()
        assert loaded is not None
        assert loaded.current_run_cost == 0.0


def test_file_store_corrupted_file() -> None:
    """Handle corrupted budget file."""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "budget.json"
        path.write_text("not valid json")
        store = BudgetStore(key="agent", backend="file", path=path)
        assert store.load() is None


def test_file_store_empty_file() -> None:
    """Handle empty budget file."""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "budget.json"
        path.write_text("")
        store = BudgetStore(key="agent", backend="file", path=path)
        assert store.load() is None


def test_budget_tracker_with_token_usage() -> None:
    """Store tracker with detailed token usage."""
    store = BudgetStore(key="agent:tokens")
    t = BudgetTracker()
    t.record(
        CostInfo(
            cost_usd=1.0,
            token_usage=TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150),
        )
    )
    store.save(t)
    loaded = store.load()
    assert loaded is not None
    assert loaded.current_run_cost == 1.0


# =============================================================================
# Concrete class API: backend= param, custom backend protocol, old classes removed
# =============================================================================


class TestBudgetStoreMemoryBackend:
    """BudgetStore(key, backend='memory') works like old InMemoryBudgetStore."""

    def test_load_returns_none_when_empty(self) -> None:
        store = BudgetStore(key="class-user:1")
        assert store.load() is None

    def test_key_isolation(self) -> None:
        """Different keys in same process don't share state."""
        s1 = BudgetStore(key="class-user:1")
        s2 = BudgetStore(key="class-user:2")
        s1.save(_tracker(1.0))
        assert s2.load() is None

    def test_default_backend_is_memory(self) -> None:
        store = BudgetStore(key="class-x")
        store.save(_tracker(0.1))
        assert store.load() is not None


class TestBudgetStoreFileBackendClass:
    """BudgetStore(key, backend='file', path=...) works like old FileBudgetStore."""

    def test_file_backend_requires_path(self) -> None:
        """file backend without path raises ValueError."""
        with pytest.raises(ValueError, match="path"):
            BudgetStore(key="u", backend="file")


class TestBudgetStoreCustomBackend:
    """BudgetStore(key, backend=MyBackend()) accepts custom BudgetBackend."""

    def test_custom_backend_protocol(self) -> None:
        """Custom backend must implement load/save."""
        from syrin.budget import BudgetTracker

        store_data: dict[str, dict[str, object]] = {}

        class MyBackend:
            def load(self, key: str) -> BudgetTracker | None:
                state = store_data.get(key)
                if state is None:
                    return None
                t = BudgetTracker()
                t.load_state(state)
                return t

            def save(self, key: str, tracker: BudgetTracker) -> None:
                store_data[key] = tracker.get_state()

        store = BudgetStore(key="org:acme", backend=MyBackend())
        store.save(_tracker(4.0))
        loaded = store.load()
        assert loaded is not None
        assert loaded.current_run_cost == 4.0


class TestOldClassesRemoved:
    """FileBudgetStore and InMemoryBudgetStore are removed from public API."""

    def test_file_budget_store_not_in_module(self) -> None:
        import syrin.budget_store as bs

        assert not hasattr(bs, "FileBudgetStore"), "FileBudgetStore must be removed from public API"

    def test_in_memory_budget_store_not_in_module(self) -> None:
        import syrin.budget_store as bs

        assert not hasattr(bs, "InMemoryBudgetStore"), (
            "InMemoryBudgetStore must be removed from public API"
        )

    def test_file_budget_store_not_in_syrin_root(self) -> None:
        import syrin

        assert not hasattr(syrin, "FileBudgetStore")

    def test_in_memory_budget_store_not_in_syrin_root(self) -> None:
        import syrin

        assert not hasattr(syrin, "InMemoryBudgetStore")


class TestBudgetStoreKeyOnStore:
    """budget_store_key removed from Agent — key is on BudgetStore."""

    def test_budget_store_has_key(self) -> None:
        store = BudgetStore(key="session:abc")
        assert store.key == "session:abc"

    def test_agent_budget_store_key_param_removed(self) -> None:
        """Agent no longer accepts budget_store_key= kwarg."""
        from syrin import Agent, Budget
        from syrin.model import Model

        with pytest.raises(TypeError):
            Agent(  # type: ignore[call-arg]
                model=Model.Almock(),
                budget=Budget(max_cost=1.0),
                budget_store=BudgetStore(key="u"),
                budget_store_key="u",
            )

    def test_agent_accepts_budget_store_without_key(self) -> None:
        """Agent accepts budget_store= with key baked in."""
        from syrin import Agent, Budget
        from syrin.model import Model

        agent = Agent(
            model=Model.Almock(),
            budget=Budget(max_cost=1.0),
            budget_store=BudgetStore(key="user:test"),
        )
        assert agent._budget_store is not None
        assert agent._budget_store.key == "user:test"
