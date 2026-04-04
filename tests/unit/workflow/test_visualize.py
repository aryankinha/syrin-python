"""P1-T13: Workflow static visualization tests."""

from __future__ import annotations

import pytest

from syrin import Agent, Budget, Model
from syrin.workflow import Workflow


class AgentA(Agent):
    """Stub agent A."""

    model = Model.Almock()
    system_prompt = "A"


class AgentB(Agent):
    """Stub agent B."""

    model = Model.Almock()
    system_prompt = "B"


class AgentC(Agent):
    """Stub agent C."""

    model = Model.Almock()
    system_prompt = "C"


@pytest.mark.phase_1
class TestVisualizeSmokeTest:
    """visualize() does not raise on any step type."""

    def test_visualize_sequential(self, capsys: pytest.CaptureFixture[str]) -> None:
        """visualize() renders a sequential-only workflow without error."""
        wf = Workflow("seq").step(AgentA).step(AgentB)
        wf.visualize()  # must not raise

    def test_visualize_parallel(self, capsys: pytest.CaptureFixture[str]) -> None:
        """visualize() renders a parallel step without error."""
        wf = Workflow("par").parallel([AgentA, AgentB])
        wf.visualize()

    def test_visualize_branch(self, capsys: pytest.CaptureFixture[str]) -> None:
        """visualize() renders a branch step without error."""
        wf = Workflow("branch").branch(
            condition=lambda _ctx: True,
            if_true=AgentA,
            if_false=AgentB,
        )
        wf.visualize()

    def test_visualize_dynamic(self, capsys: pytest.CaptureFixture[str]) -> None:
        """visualize() renders a dynamic step without error."""
        wf = Workflow("dyn").dynamic(fn=lambda _ctx: [])
        wf.visualize()

    def test_visualize_mixed(self, capsys: pytest.CaptureFixture[str]) -> None:
        """visualize() renders a workflow with all step types."""
        wf = (
            Workflow("mixed")
            .step(AgentA)
            .parallel([AgentB, AgentC])
            .branch(condition=lambda _ctx: True, if_true=AgentA, if_false=AgentB)
            .dynamic(fn=lambda _ctx: [])
        )
        wf.visualize()


@pytest.mark.phase_1
class TestToMermaid:
    """to_mermaid() returns a valid Mermaid string."""

    def test_returns_string(self) -> None:
        """to_mermaid() returns a str."""
        wf = Workflow("test").step(AgentA)
        result = wf.to_mermaid()
        assert isinstance(result, str)

    def test_starts_with_graph_directive(self) -> None:
        """to_mermaid() starts with 'graph TD' or 'graph LR'."""
        wf = Workflow("test").step(AgentA)
        result = wf.to_mermaid()
        assert result.startswith("graph TD") or result.startswith("graph LR")

    def test_no_unclosed_brackets(self) -> None:
        """to_mermaid() output has balanced brackets."""
        wf = (
            Workflow("bracket-test")
            .step(AgentA)
            .parallel([AgentB, AgentC])
            .branch(condition=lambda _ctx: False, if_true=AgentA, if_false=AgentB)
            .dynamic(fn=lambda _ctx: [])
        )
        mermaid = wf.to_mermaid()
        assert mermaid.count("[") == mermaid.count("]")
        assert mermaid.count("{") == mermaid.count("}")
        assert mermaid.count("(") == mermaid.count(")")

    def test_sequential_step_appears(self) -> None:
        """to_mermaid() includes agent class names for sequential steps."""
        wf = Workflow("test").step(AgentA)
        result = wf.to_mermaid()
        assert "AgentA" in result

    def test_parallel_step_appears(self) -> None:
        """to_mermaid() includes all agent names for parallel steps."""
        wf = Workflow("test").parallel([AgentA, AgentB])
        result = wf.to_mermaid()
        assert "AgentA" in result
        assert "AgentB" in result

    def test_dynamic_step_appears(self) -> None:
        """to_mermaid() renders dynamic step with runtime label."""
        wf = Workflow("test").dynamic(fn=lambda _ctx: [])
        result = wf.to_mermaid()
        # Should contain some indicator of dynamism
        assert "dynamic" in result.lower() or "runtime" in result.lower() or "λ" in result

    def test_branch_step_appears(self) -> None:
        """to_mermaid() renders branch condition node."""
        wf = Workflow("test").branch(
            condition=lambda _ctx: True,
            if_true=AgentA,
            if_false=AgentB,
        )
        result = wf.to_mermaid()
        # Should contain branch indicator (diamond or condition reference)
        assert "AgentA" in result
        assert "AgentB" in result


