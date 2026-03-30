"""Tool schema cache — to_format() must not re-serialize on every call.

Tests that:
- Repeated calls to to_format() return the same object (identity check proves caching)
- Different DocFormat values are cached separately
- Two ToolSpec instances with same spec produce equivalent (but not identical) results
"""

from __future__ import annotations

from syrin.enums import DocFormat
from syrin.tool import ToolSpec, tool


def _make_spec() -> ToolSpec:
    @tool
    def my_tool(x: str, y: int) -> str:
        """A sample tool."""
        return x

    assert isinstance(my_tool, ToolSpec)
    return my_tool


class TestToolSchemaCache:
    def test_to_format_returns_same_object_on_repeated_calls(self) -> None:
        """Same ToolSpec instance returns identical dict object on repeated to_format() calls."""
        spec = _make_spec()
        result1 = spec.to_format(DocFormat.TOON)
        result2 = spec.to_format(DocFormat.TOON)
        assert result1 is result2, (
            "to_format() should return cached object, not a new dict each time"
        )

    def test_result_is_same_object_on_repeated_calls(self) -> None:
        """Cached result is identical Python object, not just equal."""
        spec = _make_spec()
        result1 = spec.to_format(DocFormat.TOON)
        result2 = spec.to_format(DocFormat.TOON)
        result3 = spec.to_format(DocFormat.TOON)
        assert result1 is result2 is result3

    def test_different_formats_cached_separately(self) -> None:
        """Each DocFormat gets its own cache slot."""
        spec = _make_spec()
        toon1 = spec.to_format(DocFormat.TOON)
        toon2 = spec.to_format(DocFormat.TOON)
        json1 = spec.to_format(DocFormat.JSON)
        json2 = spec.to_format(DocFormat.JSON)
        assert toon1 is toon2
        assert json1 is json2
        # TOON and JSON results are different dicts
        assert toon1 is not json1

    def test_two_instances_produce_equivalent_results(self) -> None:
        """Two independent ToolSpec instances with same params produce equal (not identical) results."""
        spec1 = _make_spec()
        spec2 = _make_spec()
        r1 = spec1.to_format(DocFormat.TOON)
        r2 = spec2.to_format(DocFormat.TOON)
        assert r1 == r2
        # They are separate instances so not necessarily identical objects
