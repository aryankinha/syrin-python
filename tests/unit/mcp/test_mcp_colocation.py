"""Tests for MCP co-location — /mcp route when MCP is in agent tools."""

from __future__ import annotations

from fastapi import FastAPI
from starlette.testclient import TestClient

from syrin import Agent, tool
from syrin.mcp import MCP
from syrin.model import Model
from syrin.serve.config import ServeConfig
from syrin.serve.http import build_router


def test_mcp_route_mounted_when_mcp_in_tools() -> None:
    """When MCP is in agent tools, POST /mcp handles JSON-RPC tools/list and tools/call."""

    class ProductMCP(MCP):
        @tool
        def search_products(self, query: str) -> str:
            return f"Results: {query}"

    class ProductAgent(Agent):
        model = Model.Almock()
        name = "product-agent"
        description = "Product agent with MCP"
        tools = [ProductMCP()]

    agent = ProductAgent()
    config = ServeConfig()
    router = build_router(agent, config)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "result" in data
    assert "tools" in data["result"]
    assert len(data["result"]["tools"]) >= 1
    names = [t["name"] for t in data["result"]["tools"]]
    assert "search_products" in names

    resp2 = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "search_products", "arguments": {"query": "shoes"}},
        },
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert "result" in data2
    assert data2["result"]["content"][0]["text"] == "Results: shoes"


def test_no_mcp_route_when_no_mcp_in_tools() -> None:
    """When agent has no MCP in tools, POST /mcp returns 404."""

    class PlainAgent(Agent):
        model = Model.Almock()
        name = "plain"
        description = "No MCP"
        tools = []

    agent = PlainAgent()
    config = ServeConfig()
    router = build_router(agent, config)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
    )
    assert resp.status_code == 404
