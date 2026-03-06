"""Tests for custom compaction prompt (Step 4): Summarizer, ContextCompactor, Context."""

from __future__ import annotations

from syrin.context import Context, ContextCompactor, DefaultContextManager
from syrin.context.compactors import Summarizer
from syrin.context.counter import get_counter
from syrin.context.prompts import (
    DEFAULT_COMPACTION_SYSTEM_PROMPT,
    DEFAULT_COMPACTION_USER_TEMPLATE,
)
from syrin.model import Model
from syrin.threshold import ContextThreshold

# -----------------------------------------------------------------------------
# Summarizer — valid
# -----------------------------------------------------------------------------


class TestSummarizerValid:
    """Valid cases: default prompts, custom prompts, with and without model."""

    def test_summarizer_placeholder_when_no_model(self) -> None:
        """With model=None, Summarizer uses placeholder (keeps system + last 4, summary line)."""
        s = Summarizer()
        counter = get_counter()
        messages = [{"role": "system", "content": "You are helpful."}]
        for i in range(8):
            messages.append({"role": "user", "content": f"Msg {i}"})
        out = s.summarize(messages, counter)
        assert len(out) < len(messages)
        assert any("[Previous conversation summary:" in str(m.get("content", "")) for m in out)
        # System first, then summary, then recent
        assert out[0].get("role") == "system"

    def test_summarizer_uses_default_prompts_when_none(self) -> None:
        """Summarizer(system_prompt=None, user_prompt_template=None) uses prompts.py defaults."""
        s = Summarizer(system_prompt=None, user_prompt_template=None, model=None)
        # Placeholder path: no LLM; just assert it runs and returns structure
        messages = [{"role": "user", "content": "Hi"}] * 6
        out = s.summarize(messages, get_counter())
        assert isinstance(out, list)
        assert all(isinstance(m, dict) and "role" in m and "content" in m for m in out)

    def test_summarizer_custom_prompts_no_model(self) -> None:
        """Custom system/user prompts with model=None still use placeholder behavior."""
        s = Summarizer(
            system_prompt="Custom system.",
            user_prompt_template="Condense: {messages}",
            model=None,
        )
        messages = [{"role": "user", "content": "x"}] * 6
        out = s.summarize(messages, get_counter())
        assert len(out) <= 6
        assert all("role" in m and "content" in m for m in out)

    def test_summarizer_with_model_returns_llm_summary(self) -> None:
        """When model is set (e.g. Almock), summarize() calls model and returns summary message(s)."""
        model = Model.Almock(
            response_mode="custom",
            custom_response="[Summary] Key points from the conversation.",
        )
        s = Summarizer(model=model)
        # Need > 4 non-system messages to trigger summarization (recent = last 4)
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Second question"},
            {"role": "assistant", "content": "Second answer"},
            {"role": "user", "content": "Third question"},
            {"role": "assistant", "content": "Third answer"},
        ]
        out = s.summarize(messages, get_counter())
        # Should have system + summary block + recent (last 4); summary content from model
        assert isinstance(out, list)
        assert len(out) >= 1
        contents = [m.get("content", "") for m in out]
        assert any("[Summary]" in c or "Key points" in c for c in contents)

    def test_summarizer_template_placeholder_filled_when_model_set(self) -> None:
        """User template with {messages} is filled when using model."""
        model = Model.Almock(
            response_mode="custom",
            custom_response="Brief summary of the chat.",
        )
        s = Summarizer(
            user_prompt_template="Summarize:\n{messages}",
            model=model,
        )
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        out = s.summarize(messages, get_counter())
        assert len(out) >= 1
        # No KeyError for {messages}
        assert all("role" in m for m in out)


# -----------------------------------------------------------------------------
# Summarizer — edge
# -----------------------------------------------------------------------------


class TestSummarizerEdge:
    """Edge cases: empty messages, few messages, only system."""

    def test_summarizer_empty_messages(self) -> None:
        """Empty message list returns empty or minimal list."""
        s = Summarizer()
        out = s.summarize([], get_counter())
        assert out == [] or (len(out) == 1 and out[0].get("role") == "system")

    def test_summarizer_few_messages_no_summary(self) -> None:
        """When non-system messages <= 4, summarizer returns messages unchanged (no summary)."""
        s = Summarizer()
        messages = [
            {"role": "system", "content": "Sys"},
            {"role": "user", "content": "A"},
            {"role": "assistant", "content": "B"},
        ]
        out = s.summarize(messages, get_counter())
        assert out == messages

    def test_summarizer_only_system_messages(self) -> None:
        """Only system messages: return as-is or single system."""
        s = Summarizer()
        messages = [
            {"role": "system", "content": "A"},
            {"role": "system", "content": "B"},
        ]
        out = s.summarize(messages, get_counter())
        assert len(out) <= 2
        assert all(m.get("role") == "system" for m in out)


# -----------------------------------------------------------------------------
# Summarizer — invalid / template
# -----------------------------------------------------------------------------


class TestSummarizerInvalid:
    """Invalid or risky template usage."""

    def test_summarizer_template_missing_placeholder_raises_or_uses_safe(self) -> None:
        """Template without {messages} should not break; implementation may use safe format."""
        model = Model.Almock(response_mode="custom", custom_response="OK")
        s = Summarizer(
            user_prompt_template="Just summarize.",  # no {messages}
            model=model,
        )
        messages = [{"role": "user", "content": "Hi"}] * 5
        # Either raises or uses conversation text elsewhere; no silent wrong behavior
        out = s.summarize(messages, get_counter())
        assert isinstance(out, list)


