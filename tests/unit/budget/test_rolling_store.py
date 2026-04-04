"""TDD tests for RollingBudgetStore and _get_default_store (auto cost history).

All tests are written first (TDD red phase). Implementation is in
src/syrin/budget/_history.py.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# test_rolling_store_record_and_stats
# ---------------------------------------------------------------------------


def test_rolling_store_record_and_stats(tmp_path: Path) -> None:
    """record() writes a cost sample, stats() returns accurate CostStats."""
    from syrin.budget._history import RollingBudgetStore

    store = RollingBudgetStore(path=tmp_path / "rolling.json")
    store.record("ResearchAgent", 0.05)
    stats = store.stats("ResearchAgent")

    assert stats.agent_name == "ResearchAgent"
    assert stats.run_count == 1
    assert stats.p50_cost == pytest.approx(0.05)
    assert stats.p95_cost == pytest.approx(0.05)
    assert stats.total_cost == pytest.approx(0.05)
    assert stats.mean == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# test_rolling_store_max_samples_evicts_oldest
# ---------------------------------------------------------------------------


def test_rolling_store_max_samples_evicts_oldest(tmp_path: Path) -> None:
    """When max_samples is reached, the oldest sample is evicted."""
    from syrin.budget._history import RollingBudgetStore

    store = RollingBudgetStore(path=tmp_path / "rolling.json", max_samples=3)

    store.record("A", 1.0)
    store.record("A", 2.0)
    store.record("A", 3.0)
    # 4th record should evict 1.0
    store.record("A", 4.0)

    stats = store.stats("A")
    # Only 3 samples kept (2.0, 3.0, 4.0)
    assert stats.run_count == 3  # run_count == len(samples) after cap
    assert stats.p50_cost == pytest.approx(3.0)
    assert stats.mean == pytest.approx((2.0 + 3.0 + 4.0) / 3)


# ---------------------------------------------------------------------------
# test_rolling_store_run_count_exceeds_max_samples
# ---------------------------------------------------------------------------


def test_rolling_store_run_count_exceeds_max_samples(tmp_path: Path) -> None:
    """run_count in the JSON file tracks total recorded runs even after eviction."""
    import json

    from syrin.budget._history import RollingBudgetStore

    store = RollingBudgetStore(path=tmp_path / "rolling.json", max_samples=2)

    store.record("A", 1.0)
    store.record("A", 2.0)
    store.record("A", 3.0)  # triggers eviction of 1.0

    raw = json.loads((tmp_path / "rolling.json").read_text())
    assert raw["A"]["run_count"] == 3
    assert len(raw["A"]["samples"]) == 2


# ---------------------------------------------------------------------------
# test_rolling_store_stats_empty_agent
# ---------------------------------------------------------------------------


def test_rolling_store_stats_empty_agent(tmp_path: Path) -> None:
    """stats() returns a zero-valued CostStats for an agent with no history."""
    from syrin.budget._history import CostStats, RollingBudgetStore

    store = RollingBudgetStore(path=tmp_path / "rolling.json")
    stats = store.stats("NonExistentAgent")

    assert isinstance(stats, CostStats)
    assert stats.run_count == 0
    assert stats.p50_cost == 0.0
    assert stats.p95_cost == 0.0
    assert stats.total_cost == 0.0
    assert stats.mean == 0.0


# ---------------------------------------------------------------------------
# test_rolling_store_p50_p95_correct
# ---------------------------------------------------------------------------


def test_rolling_store_p50_p95_correct(tmp_path: Path) -> None:
    """p50 is the median and p95 uses the standard index formula."""
    import statistics

    from syrin.budget._history import RollingBudgetStore

    samples = [0.01 * i for i in range(1, 11)]  # 0.01 .. 0.10, 10 samples
    store = RollingBudgetStore(path=tmp_path / "rolling.json", max_samples=100)

    for s in samples:
        store.record("B", s)

    stats = store.stats("B")
    assert stats.p50_cost == pytest.approx(statistics.median(samples))
    # p95: sorted[min(int(10*0.95), 9)] = sorted[9] = max
    expected_p95 = sorted(samples)[min(int(len(samples) * 0.95), len(samples) - 1)]
    assert stats.p95_cost == pytest.approx(expected_p95)


# ---------------------------------------------------------------------------
# test_rolling_store_clear
# ---------------------------------------------------------------------------


def test_rolling_store_clear(tmp_path: Path) -> None:
    """clear() removes all samples for the specified agent, leaving others intact."""
    from syrin.budget._history import RollingBudgetStore

    store = RollingBudgetStore(path=tmp_path / "rolling.json")
    store.record("A", 0.10)
    store.record("B", 0.20)

    store.clear("A")

    assert store.stats("A").run_count == 0
    assert store.stats("B").run_count == 1


# ---------------------------------------------------------------------------
# test_rolling_store_persists_across_instances
# ---------------------------------------------------------------------------


def test_rolling_store_persists_across_instances(tmp_path: Path) -> None:
    """Data written by one instance is visible to a new instance at the same path."""
    from syrin.budget._history import RollingBudgetStore

    path = tmp_path / "rolling.json"

    store1 = RollingBudgetStore(path=path)
    store1.record("ResearchAgent", 0.05)
    store1.record("ResearchAgent", 0.07)

    store2 = RollingBudgetStore(path=path)
    stats = store2.stats("ResearchAgent")

    assert stats.run_count == 2
    assert stats.p50_cost == pytest.approx(0.06)


# ---------------------------------------------------------------------------
# test_rolling_store_thread_safe
# ---------------------------------------------------------------------------


def test_rolling_store_thread_safe(tmp_path: Path) -> None:
    """50 concurrent records from different threads all land in the store."""
    from syrin.budget._history import RollingBudgetStore

    store = RollingBudgetStore(path=tmp_path / "rolling.json", max_samples=100)
    errors: list[Exception] = []

    def worker(i: int) -> None:
        try:
            store.record("ThreadAgent", float(i) * 0.001)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    stats = store.stats("ThreadAgent")
    assert stats.run_count == 50


# ---------------------------------------------------------------------------
# test_get_default_store_returns_singleton
# ---------------------------------------------------------------------------


def test_get_default_store_returns_singleton(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """_get_default_store() returns the same instance on every call."""
    import syrin.budget._history as history_module

    # Patch the module-level singleton to ensure isolation
    monkeypatch.setattr(history_module, "_default_rolling_store", None)

    store1 = history_module._get_default_store()
    store2 = history_module._get_default_store()
    assert store1 is store2
