"""Context compactors for automatic context management."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

from syrin.context.counter import TokenCounter, get_counter
from syrin.context.prompts import (
    DEFAULT_COMPACTION_SYSTEM_PROMPT,
    DEFAULT_COMPACTION_USER_TEMPLATE,
)
from syrin.enums import CompactionMethod

if TYPE_CHECKING:
    from syrin.model import Model


class ContextCompactorProtocol(Protocol):
    """Protocol for compactors used by DefaultContextManager.

    Context.compactor can be any object implementing this interface.
    """

    def compact(
        self,
        messages: list[dict[str, Any]],
        budget: int,
    ) -> CompactionResult:
        """Return compacted messages and metadata. budget is available token count (int)."""
        ...


@dataclass
class CompactionResult:
    """Result of a compaction operation.

    Attributes:
        messages: Compacted message list.
        method: One of CompactionMethod (none, middle_out_truncate, summarize). Use CompactionMethod(method) to compare.
        tokens_before: Token count before compaction.
        tokens_after: Token count after compaction.
    """

    messages: list[dict[str, Any]]
    method: str  # CompactionMethod value
    tokens_before: int
    tokens_after: int


class Compactor:
    """Base compactor interface. Implement compact() for custom strategies."""

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
                method=CompactionMethod.NONE,
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
            method=CompactionMethod.MIDDLE_OUT_TRUNCATE,
            tokens_before=tokens_before,
            tokens_after=tokens_after,
        )


def _format_messages_for_summary(messages: list[dict[str, Any]]) -> str:
    """Format message list as a single string for the summary prompt."""
    parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, str):
            parts.append(f"{role}: {content}")
        else:
            parts.append(f"{role}: {content!r}")
    return "\n\n".join(parts)


class Summarizer:
    """Summarizer for compacting context. Uses optional LLM when model is set; else placeholder."""

    def __init__(
        self,
        system_prompt: str | None = None,
        user_prompt_template: str | None = None,
        model: Model | None = None,
    ) -> None:
        """Initialize the summarizer.

        Args:
            system_prompt: System prompt for the summarization LLM. None = use default from prompts.py.
            user_prompt_template: User prompt template; must contain {messages}. None = default.
            model: Model to use for summarization. None = placeholder (keep system + last 4, no LLM).
        """
        self._system_prompt = (
            system_prompt if system_prompt is not None else DEFAULT_COMPACTION_SYSTEM_PROMPT
        )
        self._user_template = (
            user_prompt_template
            if user_prompt_template is not None
            else DEFAULT_COMPACTION_USER_TEMPLATE
        )
        self._model = model

    def summarize(
        self,
        messages: list[dict[str, Any]],
        counter: TokenCounter | None = None,
    ) -> list[dict[str, Any]]:
        """Summarize older messages. Uses LLM when model is set; else placeholder."""
        counter = counter or get_counter()

        system_msg: dict[str, Any] | None = None
        non_system: list[dict[str, Any]] = []

        for msg in messages:
            if msg.get("role") == "system":
                system_msg = msg
            else:
                non_system.append(msg)

        if len(non_system) <= 4:
            return messages

        recent = non_system[-4:]
        to_summarize = non_system[:-4]

        if self._model is not None:
            # LLM path: format to_summarize, call model, build result from response
            conversation_text = _format_messages_for_summary(to_summarize)
            try:
                user_content = self._user_template.format(messages=conversation_text)
            except KeyError:
                user_content = self._user_template + "\n\n" + conversation_text
            from syrin.enums import MessageRole
            from syrin.types import Message, ProviderResponse

            llm_messages = [
                Message(role=MessageRole.SYSTEM, content=self._system_prompt),
                Message(role=MessageRole.USER, content=user_content),
            ]
            # When already inside an async loop (e.g. agent run), model.complete() must not nest event loops
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop is not None:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(self._model.complete, llm_messages)
                    raw = future.result()
                    response = cast(ProviderResponse, raw)
            else:
                response = cast(ProviderResponse, self._model.complete(llm_messages))
            summary_content = (response.content or "").strip() or "[No summary generated]"
            summary_msg = {
                "role": "system",
                "content": f"[Previous conversation summary]\n{summary_content}",
            }
        else:
            summary_msg = {
                "role": "system",
                "content": f"[Previous conversation summary: {len(to_summarize)} messages omitted]",
            }

        result = [summary_msg] + recent
        if system_msg:
            result = [system_msg] + result

        return result


class ContextCompactor:
    """Default compactor that combines truncation and summarization.

    **Which method runs?** (see CompactionMethod for all values)

    1. **none** — tokens_before ≤ budget → no compaction.
    2. **middle_out_truncate** — over budget and overage (tokens_before/budget) < 1.5 → keep start/end, drop middle.
    3. **summarize** — overage ≥ 1.5 → summarize older messages (LLM if compaction_model set, else placeholder); if result still over budget, middle_out_truncate is applied (so you may see middle_out_truncate after a summarize step).

    To list all methods: ``list(CompactionMethod)`` or ``from syrin.enums import CompactionMethod; list(CompactionMethod)``.
    To force summarization: use enough messages and a small budget so overage ≥ 1.5, and > 4 non-system messages so Summarizer runs.
    """

    def __init__(
        self,
        compaction_prompt: str | None = None,
        compaction_system_prompt: str | None = None,
        compaction_model: Model | None = None,
    ) -> None:
        """Initialize the compactor.

        Args:
            compaction_prompt: User prompt template for summarization (e.g. with {messages}). None = default.
            compaction_system_prompt: System prompt for summarization. None = default from prompts.py.
            compaction_model: Model for summarization. None = placeholder (no LLM).
        """
        self._truncator = MiddleOutTruncator()
        self._summarizer = Summarizer(
            system_prompt=compaction_system_prompt,
            user_prompt_template=compaction_prompt,
            model=compaction_model,
        )
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
                method=CompactionMethod.NONE,
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
            method=CompactionMethod.SUMMARIZE,
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
