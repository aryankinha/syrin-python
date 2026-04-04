"""Benchmark: authority validation adds ≤1ms overhead per control call.

Exit criteria: Authority validation adds ≤1ms overhead per control call (benchmark).
"""

from __future__ import annotations

import time

from syrin.enums import AgentPermission, AgentRole
from syrin.swarm._authority import SwarmAuthorityGuard

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_guard() -> SwarmAuthorityGuard:
    return SwarmAuthorityGuard(
        roles={
            "sup": AgentRole.SUPERVISOR,
            "w1": AgentRole.WORKER,
            "w2": AgentRole.WORKER,
        },
        teams={"sup": ["w1", "w2"]},
    )


# ---------------------------------------------------------------------------
# Benchmark: ≤1ms per permission check
# ---------------------------------------------------------------------------


def test_authority_check_under_1ms() -> None:
    """Single permission check completes in <1ms (≤1ms overhead target)."""
    guard = _make_guard()

    # Warm up JIT / caches
    for _ in range(10):
        guard.check("sup", AgentPermission.CONTROL, "w1")

    iterations = 1000
    start = time.perf_counter()
    for _ in range(iterations):
        guard.check("sup", AgentPermission.CONTROL, "w1")
    elapsed = time.perf_counter() - start

    avg_ms = (elapsed / iterations) * 1000
    assert avg_ms <= 1.0, f"Authority check took {avg_ms:.4f}ms on average — must be ≤1ms"


def test_authority_require_under_1ms_on_grant() -> None:
    """require() on a granted permission completes in <1ms."""
    guard = _make_guard()

    # Warm up
    for _ in range(10):
        guard.require("sup", AgentPermission.CONTROL, "w1")

    iterations = 1000
    start = time.perf_counter()
    for _ in range(iterations):
        guard.require("sup", AgentPermission.CONTROL, "w1")
    elapsed = time.perf_counter() - start

    avg_ms = (elapsed / iterations) * 1000
    assert avg_ms <= 1.0, f"Authority require() took {avg_ms:.4f}ms on average — must be ≤1ms"


def test_authority_check_denial_under_1ms() -> None:
    """Permission denial check (no raise) also stays under 1ms."""
    guard = _make_guard()

    # Warm up
    for _ in range(10):
        guard.check("w1", AgentPermission.ADMIN, "w2")

    iterations = 1000
    start = time.perf_counter()
    for _ in range(iterations):
        result = guard.check("w1", AgentPermission.ADMIN, "w2")
        assert result is False
    elapsed = time.perf_counter() - start

    avg_ms = (elapsed / iterations) * 1000
    assert avg_ms <= 1.0, f"Authority denial check took {avg_ms:.4f}ms on average — must be ≤1ms"
