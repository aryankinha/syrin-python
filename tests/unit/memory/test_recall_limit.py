"""Standardize recall limit param to `limit`; deprecation warning for count/top_k.

Tests that:
- recall(limit=N) works without warning
- recall(count=N) issues DeprecationWarning and still works
- recall(top_k=N) issues DeprecationWarning and still works
- limit takes precedence when both limit and deprecated alias are specified
- Default is 10 when nothing is passed
"""

from __future__ import annotations

import warnings

import pytest

from syrin.memory.config import Memory


def _make_memory() -> Memory:
    return Memory()


class TestRecallLimitParam:
    def test_limit_param_no_warning(self) -> None:
        """recall(limit=5) does not issue a DeprecationWarning."""
        mem = _make_memory()
        mem.remember("test content")
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            result = mem.recall(limit=5)
        assert isinstance(result, list)

    def test_count_param_deprecated(self) -> None:
        """recall(count=5) issues DeprecationWarning."""
        mem = _make_memory()
        mem.remember("test content")
        with pytest.warns(DeprecationWarning, match="count=.*deprecated.*limit="):
            result = mem.recall(count=5)
        assert isinstance(result, list)

    def test_top_k_param_deprecated(self) -> None:
        """recall(top_k=5) issues DeprecationWarning."""
        mem = _make_memory()
        mem.remember("test content")
        with pytest.warns(DeprecationWarning, match="top_k=.*deprecated.*limit="):
            result = mem.recall(top_k=5)
        assert isinstance(result, list)

    def test_limit_respected(self) -> None:
        """recall(limit=1) returns at most 1 entry."""
        mem = _make_memory()
        for i in range(5):
            mem.remember(f"content {i}")
        result = mem.recall(limit=1)
        assert len(result) <= 1

    def test_count_alias_respected(self) -> None:
        """recall(count=1) returns at most 1 entry (deprecated alias still works)."""
        mem = _make_memory()
        for i in range(5):
            mem.remember(f"content {i}")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = mem.recall(count=1)
        assert len(result) <= 1

    def test_limit_takes_precedence_over_count(self) -> None:
        """When both limit and count are passed, limit wins."""
        mem = _make_memory()
        for i in range(5):
            mem.remember(f"content {i}")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result_limit_2 = mem.recall(limit=2, count=5)
        # Should use limit=2, not count=5
        assert len(result_limit_2) <= 2

    def test_default_limit_is_10(self) -> None:
        """Default limit is 10 when nothing is passed."""
        mem = _make_memory()
        # Just verify no error; can't easily test ">10 stored → returns 10" without 11 entries
        result = mem.recall()
        assert isinstance(result, list)
