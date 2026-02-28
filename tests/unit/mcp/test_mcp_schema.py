"""Tests for MCP schema conversion — ToolSpec ↔ MCP Tool."""

from __future__ import annotations

from syrin.mcp.schema import mcp_tool_to_tool_spec, tool_spec_to_mcp
from syrin.tool import ToolSpec


def test_tool_spec_to_mcp() -> None:
    """ToolSpec converts to MCP tool dict with name, description, inputSchema."""

    def dummy_func(x: str) -> str:
        return x

    spec = ToolSpec(
        name="search",
        description="Search the catalog",
        parameters_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["query"],
        },
        func=dummy_func,
    )
    mcp = tool_spec_to_mcp(spec)
    assert mcp["name"] == "search"
    assert mcp["description"] == "Search the catalog"
    assert "inputSchema" in mcp
    assert mcp["inputSchema"]["properties"]["query"] == {"type": "string"}
    assert "query" in mcp["inputSchema"]["required"]


def test_mcp_tool_to_tool_spec() -> None:
    """MCP tool dict converts to ToolSpec with call_fn."""

    results: list[dict] = []

    def call_fn(**kwargs: object) -> str:
        results.append(kwargs)
        return "ok"

    mcp_tool = {
        "name": "get_product",
        "description": "Get product by ID",
        "inputSchema": {
            "type": "object",
            "properties": {"product_id": {"type": "string"}},
            "required": ["product_id"],
        },
    }
    spec = mcp_tool_to_tool_spec(mcp_tool, call_fn)
    assert spec.name == "get_product"
    assert spec.description == "Get product by ID"
    assert spec.parameters_schema["properties"]["product_id"] == {"type": "string"}
    out = spec.func(product_id="p1")
    assert out == "ok"
    assert results == [{"product_id": "p1"}]
