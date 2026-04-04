"""P1-T1: HandoffContext tests.

Tests must be written first (TDD). The tests cover:
- Immutability (frozen dataclass)
- content is always a str
- data is None without output_type
- history is oldest-first
- budget_remaining is non-negative
- step_index increments correctly
- workflow_name is correct
- evolve() produces correct derived context
"""

from __future__ import annotations

import pytest

from syrin.workflow import HandoffContext


class TestHandoffContextImmutability:
    """HandoffContext is frozen and cannot be mutated after construction."""

    def test_is_immutable(self) -> None:
        """Attempting to set a field must raise FrozenInstanceError."""
        ctx = HandoffContext(content="hello")
        with pytest.raises((AttributeError, TypeError)):
            ctx.content = "mutated"  # type: ignore[misc]

    def test_hash_is_stable(self) -> None:
        """Two identical contexts must have the same hash."""
        ctx1 = HandoffContext(content="hello", step_index=0)
        ctx2 = HandoffContext(content="hello", step_index=0)
        assert hash(ctx1) == hash(ctx2)

    def test_different_contexts_different_hash(self) -> None:
        """Different content produces a different hash."""
        ctx1 = HandoffContext(content="hello")
        ctx2 = HandoffContext(content="world")
        assert hash(ctx1) != hash(ctx2)


class TestHandoffContextContent:
    """content field is always a str."""

    def test_content_is_string(self) -> None:
        """content must be a string, never None."""
        ctx = HandoffContext(content="result")
        assert isinstance(ctx.content, str)
        assert ctx.content == "result"

    def test_content_empty_string_allowed(self) -> None:
        """content may be an empty string."""
        ctx = HandoffContext(content="")
        assert ctx.content == ""

    def test_content_multiline_string(self) -> None:
        """Multi-line content is preserved verbatim."""
        text = "line 1\nline 2\nline 3"
        ctx = HandoffContext(content=text)
        assert ctx.content == text


class TestHandoffContextData:
    """data field: None without typed output, typed otherwise."""

    def test_data_defaults_to_none(self) -> None:
        """data is None when previous step has no output_type."""
        ctx = HandoffContext(content="text")
        assert ctx.data is None

    def test_data_holds_typed_output(self) -> None:
        """data holds the typed structured output from the previous step."""
        from dataclasses import dataclass

        @dataclass
        class Plan:
            steps: list[str]

        plan = Plan(steps=["step1", "step2"])
        ctx: HandoffContext[Plan] = HandoffContext(content="plan ready", data=plan)
        assert ctx.data is plan
        assert ctx.data.steps == ["step1", "step2"]

    def test_data_can_be_any_type(self) -> None:
        """data accepts any type (dict, list, custom class)."""
        ctx_dict: HandoffContext[dict[str, str]] = HandoffContext(
            content="ok", data={"key": "value"}
        )
        assert ctx_dict.data == {"key": "value"}

        ctx_list: HandoffContext[list[int]] = HandoffContext(content="ok", data=[1, 2, 3])
        assert ctx_list.data == [1, 2, 3]


class TestHandoffContextHistory:
    """history is oldest-first tuple of all previous step contents."""

    def test_history_defaults_empty(self) -> None:
        """history is empty for the first step."""
        ctx = HandoffContext(content="first")
        assert ctx.history == ()

    def test_history_is_oldest_first(self) -> None:
        """history accumulates in chronological order."""
        ctx = HandoffContext(
            content="third",
            history=("first", "second"),
        )
        assert ctx.history[0] == "first"
        assert ctx.history[1] == "second"

    def test_history_is_tuple_not_list(self) -> None:
        """history is a tuple (supports frozen dataclass semantics)."""
        ctx = HandoffContext(content="x", history=("a", "b"))
        assert isinstance(ctx.history, tuple)

    def test_evolve_appends_current_content_to_history(self) -> None:
        """Evolving context appends current content to history."""
        ctx = HandoffContext(content="step1 result", history=())
        next_ctx = ctx.evolve(
            content="step2 result",
            history=(*ctx.history, ctx.content),
            step_index=1,
        )
        assert "step1 result" in next_ctx.history
        assert next_ctx.content == "step2 result"