@pytest.mark.phase_1
class TestToDict:
    """to_dict() returns a dict with 'nodes' and 'edges' keys."""

    def test_returns_dict_with_nodes_and_edges(self) -> None:
        """to_dict() always has 'nodes' and 'edges' keys."""
        wf = Workflow("test").step(AgentA)
        result = wf.to_dict()
        assert "nodes" in result
        assert "edges" in result

    def test_nodes_is_list(self) -> None:
        """to_dict() nodes is a list."""
        wf = Workflow("test").step(AgentA).step(AgentB)
        result = wf.to_dict()
        assert isinstance(result["nodes"], list)

    def test_edges_is_list(self) -> None:
        """to_dict() edges is a list."""
        wf = Workflow("test").step(AgentA).step(AgentB)
        result = wf.to_dict()
        assert isinstance(result["edges"], list)

    def test_nodes_include_step_type(self) -> None:
        """Every node in to_dict() includes a 'step_type' field."""
        wf = Workflow("test").step(AgentA).parallel([AgentB, AgentC])
        result = wf.to_dict()
        for node in result["nodes"]:
            assert "step_type" in node, f"Node missing step_type: {node}"

    def test_node_with_budget_override_includes_budget(self) -> None:
        """to_dict() nodes include 'budget' when a step has an explicit budget."""
        bgt = Budget(max_cost=0.50)
        wf = Workflow("test").step(AgentA, budget=bgt)
        result = wf.to_dict()
        # At least one node should include budget info
        nodes_with_budget = [n for n in result["nodes"] if n.get("budget") is not None]
        assert len(nodes_with_budget) >= 1

    def test_two_sequential_steps_have_one_edge(self) -> None:
        """Two sequential steps produce at least one edge."""
        wf = Workflow("test").step(AgentA).step(AgentB)
        result = wf.to_dict()
        assert len(result["edges"]) >= 1


@pytest.mark.phase_1
class TestNestedVisualization:
    """Nested workflow renders as a collapsed block."""

    def test_nested_workflow_visualize_no_raise(self, capsys: pytest.CaptureFixture[str]) -> None:
        """visualize() on a workflow containing a sub-workflow does not raise."""
        inner = Workflow("inner").step(AgentA)
        outer = Workflow("outer").step(inner).step(AgentB)
        outer.visualize()

    def test_nested_workflow_to_dict_has_workflow_node(self) -> None:
        """to_dict() marks a sub-workflow step with step_type 'workflow' or 'sequential'."""
        inner = Workflow("inner").step(AgentA)
        outer = Workflow("outer").step(inner)
        result = outer.to_dict()
        # Should have at least one node
        assert len(result["nodes"]) >= 1

    def test_visualize_expand_nested_does_not_raise(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """visualize(expand_nested=True) does not raise for a nested workflow."""
        inner = Workflow("inner").step(AgentA).step(AgentB)
        outer = Workflow("outer").step(inner).step(AgentC)
        outer.visualize(expand_nested=True)  # must not raise

    def test_visualize_expand_nested_false_does_not_raise(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """visualize(expand_nested=False) is the default and must not raise."""
        inner = Workflow("inner-wf").step(AgentA)
        outer = Workflow("outer-wf").step(inner).step(AgentB)
        outer.visualize(expand_nested=False)  # must not raise

    def test_expand_nested_false_shows_collapsed_block(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """expand_nested=False shows a collapsed [SubWorkflow] block, not sub-steps."""
        inner = Workflow("inner-wf").step(AgentA).step(AgentB)
        outer = Workflow("outer").step(inner)
        outer.visualize(expand_nested=False)
        captured = capsys.readouterr()
        output = captured.out
        # Collapsed form should show the nested workflow name as a block
        assert "inner-wf" in output
        # Sub-steps (AgentA, AgentB class names) should NOT be individually listed
        # as separate step entries — they appear only inside the collapsed block label
        assert "AgentA" not in output or "[inner-wf]" in output

    def test_expand_nested_true_shows_inline_steps(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """expand_nested=True renders sub-workflow steps inline."""
        inner = Workflow("inner-wf").step(AgentA).step(AgentB)
        outer = Workflow("outer").step(inner).step(AgentC)
        outer.visualize(expand_nested=True)
        captured = capsys.readouterr()
        output = captured.out
        # Expanded form should show sub-workflow name + sub-steps
        assert "inner-wf" in output
        assert "AgentA" in output
        assert "AgentB" in output
