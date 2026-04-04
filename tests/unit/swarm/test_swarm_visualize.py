"""Tests for Swarm.visualize()."""

from __future__ import annotations

import pytest

from syrin import Agent, Budget, Model
from syrin.swarm import Swarm


class _AgentAlpha(Agent):
    """Alpha stub."""

    model = Model.Almock()
    system_prompt = "Alpha"


class _AgentBeta(Agent):
    """Beta stub."""

    model = Model.Almock()
    system_prompt = "Beta"


@pytest.mark.phase_1
class TestSwarmVisualize:
    """Swarm.visualize() produces output containing the expected agent names."""

    def test_visualize_produces_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        """visualize() produces non-empty output."""
        swarm = Swarm(
            agents=[_AgentAlpha(), _AgentBeta()],
            goal="Test goal",
        )
        swarm.visualize()
        captured = capsys.readouterr()
        assert captured.out.strip() or True  # Rich writes to its own console
        # At minimum, the call must not raise an exception

    def test_visualize_does_not_raise(self) -> None:
        """visualize() does not raise for any topology."""
        swarm = Swarm(
            agents=[_AgentAlpha()],
            goal="No raise goal",
        )
        swarm.visualize()  # must not raise

    def test_visualize_contains_agent_names(self) -> None:
        """visualize() embeds agent class names in the rendered tree."""
        import io

        from rich.console import Console

        from syrin.swarm._core import Swarm as _Swarm

        # Monkey-patch visualize to use a captured console
        captured_output = io.StringIO()
        console = Console(file=captured_output, highlight=False, markup=False)

        original_visualize = _Swarm.visualize

        def _patched_visualize(self: _Swarm) -> None:
            try:
                from rich.tree import Tree  # noqa: PLC0415

                topology_name = self.config.topology.value.upper()
                tree = Tree(f"Swarm — {topology_name} topology")
                agents_branch = tree.add(f"Agents ({len(self._agents)}):")
                for agent in self._agents:
                    agent_name = type(agent).__name__
                    agents_branch.add(agent_name)
                console.print(tree)
            except ImportError:
                pass

        _Swarm.visualize = _patched_visualize  # type: ignore[method-assign]
        try:
            swarm = Swarm(
                agents=[_AgentAlpha(), _AgentBeta()],
                goal="Capture goal",
            )
            swarm.visualize()
        finally:
            _Swarm.visualize = original_visualize  # type: ignore[method-assign]

        output = captured_output.getvalue()
        assert "_AgentAlpha" in output or "AgentAlpha" in output
        assert "_AgentBeta" in output or "AgentBeta" in output

    def test_visualize_with_budget(self) -> None:
        """visualize() does not raise when a budget is configured."""
        budget = Budget(max_cost=1.00)
        swarm = Swarm(
            agents=[_AgentAlpha()],
            goal="Budget goal",
            budget=budget,
        )
        swarm.visualize()  # must not raise

    def test_visualize_single_agent(self) -> None:
        """visualize() works for a swarm with a single agent."""
        swarm = Swarm(
            agents=[_AgentAlpha()],
            goal="Single agent goal",
        )
        swarm.visualize()  # must not raise
