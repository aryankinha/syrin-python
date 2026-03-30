"""tiktoken.encode() caching for token counter.

Tests that:
- Repeated calls with the same text return consistent results
- Cache hits don't call encode() again (mocked tiktoken)
- Different texts are handled correctly
"""

from __future__ import annotations

import pytest

from syrin.context.counter import TokenCounter


class TestTokenCounterCaching:
    def test_same_text_counted_consistently(self) -> None:
        """Repeated count() calls with same text return same result."""
        counter = TokenCounter()
        text = "Hello, world! " * 50
        r1 = counter.count(text)
        r2 = counter.count(text)
        assert r1 == r2

    def test_different_texts_counted_differently(self) -> None:
        """Different texts produce different counts."""
        counter = TokenCounter()
        r1 = counter.count("short text")
        r2 = counter.count("much longer text with many more tokens " * 10)
        assert r2 > r1

    def test_encode_called_fewer_times_with_cache(self) -> None:
        """With caching, repeated encode() is not called multiple times for same text."""
        # This tests that the implementation uses a cache by checking
        # the encode call count is lower than the number of count() calls
        call_count = 0
        original_encode = None

        try:
            import tiktoken as _tiktoken

            enc = _tiktoken.get_encoding("cl100k_base")
            original_encode = enc.encode

            def counting_encode(text: str, **kwargs: object) -> list[int]:
                nonlocal call_count
                call_count += 1
                return original_encode(text, **kwargs)  # type: ignore[misc]

            enc.encode = counting_encode  # type: ignore[method-assign]
        except ImportError:
            pytest.skip("tiktoken not available")

        counter = TokenCounter()
        text = "This is a test sentence for caching."

        # Count the same text 5 times
        for _ in range(5):
            counter.count(text)

        # With a cache, encode should be called at most once (or once per cache miss)
        # Without cache, it would be called 5 times
        assert call_count <= 1, (
            f"encode() was called {call_count} times for 5 identical count() calls; "
            "caching should reduce this to 1 call (cache miss on first, hits on rest)"
        )

    def test_empty_string_handled(self) -> None:
        """Empty string returns 0 tokens."""
        counter = TokenCounter()
        assert counter.count("") == 0

    def test_cache_persists_across_counter_instances(self) -> None:
        """Module-level cache is shared across TokenCounter instances."""
        # Both counters should use the same encoding cache
        c1 = TokenCounter()
        c2 = TokenCounter()
        text = "Shared text for caching test"
        r1 = c1.count(text)
        r2 = c2.count(text)
        assert r1 == r2
