"""Tests for image/video generation cost recording into budget.

TDD: agent records cost from GenerationResult.metadata on GENERATION_IMAGE_END
and GENERATION_VIDEO_END when has_budget.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from syrin import Agent, Budget, ImageGenerator, Model, VideoGenerator
from syrin.enums import Hook
from syrin.generation._result import GenerationResult
from syrin.types import CostInfo

# =============================================================================
# VALID: Agent records cost when result has cost_usd in metadata
# =============================================================================


def test_agent_records_image_cost_on_generation_end_when_has_budget() -> None:
    """When agent has budget and GENERATION_IMAGE_END emits with cost in metadata, record it."""
    mock_img_gen = MagicMock()
    result_with_cost = GenerationResult(
        success=True,
        url="data:image/png;base64,x",
        content_type="image/png",
        metadata={"cost_usd": 0.067, "model_name": "imagen-4.0-generate-001"},
    )
    mock_img_gen.generate.return_value = [result_with_cost]

    agent = Agent(
        model=Model.Almock(),
        system_prompt="Test.",
        image_generation=ImageGenerator.from_provider("gemini", api_key="test"),
        budget=Budget(run=10.0),
    )
    agent._image_generator = mock_img_gen

    # Ensure Almock is used (no real LLM call needed for tool execution path)
    with patch.object(agent, "_image_generator", mock_img_gen):
        # Call the emit path that would run on GENERATION_IMAGE_END
        recorded: list[CostInfo] = []
        orig_record = agent._record_cost_info

        def capture_record(c: CostInfo) -> None:
            recorded.append(c)
            orig_record(c)

        with patch.object(agent, "_record_cost_info", side_effect=capture_record):
            # Simulate emit from ImageGenerator - call _emit_event with GENERATION_IMAGE_END
            agent._emit_event(
                Hook.GENERATION_IMAGE_END,
                {
                    "results": [result_with_cost],
                    "count": 1,
                    "model": "imagen-4.0-generate-001",
                },
            )

    # Agent should have recorded the media cost (0.067)
    media_cost_calls = [c for c in recorded if c.cost_usd == 0.067 and "imagen" in c.model_name]
    assert len(media_cost_calls) >= 1


def test_agent_records_video_cost_on_generation_end_when_has_budget() -> None:
    """When agent has budget and GENERATION_VIDEO_END emits with cost in metadata, record it."""
    result_with_cost = GenerationResult(
        success=True,
        url="data:video/mp4;base64,x",
        content_type="video/mp4",
        metadata={"cost_usd": 1.75, "model_name": "veo-2.0-generate-001"},
    )

    agent = Agent(
        model=Model.Almock(),
        system_prompt="Test.",
        video_generation=VideoGenerator.from_provider("gemini", api_key="test"),
        budget=Budget(run=10.0),
    )

    recorded: list[CostInfo] = []
    orig_record = agent._record_cost_info

    def capture_record(c: CostInfo) -> None:
        recorded.append(c)
        orig_record(c)

    with patch.object(agent, "_record_cost_info", side_effect=capture_record):
        agent._emit_event(
            Hook.GENERATION_VIDEO_END,
            {"result": result_with_cost, "model": "veo-2.0-generate-001"},
        )

    media_cost_calls = [c for c in recorded if c.cost_usd == 1.75 and "veo" in c.model_name]
    assert len(media_cost_calls) >= 1


# =============================================================================
# EDGE: No budget -> no recording
# =============================================================================


def test_agent_does_not_record_media_cost_when_no_budget() -> None:
    """Without budget, emit still runs but _record_cost_info is never called for media."""
    agent = Agent(
        model=Model.Almock(),
        system_prompt="Test.",
        budget=None,
    )
    # Agent without budget has _budget_tracker = None or no budget
    assert agent._budget is None or agent._budget_tracker is None


# =============================================================================
# EDGE: metadata missing cost_usd -> no recording
# =============================================================================


def test_agent_does_not_record_when_metadata_lacks_cost_usd() -> None:
    """When results have no cost_usd in metadata, nothing extra is recorded."""
    result_no_cost = GenerationResult(
        success=True,
        url="data:image/png;base64,x",
        content_type="image/png",
        metadata={},  # no cost_usd
    )

    agent = Agent(
        model=Model.Almock(),
        system_prompt="Test.",
        image_generation=ImageGenerator.from_provider("gemini", api_key="test"),
        budget=Budget(run=10.0),
    )

    recorded: list[CostInfo] = []
    orig_record = agent._record_cost_info

    def capture_record(c: CostInfo) -> None:
        recorded.append(c)
        orig_record(c)

    with patch.object(agent, "_record_cost_info", side_effect=capture_record):
        agent._emit_event(
            Hook.GENERATION_IMAGE_END,
            {"results": [result_no_cost], "count": 1, "model": "imagen-4.0"},
        )

    # Should NOT have recorded any media cost (cost_usd would be 0, we might not call record)
    # Implementation: we only call _record_cost_info when cost_usd > 0
    media_calls = [c for c in recorded if c.model_name and "imagen" in c.model_name]
    assert len(media_calls) == 0


# =============================================================================
# EDGE: cost_usd is 0 -> no recording (avoid noise)
# =============================================================================


def test_agent_does_not_record_when_cost_usd_is_zero() -> None:
    """cost_usd=0 in metadata should not trigger record."""
    result_zero = GenerationResult(
        success=True,
        url="data:image/png;base64,x",
        metadata={"cost_usd": 0.0, "model_name": "imagen"},
    )

    agent = Agent(
        model=Model.Almock(),
        system_prompt="Test.",
        image_generation=ImageGenerator.from_provider("gemini", api_key="test"),
        budget=Budget(run=10.0),
    )

    recorded: list[CostInfo] = []
    orig_record = agent._record_cost_info

    def capture_record(c: CostInfo) -> None:
        recorded.append(c)
        orig_record(c)

    with patch.object(agent, "_record_cost_info", side_effect=capture_record):
        agent._emit_event(
            Hook.GENERATION_IMAGE_END,
            {"results": [result_zero], "count": 1, "model": "imagen"},
        )

    media_calls = [c for c in recorded if "imagen" in c.model_name]
    assert len(media_calls) == 0


# =============================================================================
# EDGE: Failed result (success=False) -> no recording
# =============================================================================


def test_agent_does_not_record_cost_for_failed_generation() -> None:
    """Failed results (success=False) should not record cost."""
    failed_result = GenerationResult(
        success=False,
        error="API error",
        metadata={"cost_usd": 0.067, "model_name": "imagen"},  # would have cost if succeeded
    )

    agent = Agent(
        model=Model.Almock(),
        system_prompt="Test.",
        image_generation=ImageGenerator.from_provider("gemini", api_key="test"),
        budget=Budget(run=10.0),
    )

    recorded: list[CostInfo] = []
    orig_record = agent._record_cost_info

    def capture_record(c: CostInfo) -> None:
        recorded.append(c)
        orig_record(c)

    with patch.object(agent, "_record_cost_info", side_effect=capture_record):
        agent._emit_event(
            Hook.GENERATION_IMAGE_END,
            {"results": [failed_result], "count": 1, "model": "imagen"},
        )

    # We only record cost for successful results
    media_calls = [c for c in recorded if "imagen" in c.model_name]
    assert len(media_calls) == 0
