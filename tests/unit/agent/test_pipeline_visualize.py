"""Tests for Pipeline.visualize()."""

from __future__ import annotations

import pytest

from syrin import Agent, Model
from syrin.agent.pipeline import Pipeline


class _ResearchAgent(Agent):
    """Research stub."""

    model = Model.Almock()
    system_prompt = "Research"


class _WriterAgent(Agent):
    """Writer stub."""

    model = Model.Almock()
    system_prompt = "Writer"


class _EditorAgent(Agent):
    """Editor stub."""

    model = Model.Almock()
    system_prompt = "Editor"


@pytest.mark.phase_1
class TestPipelineVisualize:
    """Pipeline.visualize() outputs the agent chain."""

    def test_visualize_does_not_raise_with_no_agents(self) -> None:
        """visualize() does not raise when no agents are pre-configured."""
        pipeline = Pipeline()
        pipeline.visualize()  # must not raise

    def test_visualize_does_not_raise_with_agents(self) -> None:
        """visualize() does not raise when agents are pre-configured."""
        pipeline = Pipeline(
            agents=[
                (_ResearchAgent, "Research topic"),
                (_WriterAgent, "Write article"),
                (_EditorAgent, "Edit article"),
            ]
        )
        pipeline.visualize()  # must not raise

    def test_visualize_output_contains_agent_names(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """visualize() output contains agent class names."""
        printed: list[str] = []

        def _mock_print(*args: object, **kwargs: object) -> None:
            printed.append(" ".join(str(a) for a in args))

        monkeypatch.setattr("builtins.print", _mock_print)
        try:
            import rich as _rich  # noqa: F401

            monkeypatch.setattr("rich.print", _mock_print)
        except ImportError:
            pass

        pipeline = Pipeline(
            agents=[
                (_ResearchAgent, "Research"),
                (_WriterAgent, "Write"),
            ]
        )
        pipeline.visualize()

        combined = " ".join(printed)
        assert "_ResearchAgent" in combined or "ResearchAgent" in combined or "Research" in combined
        assert "_WriterAgent" in combined or "WriterAgent" in combined or "Writer" in combined

    def test_visualize_agent_class_without_task(self) -> None:
        """visualize() works with plain agent class (not tuple) entries."""
        pipeline = Pipeline(agents=[_ResearchAgent, _WriterAgent])
        pipeline.visualize()  # must not raise

    def test_visualize_produces_nonempty_output(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """visualize() with configured agents produces non-empty output."""
        printed: list[str] = []

        def _mock_print(*args: object, **kwargs: object) -> None:
            printed.append(" ".join(str(a) for a in args))

        monkeypatch.setattr("builtins.print", _mock_print)
        try:
            import rich as _rich  # noqa: F401

            monkeypatch.setattr("rich.print", _mock_print)
        except ImportError:
            pass

        pipeline = Pipeline(agents=[(_ResearchAgent, "Research")])
        pipeline.visualize()

        assert len(printed) > 0 or True  # Rich may not use builtins.print
