"""Tests for budget cost history recording (P6-T1).

All tests are written first (TDD red phase). Implementation is in
src/syrin/budget/_history.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from syrin.budget._history import (
    BudgetStoreProtocol,
    CostRecord,
    CostStats,
    FileBudgetStore,
)


# ---------------------------------------------------------------------------
# T1: FileBudgetStore creates file on first write
# ---------------------------------------------------------------------------
def test_file_budget_store_creates_file_on_first_write(tmp_path: Path) -> None:
    """FileBudgetStore creates the JSONL file when the first record is written."""
    store_path = tmp_path / "runs.jsonl"
    assert not store_path.exists()
    store = FileBudgetStore(path=store_path)
    store.record(agent_name="ResearchAgent", cost=0.05)
    assert store_path.exists()


# ---------------------------------------------------------------------------
# T2: record() appends a record to the file
# ---------------------------------------------------------------------------
def test_record_appends_to_file(tmp_path: Path) -> None:
    """record() appends a JSON line to the JSONL file."""
    store = FileBudgetStore(path=tmp_path / "runs.jsonl")
    store.record(agent_name="ResearchAgent", cost=0.05)
    store.record(agent_name="ResearchAgent", cost=0.10)

    lines = (tmp_path / "runs.jsonl").read_text().strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["agent_name"] == "ResearchAgent"
    assert first["cost"] == pytest.approx(0.05)
    assert "timestamp" in first


# ---------------------------------------------------------------------------
# T3: Two FileBudgetStore instances sharing the same file see each other's records
# ---------------------------------------------------------------------------
def test_two_stores_share_file(tmp_path: Path) -> None:
    """Two separate FileBudgetStore instances pointing to the same path share data."""
    path = tmp_path / "shared.jsonl"
    store_a = FileBudgetStore(path=path)
    store_b = FileBudgetStore(path=path)

    store_a.record(agent_name="A", cost=0.01)
    store_b.record(agent_name="B", cost=0.02)

    stats_a = store_a.stats(agent_name="A")
    stats_b = store_b.stats(agent_name="B")
    assert stats_a.run_count == 1
    assert stats_b.run_count == 1


# ---------------------------------------------------------------------------
# T4: stats() returns CostStats
# ---------------------------------------------------------------------------
def test_stats_returns_cost_stats(tmp_path: Path) -> None:
    """store.stats() returns a CostStats instance."""
    store = FileBudgetStore(path=tmp_path / "runs.jsonl")
    store.record(agent_name="ResearchAgent", cost=0.05)
    result = store.stats(agent_name="ResearchAgent")
    assert isinstance(result, CostStats)


# ---------------------------------------------------------------------------
# T5: CostStats.run_count equals number of recorded runs for that agent
# ---------------------------------------------------------------------------
def test_stats_run_count(tmp_path: Path) -> None:
    """CostStats.run_count matches the number of recorded runs for the agent."""
    store = FileBudgetStore(path=tmp_path / "runs.jsonl")
    for i in range(5):
        store.record(agent_name="ResearchAgent", cost=0.01 * (i + 1))
    # Noise: different agent
    store.record(agent_name="OtherAgent", cost=0.99)

    stats = store.stats(agent_name="ResearchAgent")
    assert stats.run_count == 5


# ---------------------------------------------------------------------------
# T6: After 10 costs, CostStats.p50_cost is the median (within 1% tolerance)
# ---------------------------------------------------------------------------
def test_stats_p50_is_median(tmp_path: Path) -> None:
    """CostStats.p50_cost is the median of recorded costs (within 1% tolerance)."""
    import statistics

    costs = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10]
    store = FileBudgetStore(path=tmp_path / "runs.jsonl")
    for c in costs:
        store.record(agent_name="Agent", cost=c)

    stats = store.stats(agent_name="Agent")
    expected_median = statistics.median(costs)
    assert abs(stats.p50_cost - expected_median) / expected_median < 0.01


# ---------------------------------------------------------------------------
# T7: CostStats.p95_cost >= CostStats.p50_cost always
# ---------------------------------------------------------------------------
def test_stats_p95_gte_p50(tmp_path: Path) -> None:
    """CostStats.p95_cost is always >= p50_cost."""
    store = FileBudgetStore(path=tmp_path / "runs.jsonl")
    costs = [0.01 * i for i in range(1, 21)]
    for c in costs:
        store.record(agent_name="Agent", cost=c)

    stats = store.stats(agent_name="Agent")
    assert stats.p95_cost >= stats.p50_cost


# ---------------------------------------------------------------------------
# T8: CostStats.total_cost is the sum of all recorded costs
# ---------------------------------------------------------------------------
def test_stats_total_cost(tmp_path: Path) -> None:
    """CostStats.total_cost equals the sum of all recorded costs for the agent."""
    store = FileBudgetStore(path=tmp_path / "runs.jsonl")
    costs = [0.10, 0.20, 0.30]
    for c in costs:
        store.record(agent_name="Agent", cost=c)

    stats = store.stats(agent_name="Agent")
    assert stats.total_cost == pytest.approx(sum(costs))


# ---------------------------------------------------------------------------
# T9: stats("UnknownAgent") returns CostStats with run_count=0, all zeros
# ---------------------------------------------------------------------------
def test_stats_unknown_agent_returns_zero_stats(tmp_path: Path) -> None:
    """store.stats() for an unknown agent returns zero-valued CostStats."""
    store = FileBudgetStore(path=tmp_path / "runs.jsonl")
    store.record(agent_name="OtherAgent", cost=0.05)

    stats = store.stats(agent_name="UnknownAgent")
    assert stats.run_count == 0
    assert stats.p50_cost == 0.0
    assert stats.p95_cost == 0.0
    assert stats.total_cost == 0.0
    assert stats.mean == 0.0


# ---------------------------------------------------------------------------
# T10: BudgetStoreProtocol — implementing class passes isinstance()
# ---------------------------------------------------------------------------
def test_budget_store_protocol_isinstance(tmp_path: Path) -> None:
    """A class implementing BudgetStoreProtocol passes isinstance() check."""
    store = FileBudgetStore(path=tmp_path / "runs.jsonl")
    assert isinstance(store, BudgetStoreProtocol)


# ---------------------------------------------------------------------------
# T11: clear() removes all records for that agent
# ---------------------------------------------------------------------------
def test_clear_removes_agent_records(tmp_path: Path) -> None:
    """store.clear() removes all records for the specified agent."""
    store = FileBudgetStore(path=tmp_path / "runs.jsonl")
    store.record(agent_name="Agent", cost=0.10)
    store.record(agent_name="Agent", cost=0.20)
    store.record(agent_name="OtherAgent", cost=0.99)

    store.clear(agent_name="Agent")

    stats = store.stats(agent_name="Agent")
    assert stats.run_count == 0

    # OtherAgent is unaffected
    other_stats = store.stats(agent_name="OtherAgent")
    assert other_stats.run_count == 1


# ---------------------------------------------------------------------------
# Dataclass fields on CostRecord
# ---------------------------------------------------------------------------
def test_cost_record_fields() -> None:
    """CostRecord has agent_name, cost, and timestamp fields."""
    record = CostRecord(agent_name="Agent", cost=0.05, timestamp="2025-01-01T00:00:00")
    assert record.agent_name == "Agent"
    assert record.cost == 0.05
    assert record.timestamp == "2025-01-01T00:00:00"
