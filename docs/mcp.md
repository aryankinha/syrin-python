# MCP — Model Context Protocol

Syrin integrates MCP (Model Context Protocol) so agents can consume MCP servers as tool sources. Use `syrin.MCP` to define MCP servers declaratively and `syrin.MCPClient` to connect to remote MCP servers.

**Requires:** `uv pip install syrin[serve]` for HTTP serving; `httpx` for MCPClient (included with syrin).

## syrin.MCP — Declarative MCP Server

Define tools with `@tool` inside the MCP class, same as Agent.

### Standalone serving

Serve MCP independently (without an Agent):

```python
mcp = ProductMCP()
mcp.serve(port=3000)           # HTTP at http://localhost:3000/mcp
mcp.serve(stdin=sys.stdin)     # STDIO (JSON-RPC over stdin/stdout)
```

Transport is inferred: pass `stdin` for STDIO, otherwise HTTP. Requires `syrin[serve]` for HTTP.

```python
from syrin import Agent, MCP, tool
from syrin.model import Model

class ProductMCP(MCP):
    name = "product-mcp"
    description = "Product catalog tools for e-commerce"

    @tool
    def search_products(self, query: str, limit: int = 10) -> str:
        """Search the product catalog by query."""
        return catalog.search(query, limit)

    @tool
    def get_product(self, product_id: str) -> str:
        """Get product details by ID."""
        return catalog.get(product_id)

mcp = ProductMCP()
mcp.tools()      # [ToolSpec(search_products), ToolSpec(get_product)]
mcp.select("search_products")  # [ToolSpec(search_products)]
```

## syrin.MCPClient — Consume Remote MCP Servers

Connect to a remote MCP server and expose its tools for agents:

```python
from syrin import Agent, MCPClient
from syrin.model import Model

# All tools from remote MCP
shopify_mcp = MCPClient("https://mcp.shopify.com")

# Or whitelist at connection time
shopify_mcp = MCPClient("https://mcp.shopify.com", tools=["search_products", "get_product"])

class ShopAgent(Agent):
    model = Model.Almock()
    tools = [
        shopify_mcp,                                    # All tools
        shopify_mcp.select("search_products", "get_product"),  # Or pick specific tools
    ]
```

## Agent Consuming MCP — Patterns

**1. Direct inclusion** — Agent gets all MCP tools:
```python
tools = [product_mcp]
```

**2. `.select(toolName1, toolName2)`** — Agent gets only selected tools:
```python
tools = [product_mcp.select("search_products", "get_product")]
```

**3. `.tools()`** — Spread into agent's tools:
```python
tools = [*product_mcp.tools()]
```

## Co-location — MCP with Agent on Same Port

When an MCP instance is in `Agent(tools=[...])`, the serve layer auto-mounts `/mcp` alongside `/chat`:

```python
product_mcp = ProductMCP()

class ProductAgent(Agent):
    name = "product-agent"
    description = "E-commerce product search"
    model = Model.Almock()
    tools = [product_mcp, my_add_to_cart_tool]

ProductAgent().serve(port=8000)
# POST /chat          → Agent endpoint
# POST /stream        → SSE streaming
# POST /mcp           → MCP server (tools/list, tools/call)
# GET  /.well-known/agent.json  → A2A Agent Card
```

All served from one process, one port.

## MCP JSON-RPC

The `/mcp` endpoint speaks JSON-RPC 2.0:

- `tools/list` — Returns list of tools with name, description, inputSchema
- `tools/call` — Executes a tool: `{"name": "search_products", "arguments": {"query": "shoes"}}`

## MCP lifecycle events

MCP emits lifecycle events you can subscribe to:

```python
from syrin import MCP
from syrin.enums import Hook

mcp = ProductMCP()
mcp.events.on(Hook.MCP_CONNECTED, lambda ctx: print(f"Client connected: {ctx.params}"))
mcp.events.on(Hook.MCP_TOOL_CALL_START, lambda ctx: print(f"Tool: {ctx.tool_name}"))
mcp.events.on(Hook.MCP_TOOL_CALL_END, lambda ctx: print(f"Done: {ctx.get('result') or ctx.get('error')}"))
mcp.events.on(Hook.MCP_DISCONNECTED, lambda ctx: print("Client disconnected"))
```

| Hook | When | Context |
|------|------|---------|
| `MCP_CONNECTED` | Client sends `initialize` | `method`, `params` |
| `MCP_TOOL_CALL_START` | Before `tools/call` execution | `tool_name`, `arguments` |
| `MCP_TOOL_CALL_END` | After `tools/call` | `tool_name`, `arguments`, `result` or `error` |
| `MCP_DISCONNECTED` | STDIO EOF (STDIO only) | `transport` |

## Examples

- `examples/11_mcp/mcp_server_class.py` — syrin.MCP with @tool
- `examples/11_mcp/mcp_standalone_serve.py` — Standalone serve (HTTP/STDIO) + MCP lifecycle events
- `examples/11_mcp/mcp_colocation.py` — MCP co-located with agent
