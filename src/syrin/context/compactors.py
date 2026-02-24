"""Context compactors for automatic context management."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from syrin.context.counter import TokenCounter, get_counter


class ContextCompactorProtocol(Protocol):
    """Protocol for compactors used by DefaultContextManager.

    Context.compactor can be any object implementing this interface.
    """

    def compact(
        self,
        messages: list[dict[str, Any]],
        budget: int,
    ) -> "CompactionResult":
        """Return compacted messages and metadata. budget is available token count (int)."""
        ...


@dataclass
class CompactionResult:
    """Result of a compaction operation."""

    messages: list[dict[str, Any]]
    method: str
    tokens_before: int
    tokens_after: int


class Compactor:
    """Base compactor interface."""

    def compact(
        self,
        messages: list[dict[str, Any]],
        budget: int,
        counter: TokenCounter | None = None,
    ) -> CompactionResult:
        """Compact messages to fit within budget."""
        raise NotImplementedError


class MiddleOutTruncator(Compactor):
    """Keep start and end of conversation, truncate middle.

    This is based on research showing LLMs have better recall
    at the beginning and end of context (the " primacy" and "recency" effect).
    """

    def compact(
        self,
        messages: list[dict[str, Any]],
        budget: int,
        counter: TokenCounter | None = None,
    ) -> CompactionResult:
        """Truncate middle messages while keeping start and end."""
        counter = counter or get_counter()

        tokens_before = counter.count_messages(messages).total

        if tokens_before <= budget:
            return CompactionResult(
                messages=messages,
                method="none",
                tokens_before=tokens_before,
                tokens_after=tokens_before,
            )

        system_msg = None
        non_system = []

        for msg in messages:
            role = msg.get("role")
            if role == "system":
                system_msg = msg
            else:
                non_system.append(msg)

        kept_messages = [msg for msg in non_system if msg.get("role") == "system"]
        non_system = [msg for msg in non_system if msg.get("role") != "system"]

        if system_msg:
            kept_messages.append(system_msg)

        head_size = len(non_system) // 3
        tail_size = len(non_system) - head_size

        head = non_system[:head_size] if head_size > 0 else []
        tail = non_system[-tail_size:] if tail_size > 0 else []

        result_messages = kept_messages + head + tail

        tokens_after = counter.count_messages(result_messages).total

        if tokens_after > budget and len(head) > 1:
            head = head[:-1]
            result_messages = kept_messages + head + tail
            tokens_after = counter.count_messages(result_messages).total

        if tokens_after > budget and len(tail) > 1:
            tail = tail[1:]
            result_messages = kept_messages + head + tail
            tokens_after = counter.count_messages(result_messages).total

        return CompactionResult(
            messages=result_messages,
            method="middle_out_truncate",
            tokens_before=tokens_before,
            tokens_after=tokens_after,
        )


class Summarizer:
    """Summarizer for compacting context via LLM.

    This is a placeholder - in production this would call an LLM
    to summarize older messages.
    """

    def __init__(self, summarize_fn: Callable[[list[dict[str, Any]]], str] | None = None):
        self._summarize_fn = summarize_fn

    def summarize(
        self,
        messages: list[dict[str, Any]],
        counter: TokenCounter | None = None,
    ) -> list[dict[str, Any]]:
        """Summarize older messages.

        In a full implementation, this would use an LLM to generate
        a summary of the conversation history.

        For now, this is a placeholder that keeps system + recent messages.
        """
        counter = counter or get_counter()

        system_msg = None
        non_system = []

        for msg in messages:
            if msg.get("role") == "system":
                system_msg = msg
            else:
                non_system.append(msg)

        if len(non_system) <= 4:
            return messages

        recent = non_system[-4:]
        summary_msg = {
            "role": "system",
            "content": f"[Previous conversation summary: {len(non_system) - 4} messages omitted]",
        }

        result = [summary_msg] + recent
        if system_msg:
            result = [system_msg] + result

        return result


class ContextCompactor:
    """Default compactor that combines truncation and summarization.

    Strategy:
    1. If messages slightly over budget, use middle-out truncation
    2. If significantly over budget, summarize older messages
    3. As last resort, aggressive truncation
    """

    def __init__(
        self,
        summarize_fn: Callable[[list[dict[str, Any]]], str] | None = None,
    ):
        self._truncator = MiddleOutTruncator()
        self._summarizer = Summarizer(summarize_fn)
        self._counter = get_counter()

    def compact(
        self,
        messages: list[dict[str, Any]],
        budget: int,
    ) -> CompactionResult:
        """Compact messages to fit within budget."""
        tokens_before = self._counter.count_messages(messages).total

        if tokens_before <= budget:
            return CompactionResult(
                messages=messages,
                method="none",
                tokens_before=tokens_before,
                tokens_after=tokens_before,
            )

        overage = tokens_before / budget
        if overage < 1.5:
            result = self._truncator.compact(messages, budget, self._counter)
            result.tokens_before = tokens_before
            return result

        summarized = self._summarizer.summarize(messages, self._counter)
        tokens_after = self._counter.count_messages(summarized).total

        if tokens_after > budget:
            result = self._truncator.compact(summarized, budget, self._counter)
            result.tokens_before = tokens_before
            return result

        return CompactionResult(
            messages=summarized,
            method="summarize",
            tokens_before=tokens_before,
            tokens_after=tokens_after,
        )


__all__ = [
    "Compactor",
    "CompactionResult",
    "ContextCompactor",
    "ContextCompactorProtocol",
    "MiddleOutTruncator",
    "Summarizer",
]
