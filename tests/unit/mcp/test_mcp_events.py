"""Tests for MCP lifecycle events (Hook.MCP_*)."""

from __future__ import annotations

import io

from syrin import MCP, tool
from syrin.enums import Hook
from syrin.events import EventContext
from syrin.mcp.stdio import run_stdio_mcp


def test_mcp_connected_emitted_on_initialize() -> None:
    """MCP_CONNECTED is emitted when initialize is received."""

    received: list[tuple[Hook, EventContext]] = []

    class ProductMCP(MCP):
        @tool
        def search_products(self, query: str) -> str:
            return "results"

    mcp = ProductMCP()
    mcp.events.on(Hook.MCP_CONNECTED, lambda ctx: received.append((Hook.MCP_CONNECTED, ctx)))

    stdin = io.StringIO(
        '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","clientInfo":{"name":"test"}}}\n'
    )
    stdout = io.StringIO()
    run_stdio_mcp(mcp, stdin=stdin, stdout=stdout)

    assert len(received) == 1
    assert received[0][0] == Hook.MCP_CONNECTED
    assert received[0][1].get("method") == "initialize"


def test_mcp_tool_call_start_end_emitted() -> None:
    """MCP_TOOL_CALL_START and MCP_TOOL_CALL_END are emitted on tools/call."""

    received: list[tuple[Hook, EventContext]] = []

    class ProductMCP(MCP):
        @tool
        def search_products(self, query: str) -> str:
            return f"Results: {query}"

    mcp = ProductMCP()
    mcp.events.on(
        Hook.MCP_TOOL_CALL_START, lambda ctx: received.append((Hook.MCP_TOOL_CALL_START, ctx))
    )
    mcp.events.on(
        Hook.MCP_TOOL_CALL_END, lambda ctx: received.append((Hook.MCP_TOOL_CALL_END, ctx))
    )

    stdin = io.StringIO(
        '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"search_products","arguments":{"query":"shoes"}}}\n'
    )
    stdout = io.StringIO()
    run_stdio_mcp(mcp, stdin=stdin, stdout=stdout)

    assert len(received) == 2
    assert received[0][0] == Hook.MCP_TOOL_CALL_START
    assert received[0][1]["tool_name"] == "search_products"
    assert received[0][1]["arguments"] == {"query": "shoes"}
    assert received[1][0] == Hook.MCP_TOOL_CALL_END
    assert received[1][1]["tool_name"] == "search_products"
    assert received[1][1].get("result") == "Results: shoes"


def test_mcp_disconnected_emitted_on_stdio_eof() -> None:
    """MCP_DISCONNECTED is emitted when STDIO receives EOF."""

    received: list[tuple[Hook, EventContext]] = []

    class ProductMCP(MCP):
        @tool
        def search_products(self, query: str) -> str:
            return "results"

    mcp = ProductMCP()
    mcp.events.on(Hook.MCP_DISCONNECTED, lambda ctx: received.append((Hook.MCP_DISCONNECTED, ctx)))

    stdin = io.StringIO('{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\n')
    stdout = io.StringIO()
    run_stdio_mcp(mcp, stdin=stdin, stdout=stdout)

    assert len(received) == 1
    assert received[0][0] == Hook.MCP_DISCONNECTED
    assert received[0][1].get("transport") == "stdio"


def test_mcp_http_emits_connected_and_tool_call_events() -> None:
    """HTTP: MCP_CONNECTED and MCP_TOOL_CALL_* are emitted."""

    received: list[tuple[str, dict]] = []

    class ProductMCP(MCP):
        @tool
        def search_products(self, query: str) -> str:
            return f"Results: {query}"

    mcp = ProductMCP()
    mcp.events.on(Hook.MCP_CONNECTED, lambda ctx: received.append(("connected", dict(ctx))))
    mcp.events.on(Hook.MCP_TOOL_CALL_START, lambda ctx: received.append(("start", dict(ctx))))
    mcp.events.on(Hook.MCP_TOOL_CALL_END, lambda ctx: received.append(("end", dict(ctx))))

    from fastapi import FastAPI
    from starlette.testclient import TestClient

    from syrin.mcp.http import build_mcp_router

    router = build_mcp_router(mcp)
    app = FastAPI()
    app.include_router(router, prefix="/mcp")
    client = TestClient(app)

    client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"clientInfo": {"name": "test"}},
        },
    )
    client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "search_products", "arguments": {"query": "x"}},
        },
    )

    assert len(received) >= 3
    assert received[0][0] == "connected"
    assert received[1][0] == "start"
    assert received[2][0] == "end"
    assert received[2][1]["tool_name"] == "search_products"
    assert received[2][1].get("result") == "Results: x"