class TestHandoffContextBudget:
    """budget_remaining is a non-negative float."""

    def test_budget_remaining_defaults_zero(self) -> None:
        """budget_remaining defaults to 0.0 when not set."""
        ctx = HandoffContext(content="x")
        assert ctx.budget_remaining == 0.0

    def test_budget_remaining_positive(self) -> None:
        """budget_remaining accepts positive floats."""
        ctx = HandoffContext(content="x", budget_remaining=4.50)
        assert ctx.budget_remaining == 4.50

    def test_budget_remaining_zero_is_valid(self) -> None:
        """budget_remaining of exactly 0.0 is valid (budget exhausted)."""
        ctx = HandoffContext(content="x", budget_remaining=0.0)
        assert ctx.budget_remaining == 0.0


class TestHandoffContextStepIndex:
    """step_index increments correctly across steps."""

    def test_step_index_defaults_zero(self) -> None:
        """step_index defaults to 0."""
        ctx = HandoffContext(content="x")
        assert ctx.step_index == 0

    def test_step_index_is_set_correctly(self) -> None:
        """step_index reflects the index of the step that receives this context."""
        ctx = HandoffContext(content="x", step_index=3)
        assert ctx.step_index == 3

    def test_evolve_increments_step_index(self) -> None:
        """evolve() with step_index+1 correctly increments."""
        ctx = HandoffContext(content="step 0", step_index=0)
        next_ctx = ctx.evolve(content="step 1", step_index=ctx.step_index + 1)
        assert next_ctx.step_index == 1


class TestHandoffContextWorkflowName:
    """workflow_name matches the owning workflow."""

    def test_workflow_name_defaults_empty(self) -> None:
        """workflow_name defaults to empty string."""
        ctx = HandoffContext(content="x")
        assert ctx.workflow_name == ""

    def test_workflow_name_is_preserved(self) -> None:
        """workflow_name is set and preserved."""
        ctx = HandoffContext(content="x", workflow_name="research-pipeline")
        assert ctx.workflow_name == "research-pipeline"

    def test_evolve_preserves_workflow_name(self) -> None:
        """evolve() preserves workflow_name when not overridden."""
        ctx = HandoffContext(content="x", workflow_name="my-wf")
        next_ctx = ctx.evolve(content="y")
        assert next_ctx.workflow_name == "my-wf"


class TestHandoffContextEvolve:
    """evolve() returns a new frozen context with requested field changes."""

    def test_evolve_returns_new_instance(self) -> None:
        """evolve() creates a new HandoffContext, not mutating the original."""
        ctx = HandoffContext(content="original")
        next_ctx = ctx.evolve(content="modified")
        assert ctx.content == "original"
        assert next_ctx.content == "modified"

    def test_evolve_preserves_unspecified_fields(self) -> None:
        """Fields not in **changes retain their original values."""
        ctx = HandoffContext(
            content="x",
            step_index=2,
            workflow_name="wf",
            budget_remaining=5.0,
            run_id="run-123",
        )
        next_ctx = ctx.evolve(content="y")
        assert next_ctx.step_index == 2
        assert next_ctx.workflow_name == "wf"
        assert next_ctx.budget_remaining == 5.0
        assert next_ctx.run_id == "run-123"

    def test_evolve_all_fields(self) -> None:
        """All fields can be updated via evolve()."""
        ctx = HandoffContext(
            content="old",
            data=None,
            history=(),
            budget_remaining=10.0,
            step_index=0,
            workflow_name="wf",
            run_id="run-1",
        )
        next_ctx = ctx.evolve(
            content="new",
            data={"key": "val"},
            history=("old",),
            budget_remaining=9.0,
            step_index=1,
            workflow_name="wf-v2",
            run_id="run-2",
        )
        assert next_ctx.content == "new"
        assert next_ctx.data == {"key": "val"}
        assert next_ctx.history == ("old",)
        assert next_ctx.budget_remaining == 9.0
        assert next_ctx.step_index == 1
        assert next_ctx.workflow_name == "wf-v2"
        assert next_ctx.run_id == "run-2"
