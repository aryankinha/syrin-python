"""Tests for MCP.serve() — standalone HTTP and STDIO serving."""

from __future__ import annotations

import io

from syrin import MCP, tool
from syrin.mcp.stdio import run_stdio_mcp


def test_mcp_serve_stdio_tools_list() -> None:
    """STDIO: tools/list returns tools."""

    class ProductMCP(MCP):
        @tool
        def search_products(self, query: str) -> str:
            return f"Results: {query}"

    mcp = ProductMCP()
    stdin = io.StringIO('{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\n')
    stdout = io.StringIO()

    run_stdio_mcp(mcp, stdin=stdin, stdout=stdout)

    out = stdout.getvalue().strip()
    assert '"result"' in out
    assert '"tools"' in out
    assert "search_products" in out


def test_mcp_serve_stdio_tools_call() -> None:
    """STDIO: tools/call executes tool."""

    class ProductMCP(MCP):
        @tool
        def search_products(self, query: str) -> str:
            return f"Results: {query}"

    mcp = ProductMCP()
    stdin = io.StringIO(
        '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"search_products","arguments":{"query":"shoes"}}}\n'
    )
    stdout = io.StringIO()

    run_stdio_mcp(mcp, stdin=stdin, stdout=stdout)

    out = stdout.getvalue().strip()
    assert '"result"' in out
    assert "Results: shoes" in out


def test_mcp_initialize_returns_server_info() -> None:
    """MCP initialize returns protocolVersion, capabilities, serverInfo per spec."""

    class ProductMCP(MCP):
        name = "product-mcp"

        @tool
        def search_products(self, query: str) -> str:
            return "results"

    mcp = ProductMCP()
    stdin = io.StringIO(
        '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}\n'
    )
    stdout = io.StringIO()

    run_stdio_mcp(mcp, stdin=stdin, stdout=stdout)

    import json

    out = stdout.getvalue().strip()
    lines = [ln for ln in out.split("\n") if ln.strip() and ln.strip().startswith("{")]
    assert len(lines) >= 1
    data = json.loads(lines[-1])
    assert "result" in data
    r = data["result"]
    assert "protocolVersion" in r
    assert "capabilities" in r
    assert "tools" in r["capabilities"]
    assert r["serverInfo"]["name"] == "product-mcp"


def test_mcp_serve_http_smoke() -> None:
    """HTTP: MCP.serve(port=...) starts server (smoke test via TestClient)."""

    class ProductMCP(MCP):
        @tool
        def search_products(self, query: str) -> str:
            return f"Results: {query}"

    mcp = ProductMCP()
    from fastapi import FastAPI

    from syrin.mcp.http import build_mcp_router

    router = build_mcp_router(mcp)
    app = FastAPI()
    app.include_router(router, prefix="/mcp")
    from starlette.testclient import TestClient

    client = TestClient(app)

    # MCP spec: initialize must be first (Syrin CLI connection test)
    resp = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "syrin-cli", "version": "1.0"},
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "result" in data
    r = data["result"]
    assert "protocolVersion" in r
    assert r["serverInfo"]["name"] == "mcp"

    resp = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "result" in data
    assert "tools" in data["result"]
    assert len(data["result"]["tools"]) >= 1
