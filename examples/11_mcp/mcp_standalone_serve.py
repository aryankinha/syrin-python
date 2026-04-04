"""MCP Standalone Serve Example.

Demonstrates:
- mcp.serve(port=3000) — HTTP transport (default)
- mcp.serve(stdin=sys.stdin) — STDIO transport
- mcp.events — MCP lifecycle hooks (MCP_CONNECTED, MCP_TOOL_CALL_*, MCP_DISCONNECTED)

Requires: uv pip install syrin[serve] for HTTP

Run HTTP: python -m examples.11_mcp.mcp_standalone_serve
Run STDIO: echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python -m examples.11_mcp.mcp_standalone_serve --stdio
"""

from __future__ import annotations

import argparse
import sys

from syrin import MCP, tool
from syrin.enums import Hook

# Demo mock catalog — replace with real search in production.
# Returning structured data prevents LLM loop (keeps calling) and hallucination (inventing results).
_MOCK_CATALOG = [
    {
        "id": "s1",
        "name": "Nike Air Max 270",
        "price": 150,
        "description": "Stylish sneaker for casual wear.",
    },
    {
        "id": "s2",
        "name": "Adidas Ultraboost",
        "price": 180,
        "description": "Comfortable running shoe.",
    },
    {"id": "s3", "name": "Vans Old Skool", "price": 60, "description": "Iconic skate shoe."},
]


class ProductMCP(MCP):
    name = "product-mcp"
    description = "Product catalog tools"

    @tool
    def search_products(self, query: str, limit: int = 10) -> str:
        """Search the product catalog. Returns product id, name, price, description."""
        items = _MOCK_CATALOG[:limit]
        lines = [f"- {p['name']} (id={p['id']}): ${p['price']} — {p['description']}" for p in items]
        return f"Results for '{query}' (limit={limit}):\n" + "\n".join(lines)

    @tool
    def get_product(self, product_id: str) -> str:
        """Get product by ID."""
        for p in _MOCK_CATALOG:
            if p["id"] == product_id:
                return f"{p['name']}: ${p['price']} — {p['description']}"
        return f"Product {product_id} not found."


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdio", action="store_true", help="Use STDIO transport instead of HTTP")
    parser.add_argument("--port", type=int, default=3000, help="HTTP port (default 3000)")
    args = parser.parse_args()

    mcp = ProductMCP()
    # MCP lifecycle events — subscribe to connection, tool calls, disconnection
    mcp.events.on(
        Hook.MCP_CONNECTED,
        lambda ctx: print(
            f"  [MCP] Client connected: {ctx.get('params', {}).get('clientInfo', {}).get('name', '?')}"
        ),
    )
    mcp.events.on(
        Hook.MCP_TOOL_CALL_START,
        lambda ctx: print(f"  [MCP] Tool call: {ctx.get('tool_name', '?')}"),
    )
    mcp.events.on(
        Hook.MCP_TOOL_CALL_END,
        lambda ctx: print(
            f"  [MCP] Tool done: {ctx.get('tool_name', '?')} — {'ok' if ctx.get('result') is not None else 'error'}"
        ),
    )
    # Disconnection event only works on STDIO server; HTTP doesn't support it.
    mcp.events.on(Hook.MCP_DISCONNECTED, lambda _: print("  [MCP] Client disconnected"))

    if args.stdio:
        mcp.serve(stdin=sys.stdin, stdout=sys.stdout)
    else:
        print(f"MCP HTTP server at http://localhost:{args.port}/mcp")
        mcp.serve(port=args.port)
