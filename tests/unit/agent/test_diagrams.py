"""Tests for agent.lifecycle_diagram() and agent.flow_diagram() — Mermaid diagram generation."""

from __future__ import annotations


class TestLifecycleDiagram:
    def test_lifecycle_diagram_returns_string(self) -> None:
        """agent.lifecycle_diagram() returns a non-empty string."""
        from syrin.agent import Agent
        from syrin.model import Model

        agent = Agent(model=Model.Anthropic("claude-sonnet-4-6"))
        result = agent.lifecycle_diagram()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_lifecycle_diagram_is_valid_mermaid(self) -> None:
        """lifecycle_diagram() output starts with a valid Mermaid diagram type."""
        from syrin.agent import Agent
        from syrin.model import Model

        agent = Agent(model=Model.Anthropic("claude-sonnet-4-6"))
        diagram = agent.lifecycle_diagram()
        # Must start with a Mermaid keyword
        first_line = diagram.strip().splitlines()[0].strip()
        valid_starts = ("stateDiagram", "sequenceDiagram", "flowchart", "graph")
        assert any(first_line.startswith(s) for s in valid_starts), (
            f"Diagram does not start with a valid Mermaid type: {first_line!r}"
        )

    def test_lifecycle_diagram_includes_key_hooks(self) -> None:
        """lifecycle_diagram() references key lifecycle stages."""
        from syrin.agent import Agent
        from syrin.model import Model

        agent = Agent(model=Model.Anthropic("claude-sonnet-4-6"))
        diagram = agent.lifecycle_diagram()
        # Should mention at minimum input, LLM call, and output
        assert any(keyword in diagram.lower() for keyword in ["input", "user"]), (
            "Diagram should reference the input/user stage"
        )
        assert any(keyword in diagram.lower() for keyword in ["llm", "model", "call"]), (
            "Diagram should reference the LLM call stage"
        )

    def test_lifecycle_diagram_export_to_file(self, tmp_path) -> None:
        """lifecycle_diagram(export_path=...) writes Mermaid to a file."""
        from syrin.agent import Agent
        from syrin.model import Model

        agent = Agent(model=Model.Anthropic("claude-sonnet-4-6"))
        out = tmp_path / "lifecycle.mmd"
        agent.lifecycle_diagram(export_path=str(out))
        assert out.exists()
        content = out.read_text()
        assert len(content) > 0


class TestFlowDiagram:
    def test_flow_diagram_returns_string(self) -> None:
        """agent.flow_diagram() returns a non-empty string."""
        from syrin.agent import Agent
        from syrin.model import Model

        agent = Agent(model=Model.Anthropic("claude-sonnet-4-6"))
        result = agent.flow_diagram()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_flow_diagram_is_valid_mermaid(self) -> None:
        """flow_diagram() output starts with a valid Mermaid diagram type."""
        from syrin.agent import Agent
        from syrin.model import Model

        agent = Agent(model=Model.Anthropic("claude-sonnet-4-6"))
        diagram = agent.flow_diagram()
        first_line = diagram.strip().splitlines()[0].strip()
        valid_starts = ("flowchart", "graph", "sequenceDiagram", "stateDiagram")
        assert any(first_line.startswith(s) for s in valid_starts), (
            f"Diagram does not start with a valid Mermaid type: {first_line!r}"
        )

    def test_flow_diagram_includes_agent_name(self) -> None:
        """flow_diagram() references the agent's name."""
        from syrin.agent import Agent
        from syrin.model import Model

        agent = Agent(model=Model.Anthropic("claude-sonnet-4-6"), name="MyTestAgent")
        diagram = agent.flow_diagram()
        assert "MyTestAgent" in diagram

    def test_flow_diagram_with_tools_shows_tools(self) -> None:
        """flow_diagram() with tools registered shows tool nodes."""
        from syrin import tool
        from syrin.agent import Agent
        from syrin.model import Model

        @tool
        def search(query: str) -> str:
            return f"results for {query}"

        agent = Agent(
            model=Model.Anthropic("claude-sonnet-4-6"),
            tools=[search],
        )
        diagram = agent.flow_diagram()
        assert "search" in diagram.lower()

    def test_flow_diagram_export_to_file(self, tmp_path) -> None:
        """flow_diagram(export_path=...) writes to a file."""
        from syrin.agent import Agent
        from syrin.model import Model

        agent = Agent(model=Model.Anthropic("claude-sonnet-4-6"))
        out = tmp_path / "flow.mmd"
        agent.flow_diagram(export_path=str(out))
        assert out.exists()
        content = out.read_text()
        assert len(content) > 0
