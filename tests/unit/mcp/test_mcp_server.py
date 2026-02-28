"""Tests for syrin.MCP — declarative MCP server base class."""

from __future__ import annotations

from syrin import tool
from syrin.mcp import MCP


def test_mcp_collects_tool_methods_from_class() -> None:
    """MCP collects @tool methods from class."""

    class ProductMCP(MCP):
        @tool
        def search_products(self, query: str, limit: int = 10) -> str:
            return f"Results: {query} (limit={limit})"

        @tool
        def get_product(self, product_id: str) -> str:
            return f"Product: {product_id}"

    mcp = ProductMCP()
    specs = mcp.tools()
    assert len(specs) == 2
    names = [s.name for s in specs]
    assert "search_products" in names
    assert "get_product" in names


def test_mcp_select_returns_subset() -> None:
    """MCP.select() returns only specified tools."""

    class ProductMCP(MCP):
        @tool
        def search_products(self, query: str) -> str:
            return "results"

        @tool
        def get_product(self, product_id: str) -> str:
            return "product"

    mcp = ProductMCP()
    selected = mcp.select("get_product")
    assert len(selected) == 1
    assert selected[0].name == "get_product"


def test_mcp_tool_execution() -> None:
    """MCP tool func executes correctly when bound to instance."""

    class ProductMCP(MCP):
        @tool
        def search_products(self, query: str, limit: int = 5) -> str:
            return f"Found {query[:limit]}"

    mcp = ProductMCP()
    spec = mcp.tools()[0]
    result = spec.func(query="hello", limit=3)
    assert result == "Found hel"