# -----------------------------------------------------------------------------
# ContextCompactor with compaction params
# -----------------------------------------------------------------------------


class TestContextCompactorCompactionParams:
    """ContextCompactor accepts compaction_prompt, compaction_system_prompt, compaction_model."""

    def test_compactor_default_no_compaction_params(self) -> None:
        """ContextCompactor() with no args works as before (no compaction_*)."""
        compactor = ContextCompactor()
        messages = [{"role": "user", "content": "Hi"}]
        result = compactor.compact(messages, 10000)
        assert result.method == "none"

    def test_compactor_with_compaction_prompt_and_model(self) -> None:
        """ContextCompactor(compaction_prompt=..., compaction_model=...) uses them when summarizing."""
        model = Model.Almock(
            response_mode="custom",
            custom_response="Compacted summary.",
        )
        compactor = ContextCompactor(
            compaction_prompt="Short summary: {messages}",
            compaction_model=model,
        )
        # Budget 500 is small; need overage >= 1.5 to trigger summarize (else middle-out)
        messages = [{"role": "system", "content": "Sys"}]
        for i in range(50):
            messages.append({"role": "user", "content": f"Message {i} " + "x" * 100})
        result = compactor.compact(messages, 500)
        assert result.method == "summarize"
        assert result.tokens_after < result.tokens_before
        assert len(result.messages) < len(messages)

    def test_compactor_compaction_system_prompt_override(self) -> None:
        """ContextCompactor(compaction_system_prompt=...) passes to Summarizer."""
        model = Model.Almock(response_mode="custom", custom_response="Done.")
        compactor = ContextCompactor(
            compaction_system_prompt="You are a compressor.",
            compaction_model=model,
        )
        messages = [{"role": "user", "content": "y" * 200}] * 25
        result = compactor.compact(messages, 400)
        assert result.method == "summarize"


# -----------------------------------------------------------------------------
# Context config
# -----------------------------------------------------------------------------


class TestContextCompactionConfig:
    """Context.compaction_prompt, compaction_system_prompt, compaction_model."""

    def test_context_has_compaction_fields(self) -> None:
        """Context accepts compaction_prompt, compaction_system_prompt, compaction_model."""
        ctx = Context(
            max_tokens=8000,
            compaction_prompt="Summarize: {messages}",
            compaction_model=None,
        )
        assert ctx.compaction_prompt == "Summarize: {messages}"
        assert ctx.compaction_model is None

    def test_context_compaction_system_prompt(self) -> None:
        """Context.compaction_system_prompt is optional."""
        ctx = Context(
            max_tokens=8000,
            compaction_system_prompt="You are a summarizer.",
        )
        assert ctx.compaction_system_prompt == "You are a summarizer."

    def test_context_apply_uses_compaction_model_when_set(self) -> None:
        """Context.apply() with compaction_model uses it for default compactor."""
        model = Model.Almock(response_mode="custom", custom_response="Summary.")
        ctx = Context(
            max_tokens=8000,
            compaction_model=model,
        )
        messages = [{"role": "system", "content": "S"}]
        for i in range(40):
            messages.append({"role": "user", "content": f"M{i} " + "a" * 150})
        out = ctx.apply(messages, max_tokens=600)
        assert isinstance(out, list)
        assert len(out) < len(messages)


# -----------------------------------------------------------------------------
# DefaultContextManager wiring
# -----------------------------------------------------------------------------


class TestManagerCompactionWiring:
    """DefaultContextManager builds compactor from Context.compaction_*."""

    def test_manager_uses_context_compaction_model_when_no_custom_compactor(self) -> None:
        """When context.compactor is None, manager uses ContextCompactor with context's compaction_*."""
        model = Model.Almock(response_mode="custom", custom_response="Summarized.")
        ctx = Context(
            max_tokens=3000,
            thresholds=[
                ContextThreshold(at=50, action=lambda evt: evt.compact() if evt.compact else None)
            ],
            compaction_model=model,
        )
        manager = DefaultContextManager(ctx)
        messages = [{"role": "system", "content": "System"}]
        for i in range(40):
            messages.append({"role": "user", "content": f"Message {i} " + "y" * 120})
        payload = manager.prepare(
            messages=messages,
            system_prompt="You are helpful.",
            tools=[],
            memory_context="",
        )
        # Compaction should have run (threshold 50%), and summarization used model
        assert manager.stats.compacted is True
        assert payload.tokens > 0
        assert len(payload.messages) < len(messages)


# -----------------------------------------------------------------------------
# Prompts module
# -----------------------------------------------------------------------------


class TestPromptsModule:
    """Default compaction prompts are non-empty and contain expected placeholders."""

    def test_default_system_prompt_non_empty(self) -> None:
        assert DEFAULT_COMPACTION_SYSTEM_PROMPT
        assert "summar" in DEFAULT_COMPACTION_SYSTEM_PROMPT.lower()

    def test_default_user_template_has_messages_placeholder(self) -> None:
        assert "{messages}" in DEFAULT_COMPACTION_USER_TEMPLATE
