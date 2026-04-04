"""P2-T1: BudgetPool — shared budget pool for swarms."""

from __future__ import annotations

import asyncio

import pytest

from syrin.budget._pool import BudgetPool
from syrin.budget.exceptions import BudgetAllocationError


@pytest.mark.phase_2
class TestBudgetPoolCreation:
    """BudgetPool constructor and initial state."""

    def test_creates_with_total_and_per_agent_max(self) -> None:
        """BudgetPool(total, per_agent_max) sets correct attributes."""
        pool = BudgetPool(total=10.00, per_agent_max=3.00)
        assert pool.total == pytest.approx(10.00)
        assert pool.per_agent_max == pytest.approx(3.00)

    def test_initial_remaining_equals_total(self) -> None:
        """Remaining equals total before any allocations."""
        pool = BudgetPool(total=10.00, per_agent_max=3.00)
        assert pool.remaining == pytest.approx(10.00)

    def test_no_per_agent_max(self) -> None:
        """BudgetPool without per_agent_max allows any allocation up to pool total."""
        pool = BudgetPool(total=10.00)
        assert pool.per_agent_max is None

    def test_negative_total_raises(self) -> None:
        """BudgetPool with negative total raises ValueError."""
        with pytest.raises(ValueError):
            BudgetPool(total=-1.00)

    def test_negative_per_agent_max_raises(self) -> None:
        """BudgetPool with negative per_agent_max raises ValueError."""
        with pytest.raises(ValueError):
            BudgetPool(total=10.00, per_agent_max=-1.00)


@pytest.mark.phase_2
class TestBudgetPoolAllocate:
    """pool.allocate() carves budget from pool."""

    def test_allocate_reduces_remaining(self) -> None:
        """allocate(agent_id, amount) reduces pool.remaining by amount."""
        pool = BudgetPool(total=10.00, per_agent_max=3.00)
        asyncio.run(pool.allocate("agent-1", 2.00))
        assert pool.remaining == pytest.approx(8.00)

    def test_allocate_exceeds_per_agent_max_raises(self) -> None:
        """Allocating more than per_agent_max raises BudgetAllocationError."""
        pool = BudgetPool(total=10.00, per_agent_max=3.00)
        with pytest.raises(BudgetAllocationError) as exc_info:
            asyncio.run(pool.allocate("agent-1", 5.00))
        assert "per_agent_max" in str(exc_info.value).lower() or exc_info.value.amount == 5.00

    def test_allocate_twice_same_agent_raises(self) -> None:
        """Allocating for the same agent twice raises BudgetAllocationError."""
        pool = BudgetPool(total=10.00, per_agent_max=3.00)
        asyncio.run(pool.allocate("agent-1", 2.00))
        with pytest.raises(BudgetAllocationError):
            asyncio.run(pool.allocate("agent-1", 1.00))

    def test_allocate_exceeds_pool_remaining_raises(self) -> None:
        """Allocating more than pool.remaining raises BudgetAllocationError."""
        pool = BudgetPool(total=2.00, per_agent_max=3.00)
        with pytest.raises(BudgetAllocationError):
            asyncio.run(pool.allocate("agent-1", 3.00))

    def test_allocate_exact_remaining_succeeds(self) -> None:
        """Allocating exactly pool.remaining succeeds."""
        pool = BudgetPool(total=2.00)
        asyncio.run(pool.allocate("agent-1", 2.00))
        assert pool.remaining == pytest.approx(0.00)

    def test_allocate_without_per_agent_max_only_limited_by_pool(self) -> None:
        """Without per_agent_max, allocations are only limited by pool total."""
        pool = BudgetPool(total=10.00)
        asyncio.run(pool.allocate("agent-1", 8.00))
        assert pool.remaining == pytest.approx(2.00)


