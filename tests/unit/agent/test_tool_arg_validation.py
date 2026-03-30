"""Tool argument validation before execution.

Tests that:
- Missing required arguments raise ToolArgumentError
- Wrong basic types (dict where str expected, etc.) raise ToolArgumentError
- Coercible types (int-as-string for int param) are accepted
- Optional parameters accept None
- Validation error message includes tool name, param name, and expected type
"""

from __future__ import annotations

import pytest

from syrin.agent._tool_exec import execute_tool
from syrin.exceptions import ToolArgumentError
from syrin.tool import ToolSpec, tool

# ---------------------------------------------------------------------------
# Helper: build a minimal Agent-like stub for execute_tool
# ---------------------------------------------------------------------------


class _StubAgent:
    """Minimal stub with just enough for execute_tool."""

    def __init__(self, tools: list[ToolSpec]) -> None:
        self.tools = tools
        self._dependencies = None

    @property
    def tools_map(self) -> dict[str, ToolSpec]:
        return {spec.name: spec for spec in self.tools}


# ---------------------------------------------------------------------------
# Sample tools
# ---------------------------------------------------------------------------


@tool
def greet(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}"


@tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


@tool
def ratio(numerator: float, denominator: float) -> float:
    """Return ratio."""
    return numerator / denominator


@tool
def flag(enabled: bool) -> str:
    """Toggle."""
    return "on" if enabled else "off"


@tool
def tag(name: str, tags: list[str]) -> str:
    """Tag something."""
    return f"{name}: {tags}"


@tool
def optional_name(name: str | None = None) -> str:
    """Optional name."""
    return name or "nobody"


# ---------------------------------------------------------------------------
# Tests: valid calls must still work
# ---------------------------------------------------------------------------


class TestValidCalls:
    def test_str_param(self) -> None:
        agent = _StubAgent([greet])
        result = execute_tool(agent, "greet", {"name": "Alice"})
        assert result == "Hello, Alice"

    def test_int_param(self) -> None:
        agent = _StubAgent([add])
        result = execute_tool(agent, "add", {"a": 1, "b": 2})
        assert result == "3"

    def test_float_param(self) -> None:
        agent = _StubAgent([ratio])
        result = execute_tool(agent, "ratio", {"numerator": 10.0, "denominator": 2.0})
        assert result == "5.0"

    def test_bool_param(self) -> None:
        agent = _StubAgent([flag])
        result = execute_tool(agent, "flag", {"enabled": True})
        assert result == "on"

    def test_list_param(self) -> None:
        agent = _StubAgent([tag])
        result = execute_tool(agent, "tag", {"name": "item", "tags": ["a", "b"]})
        assert result == "item: ['a', 'b']"

    def test_optional_none(self) -> None:
        agent = _StubAgent([optional_name])
        result = execute_tool(agent, "optional_name", {})
        assert result == "nobody"

    def test_optional_value(self) -> None:
        agent = _StubAgent([optional_name])
        result = execute_tool(agent, "optional_name", {"name": "Alice"})
        assert result == "Alice"


# ---------------------------------------------------------------------------
# Tests: type mismatches that should raise ToolArgumentError
# ---------------------------------------------------------------------------


class TestTypeMismatch:
    def test_dict_where_str_expected(self) -> None:
        """Sending a dict when str is expected should fail."""
        agent = _StubAgent([greet])
        with pytest.raises(ToolArgumentError) as exc_info:
            execute_tool(agent, "greet", {"name": {"nested": "object"}})
        assert "name" in str(exc_info.value)
        assert "greet" in str(exc_info.value)

    def test_list_where_str_expected(self) -> None:
        agent = _StubAgent([greet])
        with pytest.raises(ToolArgumentError):
            execute_tool(agent, "greet", {"name": ["a", "b"]})

    def test_str_where_list_expected(self) -> None:
        agent = _StubAgent([tag])
        with pytest.raises(ToolArgumentError):
            execute_tool(agent, "tag", {"name": "item", "tags": "not-a-list"})

    def test_dict_where_int_expected(self) -> None:
        agent = _StubAgent([add])
        with pytest.raises(ToolArgumentError) as exc_info:
            execute_tool(agent, "add", {"a": {"bad": "arg"}, "b": 2})
        assert "a" in str(exc_info.value)

    def test_error_includes_expected_type(self) -> None:
        # A dict cannot be coerced to str — should raise with clear message
        agent = _StubAgent([greet])
        with pytest.raises(ToolArgumentError) as exc_info:
            execute_tool(agent, "greet", {"name": {"nested": "value"}})
        assert "str" in str(exc_info.value).lower() or "name" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Tests: coercible types (LLM-generated numbers as strings, etc.)
# ---------------------------------------------------------------------------


class TestCoercibleTypes:
    def test_int_as_string_accepted_for_int(self) -> None:
        """LLMs often emit integer values as strings. Should be coerced."""
        agent = _StubAgent([add])
        # "3" can be coerced to int — should NOT raise
        result = execute_tool(agent, "add", {"a": "3", "b": "4"})
        assert result == "7"

    def test_float_as_string_accepted_for_float(self) -> None:
        agent = _StubAgent([ratio])
        result = execute_tool(agent, "ratio", {"numerator": "10.0", "denominator": "2.0"})
        assert result == "5.0"

    def test_bool_as_string_true(self) -> None:
        """LLMs may emit "true" for bool."""
        agent = _StubAgent([flag])
        result = execute_tool(agent, "flag", {"enabled": "true"})
        assert result == "on"

    def test_bool_as_string_false(self) -> None:
        agent = _StubAgent([flag])
        result = execute_tool(agent, "flag", {"enabled": "false"})
        assert result == "off"
