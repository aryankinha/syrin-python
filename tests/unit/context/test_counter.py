"""Tests for TokenCounter and context breakdown (Step 3)."""

from __future__ import annotations

from syrin.context.counter import TokenCounter
from syrin.context.snapshot import ContextBreakdown

# =============================================================================
# count_breakdown — valid cases
# =============================================================================


class TestTokenCounterCountBreakdown:
    """TokenCounter.count_breakdown returns ContextBreakdown by component."""

    def test_count_breakdown_all_zero(self) -> None:
        """When nothing is present and tokens_used=0, all components are 0."""
        counter = TokenCounter()
        b = counter.count_breakdown(
            system_prompt="",
            memory_context="",
            tools=[],
            tokens_used=0,
        )
        assert isinstance(b, ContextBreakdown)
        assert b.system_tokens == 0
        assert b.tools_tokens == 0
        assert b.memory_tokens == 0
        assert b.messages_tokens == 0
        assert b.total_tokens == 0

    def test_count_breakdown_system_only(self) -> None:
        """System prompt only; messages_tokens derived from tokens_used."""
        counter = TokenCounter()
        system = "You are a helpful assistant."
        system_tokens = counter.count(system) + counter._role_overhead("system")
        b = counter.count_breakdown(
            system_prompt=system,
            memory_context="",
            tools=[],
            tokens_used=system_tokens,
        )
        assert b.system_tokens == system_tokens
        assert b.tools_tokens == 0
        assert b.memory_tokens == 0
        assert b.messages_tokens == 0
        assert b.total_tokens == system_tokens

    def test_count_breakdown_tools_only(self) -> None:
        """Tools only; other components zero."""
        counter = TokenCounter()
        tools = [{"name": "foo", "description": "A tool", "parameters": {}}]
        tools_tokens = counter.count_tools(tools)
        b = counter.count_breakdown(
            system_prompt="",
            memory_context="",
            tools=tools,
            tokens_used=tools_tokens,
        )
        assert b.system_tokens == 0
        assert b.tools_tokens == tools_tokens
        assert b.tools_tokens > 0
        assert b.memory_tokens == 0
        assert b.messages_tokens == 0
        assert b.total_tokens == tools_tokens

    def test_count_breakdown_memory_only(self) -> None:
        """Memory context only."""
        counter = TokenCounter()
        memory = "User prefers Python."
        memory_block = f"[Memory]\n{memory}"
        memory_tokens = counter.count(memory_block) + counter._role_overhead("system")
        b = counter.count_breakdown(
            system_prompt="",
            memory_context=memory,
            tools=[],
            tokens_used=memory_tokens,
        )
        assert b.system_tokens == 0
        assert b.tools_tokens == 0
        assert b.memory_tokens == memory_tokens
        assert b.messages_tokens == 0
        assert b.total_tokens == memory_tokens

    def test_count_breakdown_messages_only(self) -> None:
        """Only conversation messages; system/memory/tools zero."""
        counter = TokenCounter()
        tokens_used = 50
        b = counter.count_breakdown(
            system_prompt="",
            memory_context="",
            tools=[],
            tokens_used=tokens_used,
        )
        assert b.system_tokens == 0
        assert b.tools_tokens == 0
        assert b.memory_tokens == 0
        assert b.messages_tokens == tokens_used
        assert b.total_tokens == tokens_used

    def test_count_breakdown_combined(self) -> None:
        """System + tools + memory + messages; total matches tokens_used."""
        counter = TokenCounter()
        system = "You are helpful."
        memory = "User likes cats."
        tools = [{"name": "search", "parameters": {}}]
        system_tokens = counter.count(system) + counter._role_overhead("system")
        memory_tokens = counter.count(f"[Memory]\n{memory}") + counter._role_overhead("system")
        tools_tokens = counter.count_tools(tools)
        messages_tokens = 100
        tokens_used = system_tokens + memory_tokens + tools_tokens + messages_tokens
        b = counter.count_breakdown(
            system_prompt=system,
            memory_context=memory,
            tools=tools,
            tokens_used=tokens_used,
        )
        assert b.system_tokens == system_tokens
        assert b.tools_tokens == tools_tokens
        assert b.memory_tokens == memory_tokens
        assert b.messages_tokens == messages_tokens
        assert b.total_tokens == tokens_used
        assert b.total_tokens == (
            b.system_tokens + b.tools_tokens + b.memory_tokens + b.messages_tokens
        )

    def test_count_breakdown_total_equals_tokens_used_when_no_other_components(self) -> None:
        """When only messages (no system/memory/tools), breakdown.total_tokens equals tokens_used."""
        counter = TokenCounter()
        for tokens_used in (0, 1, 100, 10_000):
            b = counter.count_breakdown(
                system_prompt="",
                memory_context="",
                tools=[],
                tokens_used=tokens_used,
            )
            assert b.total_tokens == tokens_used


# =============================================================================
# count_breakdown — edge cases
# =============================================================================


class TestTokenCounterCountBreakdownEdgeCases:
    """Edge cases: residual messages_tokens, empty inputs, rounding."""

    def test_count_breakdown_messages_residual_nonnegative(self) -> None:
        """When tokens_used < system+memory+tools, messages_tokens is 0 (no negative)."""
        counter = TokenCounter()
        system = "A" * 100
        system_tokens = counter.count(system) + counter._role_overhead("system")
        # tokens_used less than system alone
        tokens_used = max(0, system_tokens - 10)
        b = counter.count_breakdown(
            system_prompt=system,
            memory_context="",
            tools=[],
            tokens_used=tokens_used,
        )
        assert b.messages_tokens >= 0
        assert b.system_tokens == system_tokens
        # messages_tokens should be 0 when tokens_used < system_tokens
        assert b.messages_tokens == max(0, tokens_used - system_tokens)

    def test_count_breakdown_empty_tools_list(self) -> None:
        """tools=[] yields tools_tokens=0."""
        counter = TokenCounter()
        b = counter.count_breakdown(
            system_prompt="",
            memory_context="",
            tools=[],
            tokens_used=10,
        )
        assert b.tools_tokens == 0
        assert b.messages_tokens == 10

    def test_count_breakdown_empty_system_and_memory(self) -> None:
        """Empty system and memory; all tokens go to messages."""
        counter = TokenCounter()
        b = counter.count_breakdown(
            system_prompt="",
            memory_context="",
            tools=[],
            tokens_used=42,
        )
        assert b.system_tokens == 0
        assert b.memory_tokens == 0
        assert b.messages_tokens == 42


# =============================================================================
# count_breakdown — invalid / type usage
# =============================================================================


class TestTokenCounterCountBreakdownInvalid:
    """Invalid or boundary inputs (tokens_used negative should be handled)."""

    def test_count_breakdown_negative_tokens_used_messages_nonnegative(self) -> None:
        """If tokens_used is negative, messages_tokens is clamped to 0; total_tokens is sum of components."""
        counter = TokenCounter()
        b = counter.count_breakdown(
            system_prompt="",
            memory_context="",
            tools=[],
            tokens_used=-100,
        )
        assert b.messages_tokens == 0
        # total_tokens is the sum of components (all non-negative), so 0 for invalid input
        assert b.total_tokens == 0
