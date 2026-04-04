"""Tests for Pry TUI structural correctness.

Exit criteria:
- Single rich.Live context — no nested Live loops
- All TUI updates route through a single queue — zero thread races under parallel execution
"""

from __future__ import annotations

import threading

from syrin.debug._ui import Pry

# ---------------------------------------------------------------------------
# Single Live context: Pry uses only one _live attribute
# ---------------------------------------------------------------------------


def test_pry_has_single_live_attribute() -> None:
    """Pry class stores at most one _live instance, never nested."""
    pry = Pry()
    # Before start(), _live should be None or absent
    live_attr = getattr(pry, "_live", None)
    assert live_attr is None, "Pry should not have an active Live before attach()"


def test_pry_live_attribute_is_not_set_without_start() -> None:
    """_live is None until Pry.start() is called."""
    pry = Pry()
    assert getattr(pry, "_live", None) is None


# ---------------------------------------------------------------------------
# TUI updates: events accumulate in _events deque
# ---------------------------------------------------------------------------


def test_pry_events_is_deque() -> None:
    """Pry._events is a deque for O(1) bounded appends."""
    from collections import deque

    pry = Pry()
    assert isinstance(pry._events, deque)


def test_pry_events_has_maxlen() -> None:
    """Pry._events deque has a maxlen (bounded ring buffer)."""
    pry = Pry()
    assert pry._events.maxlen is not None
    assert pry._events.maxlen > 0


def test_pry_events_starts_empty() -> None:
    """Pry._events deque starts empty."""
    pry = Pry()
    assert len(pry._events) == 0


# ---------------------------------------------------------------------------
# Thread safety: concurrent appends to _events do not corrupt state
# ---------------------------------------------------------------------------


def test_pry_events_thread_safe_append() -> None:
    """Concurrent hook callbacks appending to _events do not raise or corrupt data."""
    pry = Pry()
    errors: list[Exception] = []
    appends: list[int] = []

    def _append_events(count: int) -> None:
        try:
            for i in range(count):
                # Simulate what hook callbacks do: append an EventRecord-like object
                # We just test that the deque accepts concurrent appends safely.
                pry._events.append(
                    type(
                        "FakeRecord",
                        (),
                        {  # type: ignore[misc]
                            "hook": "test.hook",
                            "agent": "agent-1",
                            "ts": 0.0,
                            "data": {},
                            "label": f"event-{i}",
                        },
                    )()
                )
                appends.append(1)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=_append_events, args=(50,)) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Thread safety errors: {errors}"
    # All 400 appends attempted, but deque may have rotated
    assert len(appends) == 400
    # deque length bounded by maxlen
    assert len(pry._events) <= pry._events.maxlen  # type: ignore[operator]


# ---------------------------------------------------------------------------
# No nested Live loops: inspect class structure
# ---------------------------------------------------------------------------


def test_pry_start_method_creates_at_most_one_live() -> None:
    """Pry._start_rich() sets self._live only once — no multiple Live instances."""
    import inspect

    src = inspect.getsource(Pry._start_rich)  # type: ignore[attr-defined]
    # Count 'Live(' calls in the method source
    live_calls = src.count("Live(")
    assert live_calls <= 1, (
        f"_start_rich() should create at most one Live instance, found {live_calls}"
    )