@pytest.mark.phase_2
class TestBudgetPoolSpend:
    """pool.spend() records actual agent spend."""

    def test_spend_reduces_remaining(self) -> None:
        """spend(agent_id, amount) reduces pool.remaining."""
        pool = BudgetPool(total=10.00, per_agent_max=3.00)
        asyncio.run(pool.allocate("agent-1", 2.00))
        asyncio.run(pool.spend("agent-1", 1.50))
        # remaining = 10 - 2 (allocated) = 8; spend tracks actual cost within allocation
        assert pool.remaining == pytest.approx(8.00)

    def test_spend_updates_agent_spent(self) -> None:
        """spend() updates the per-agent spent amount in the snapshot."""
        pool = BudgetPool(total=10.00, per_agent_max=3.00)
        asyncio.run(pool.allocate("agent-1", 2.00))
        asyncio.run(pool.spend("agent-1", 1.50))
        snap = pool.snapshot()
        assert snap["agent-1"]["spent"] == pytest.approx(1.50)

    def test_spend_unallocated_agent_raises(self) -> None:
        """spend() for an agent that hasn't been allocated raises."""
        pool = BudgetPool(total=10.00)
        with pytest.raises((BudgetAllocationError, KeyError, ValueError)):
            asyncio.run(pool.spend("unknown", 1.00))


@pytest.mark.phase_2
class TestBudgetPoolReturnUnused:
    """pool.return_unused() returns unspent allocation back to pool."""

    def test_return_unused_restores_remaining(self) -> None:
        """return_unused() adds unspent allocation back to pool.remaining."""
        pool = BudgetPool(total=10.00, per_agent_max=3.00)
        asyncio.run(pool.allocate("agent-1", 2.00))
        asyncio.run(pool.spend("agent-1", 0.50))
        asyncio.run(pool.return_unused("agent-1"))
        # Allocated 2.00, spent 0.50 → 1.50 returned
        # remaining = 8.00 (after alloc) + 1.50 (returned) = 9.50
        assert pool.remaining == pytest.approx(9.50)

    def test_return_unused_clears_allocation(self) -> None:
        """After return_unused(), the agent can be re-allocated."""
        pool = BudgetPool(total=10.00, per_agent_max=3.00)
        asyncio.run(pool.allocate("agent-1", 2.00))
        asyncio.run(pool.return_unused("agent-1"))
        # Should not raise
        asyncio.run(pool.allocate("agent-1", 1.00))
        assert pool.remaining == pytest.approx(9.00)


@pytest.mark.phase_2
class TestBudgetPoolSnapshot:
    """pool.snapshot() returns current state for all allocated agents."""

    def test_snapshot_empty_before_alloc(self) -> None:
        """Snapshot is empty before any allocations."""
        pool = BudgetPool(total=10.00, per_agent_max=3.00)
        snap = pool.snapshot()
        assert snap == {}

    def test_snapshot_includes_all_agents(self) -> None:
        """Snapshot includes entries for every allocated agent."""
        pool = BudgetPool(total=10.00, per_agent_max=3.00)
        asyncio.run(pool.allocate("agent-1", 2.00))
        asyncio.run(pool.allocate("agent-2", 1.00))
        snap = pool.snapshot()
        assert "agent-1" in snap
        assert "agent-2" in snap

    def test_snapshot_fields(self) -> None:
        """Each snapshot entry has 'allocated' and 'spent' keys."""
        pool = BudgetPool(total=10.00, per_agent_max=3.00)
        asyncio.run(pool.allocate("agent-1", 2.00))
        asyncio.run(pool.spend("agent-1", 0.75))
        snap = pool.snapshot()
        entry = snap["agent-1"]
        assert entry["allocated"] == pytest.approx(2.00)
        assert entry["spent"] == pytest.approx(0.75)


@pytest.mark.phase_2
class TestBudgetPoolConcurrency:
    """Concurrent allocations are atomic (no double-spend)."""

    async def test_concurrent_allocations_do_not_exceed_total(self) -> None:
        """Many concurrent allocations never exceed the pool total."""
        pool = BudgetPool(total=5.00, per_agent_max=1.00)
        errors: list[Exception] = []
        successes: list[str] = []

        async def try_allocate(agent_id: str) -> None:
            try:
                await pool.allocate(agent_id, 1.00)
                successes.append(agent_id)
            except BudgetAllocationError as exc:
                errors.append(exc)

        agents = [f"agent-{i}" for i in range(10)]
        await asyncio.gather(*[try_allocate(a) for a in agents])

        # Only 5 should succeed (pool total = 5.00, each needs 1.00)
        assert len(successes) == 5
        assert pool.remaining == pytest.approx(0.00)
