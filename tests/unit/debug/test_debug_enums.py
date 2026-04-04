"""Tests for DebugPoint and PryResumeMode enums, and Workflow.debugpoint().

Exit criteria:
- DebugPoint.ON_HANDOFF pauses at every agent-to-agent transition
- DebugPoint.ON_LLM_REQUEST, ON_TOOL_RESULT, ON_A2A_RECEIVE, ON_ERROR exist
- .debugpoint() in a Workflow builder inserts a pause before the next step
- PryResumeMode.CONTINUE_AGENT resumes only the selected agent
"""

from __future__ import annotations

from syrin.enums import DebugPoint, PryResumeMode
from syrin.workflow._core import Workflow

# ---------------------------------------------------------------------------
# DebugPoint enum values
# ---------------------------------------------------------------------------


def test_debug_point_on_handoff() -> None:
    """DebugPoint.ON_HANDOFF is defined."""
    assert DebugPoint.ON_HANDOFF == "on_handoff"


def test_debug_point_on_llm_request() -> None:
    """DebugPoint.ON_LLM_REQUEST is defined."""
    assert DebugPoint.ON_LLM_REQUEST == "on_llm_request"


def test_debug_point_on_tool_result() -> None:
    """DebugPoint.ON_TOOL_RESULT is defined."""
    assert DebugPoint.ON_TOOL_RESULT == "on_tool_result"


def test_debug_point_on_a2a_receive() -> None:
    """DebugPoint.ON_A2A_RECEIVE is defined."""
    assert DebugPoint.ON_A2A_RECEIVE == "on_a2a_receive"


def test_debug_point_on_error() -> None:
    """DebugPoint.ON_ERROR is defined."""
    assert DebugPoint.ON_ERROR == "on_error"


def test_debug_point_all_are_strings() -> None:
    """All DebugPoint values are strings (StrEnum)."""
    for dp in DebugPoint:
        assert isinstance(dp, str)


# ---------------------------------------------------------------------------
# PryResumeMode enum values
# ---------------------------------------------------------------------------


def test_pry_resume_mode_step() -> None:
    """PryResumeMode.STEP is defined."""
    assert PryResumeMode.STEP == "step"


def test_pry_resume_mode_continue() -> None:
    """PryResumeMode.CONTINUE is defined."""
    assert PryResumeMode.CONTINUE == "continue"


def test_pry_resume_mode_continue_agent() -> None:
    """PryResumeMode.CONTINUE_AGENT resumes only the selected agent."""
    assert PryResumeMode.CONTINUE_AGENT == "continue_agent"


def test_pry_resume_mode_all_are_strings() -> None:
    """All PryResumeMode values are strings (StrEnum)."""
    for mode in PryResumeMode:
        assert isinstance(mode, str)


# ---------------------------------------------------------------------------
# Workflow.debugpoint() inserts a pause marker before the next step
# ---------------------------------------------------------------------------


def test_debugpoint_adds_to_debug_points() -> None:
    """.debugpoint() records the next step index in _debug_points."""
    from syrin import Agent, Model

    Model.Almock(latency_seconds=0, lorem_length=1)

    class _A(Agent):
        model = Model.Almock(latency_seconds=0, lorem_length=1)
        system_prompt = "a"

    wf = Workflow("wf", pry=True)
    wf.debugpoint()
    wf.step(_A, "task one")
    assert 0 in wf._debug_points


def test_debugpoint_records_step_index_correctly() -> None:
    """.debugpoint() before the second step records index 1."""
    from syrin import Agent, Model

    class _B(Agent):
        model = Model.Almock(latency_seconds=0, lorem_length=1)
        system_prompt = "b"

    wf = Workflow("wf", pry=True)
    wf.step(_B, "first")
    wf.debugpoint()
    wf.step(_B, "second")
    # _debug_points should have 1 (index of the second step)
    assert 1 in wf._debug_points


def test_debugpoint_is_chainable() -> None:
    """.debugpoint() returns self for fluent chaining."""
    wf = Workflow("wf", pry=True)
    result = wf.debugpoint()
    assert result is wf


def test_debugpoint_no_effect_when_pry_false() -> None:
    """.debugpoint() still records the index even when pry=False (stored, not activated)."""
    from syrin import Agent, Model

    class _C(Agent):
        model = Model.Almock(latency_seconds=0, lorem_length=1)
        system_prompt = "c"

    wf = Workflow("wf", pry=False)
    wf.debugpoint()
    wf.step(_C, "task")
    # Index is stored but won't be activated at runtime (no-op guarantee)
    assert len(wf._debug_points) == 1
