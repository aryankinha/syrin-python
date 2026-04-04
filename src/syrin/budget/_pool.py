"""BudgetPool — async-safe shared budget pool for swarms.

One :class:`BudgetPool` is shared across all agents in a :class:`~syrin.swarm.Swarm`
when ``Budget(shared=True)`` is used.  All mutations are protected by an
:class:`asyncio.Lock` so concurrent allocations are atomic.
"""

from __future__ import annotations

import asyncio
from typing import TypedDict

from syrin.budget.exceptions import BudgetAllocationError


class _AgentEntry(TypedDict):
    """Per-agent allocation record."""

    allocated: float
    spent: float


class BudgetPool:
    """Async-safe shared budget pool with optional per-agent caps.

    Attributes:
        total: Total pool size in USD.
        per_agent_max: Maximum any single agent may allocate, or ``None`` for
            no per-agent cap.

    Example::

        pool = BudgetPool(total=10.00, per_agent_max=3.00)
        await pool.allocate("agent-1", 2.00)
        await pool.spend("agent-1", 1.50)
        await pool.return_unused("agent-1")
        snap = pool.snapshot()
    """

    def __init__(
        self,
        total: float,
        per_agent_max: float | None = None,
    ) -> None:
        """Create a BudgetPool.

        Args:
            total: Total pool size in USD.  Must be non-negative.
            per_agent_max: Maximum any single agent may allocate.  Must be
                non-negative when provided.

        Raises:
            ValueError: If ``total`` or ``per_agent_max`` is negative.
        """
        if total < 0:
            raise ValueError(f"BudgetPool.total must be non-negative, got {total}")
        if per_agent_max is not None and per_agent_max < 0:
            raise ValueError(f"BudgetPool.per_agent_max must be non-negative, got {per_agent_max}")

        self._total = total
        self._per_agent_max = per_agent_max
        # Remaining = total - sum(allocations)
        self._allocated_total: float = 0.0
        self._entries: dict[str, _AgentEntry] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    # ──────────────────────────────────────────────────────────────────────────
    # Properties
    # ──────────────────────────────────────────────────────────────────────────

    @property
    def total(self) -> float:
        """Total pool size in USD."""
        return self._total

    @property
    def per_agent_max(self) -> float | None:
        """Maximum any single agent may allocate, or ``None``."""
        return self._per_agent_max

    @property
    def remaining(self) -> float:
        """Remaining unallocated balance in USD (never negative)."""
        return max(0.0, self._total - self._allocated_total)

    # ──────────────────────────────────────────────────────────────────────────
    # Mutations (all protected by asyncio.Lock)
    # ──────────────────────────────────────────────────────────────────────────

    async def allocate(self, agent_id: str, amount: float) -> None:
        """Atomically reserve *amount* USD for *agent_id*.

        Args:
            agent_id: Unique identifier for the agent.
            amount: Amount to allocate in USD.

        Raises:
            BudgetAllocationError: If the agent is already allocated, the amount
                exceeds ``per_agent_max``, or the pool has insufficient balance.
        """
        async with self._lock:
            if agent_id in self._entries:
                raise BudgetAllocationError(
                    f"Agent '{agent_id}' already has an active allocation.",
                    agent_id=agent_id,
                    amount=amount,
                    reason="already_allocated",
                )
            if self._per_agent_max is not None and amount > self._per_agent_max:
                raise BudgetAllocationError(
                    f"Requested {amount:.4f} exceeds per_agent_max {self._per_agent_max:.4f}.",
                    agent_id=agent_id,
                    amount=amount,
                    reason="per_agent_max",
                )
            if amount > self.remaining:
                raise BudgetAllocationError(
                    f"Requested {amount:.4f} exceeds pool remaining {self.remaining:.4f}.",
                    agent_id=agent_id,
                    amount=amount,
                    reason="insufficient_pool",
                )
            self._entries[agent_id] = {"allocated": amount, "spent": 0.0}
            self._allocated_total += amount

    async def spend(self, agent_id: str, amount: float) -> None:
        """Record *amount* USD spent by *agent_id*.

        Args:
            agent_id: Agent that incurred the cost.
            amount: Amount spent in USD.

        Raises:
            BudgetAllocationError: If the agent has no active allocation.
        """
        async with self._lock:
            if agent_id not in self._entries:
                raise BudgetAllocationError(
                    f"Agent '{agent_id}' has no active allocation.",
                    agent_id=agent_id,
                    amount=amount,
                    reason="not_allocated",
                )
            self._entries[agent_id]["spent"] += amount

    async def return_unused(self, agent_id: str) -> None:
        """Return unspent allocation from *agent_id* back to the pool.

        Calculates unspent = allocated − spent and adds it back to the pool's
        available balance.  Clears the allocation so the agent may be
        re-allocated later.

        Args:
            agent_id: Agent whose unused allocation to return.
        """
        async with self._lock:
            entry = self._entries.pop(agent_id, None)
            if entry is None:
                return
            unspent = max(0.0, entry["allocated"] - entry["spent"])
            # Only return the *unspent* portion; spent money stays consumed.
            self._allocated_total -= unspent
            # Ensure we don't go below zero due to floating-point drift
            self._allocated_total = max(0.0, self._allocated_total)

    def snapshot(self) -> dict[str, _AgentEntry]:
        """Return a point-in-time snapshot of all agent allocations.

        Returns:
            Dict mapping agent ID → ``{"allocated": float, "spent": float}``.
            The dict is a shallow copy — safe to inspect without locking.
        """
        return {
            k: {"allocated": v["allocated"], "spent": v["spent"]} for k, v in self._entries.items()
        }
