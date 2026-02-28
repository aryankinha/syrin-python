"""Tests for Agent @tool auto-collection from class methods."""

from __future__ import annotations

from syrin import Agent, tool
from syrin.model import Model


def test_agent_collects_tool_methods_from_class() -> None:
    """@tool methods on Agent class are collected without explicit tools=[]."""

    class Assistant(Agent):
        model = Model("openai/gpt-4")

        @tool
        def greet(self, name: str) -> str:
            return f"Hello {name}"

    agent = Assistant()
    assert len(agent.tools) == 1
    assert agent.tools[0].name == "greet"
    result = agent._execute_tool("greet", {"name": "World"})
    assert result == "Hello World"


def test_agent_tool_methods_plus_explicit_tools_merged() -> None:
    """Class @tool methods and explicit tools list are merged."""

    @tool
    def external_search(query: str) -> str:
        return f"Results for {query}"

    class SearchAgent(Agent):
        model = Model("openai/gpt-4")

        @tool
        def local_lookup(self, key: str) -> str:
            return f"Local: {key}"

    agent = SearchAgent(tools=[external_search])
    names = [t.name for t in agent.tools]
    assert "local_lookup" in names
    assert "external_search" in names


def test_agent_explicit_tool_overrides_class_by_name() -> None:
    """Explicit tool with same name overrides class @tool."""

    @tool
    def greet(name: str) -> str:
        return f"External: {name}"

    class Assistant(Agent):
        model = Model("openai/gpt-4")

        @tool
        def greet(self, name: str) -> str:
            return f"Class: {name}"

    agent = Assistant(tools=[greet])
    assert len(agent.tools) == 1
    assert agent.tools[0].name == "greet"
    result = agent._execute_tool("greet", {"name": "X"})
    assert result == "External: X"
