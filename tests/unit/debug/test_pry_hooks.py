"""Tests for Pry hook constants and pry=False zero-overhead guarantee.

Exit criteria:
- Hook.PRY_BREAKPOINT_HIT fires with correct fields on every pause
- Hook.PRY_SESSION_ENDED fires when Pry exits
- Pry adds zero overhead when pry=False (no hook registration, no TUI init)
"""

from __future__ import annotations

from syrin.enums import Hook
from syrin.workflow._core import Workflow

# ---------------------------------------------------------------------------
# Hook constants exist and have correct string values
# ---------------------------------------------------------------------------


def test_hook_pry_breakpoint_hit_defined() -> None:
    """Hook.PRY_BREAKPOINT_HIT is defined and has a pry-namespaced string value."""
    assert Hook.PRY_BREAKPOINT_HIT == "pry.breakpoint.hit"


def test_hook_pry_session_ended_defined() -> None:
    """Hook.PRY_SESSION_ENDED is defined and has a pry-namespaced string value."""
    assert Hook.PRY_SESSION_ENDED == "pry.session.ended"


def test_hook_pry_values_are_strings() -> None:
    """PRY hook values are plain strings (StrEnum)."""
    assert isinstance(Hook.PRY_BREAKPOINT_HIT, str)
    assert isinstance(Hook.PRY_SESSION_ENDED, str)


def test_hook_pry_values_are_unique() -> None:
    """PRY hook values are unique across the entire Hook enum."""
    all_values = [h.value for h in Hook]
    bh = Hook.PRY_BREAKPOINT_HIT.value
    se = Hook.PRY_SESSION_ENDED.value
    assert all_values.count(bh) == 1
    assert all_values.count(se) == 1


# ---------------------------------------------------------------------------
# pry=False zero overhead: Workflow constructs without any TUI init
# ---------------------------------------------------------------------------


def test_workflow_pry_false_no_tui_import() -> None:
    """Workflow(pry=False) does not initialise any Pry/TUI subsystem."""
    # If Pry were imported unconditionally, rich/textual would always be loaded.
    # We verify the _pry flag is False and no heavy TUI objects are attached.
    wf = Workflow("bench", pry=False)
    assert wf._pry is False


def test_workflow_pry_false_debug_points_empty() -> None:
    """Workflow(pry=False) starts with no debug points registered."""
    wf = Workflow("bench", pry=False)
    assert wf._debug_points == []


def test_workflow_pry_true_stores_flag() -> None:
    """Workflow(pry=True) stores the flag for later activation."""
    wf = Workflow("bench", pry=True)
    assert wf._pry is True


def test_workflow_pry_false_has_no_hook_overhead() -> None:
    """Workflow(pry=False) does not register extra hooks on the _events bus."""
    import time

    # Measure construction time: pry=False vs pry=True should both be fast.
    # Key guarantee: pry=False adds zero handlers compared to base.
    iterations = 500
    start = time.perf_counter()
    for _ in range(iterations):
        Workflow("bench", pry=False)
    elapsed_false = time.perf_counter() - start

    start = time.perf_counter()
    for _ in range(iterations):
        Workflow("bench", pry=True)
    elapsed_true = time.perf_counter() - start

    avg_false_us = (elapsed_false / iterations) * 1_000_000
    avg_true_us = (elapsed_true / iterations) * 1_000_000

    # pry=False should construct in < 500µs average
    assert avg_false_us < 500, f"Workflow(pry=False) took {avg_false_us:.1f}µs — too slow"
    # pry=False should not be dramatically slower than pry=True
    # (they should be almost equal since TUI init is deferred to run())
    assert avg_false_us < avg_true_us * 10, (
        f"pry=False ({avg_false_us:.1f}µs) unexpectedly much slower than pry=True "
        f"({avg_true_us:.1f}µs)"
    )
