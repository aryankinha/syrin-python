# MCP Examples

Examples for syrin.MCP (declarative MCP server) and syrin.MCPClient (remote MCP consumer).

## Files

- **mcp_server_class.py** — Define MCP with `@tool`, use `.tools()` and `.select()`
- **mcp_standalone_serve.py** — Serve MCP independently: `mcp.serve(port=3000)` or `mcp.serve(stdin=sys.stdin)`
- **mcp_colocation.py** — MCP in agent tools → `/mcp` and `/.well-known/agent.json` auto-mounted

**Note:** Product tools return mock catalog data. Stub responses like `"Results for 'shoes'"` with no product details cause LLM tool-call loops and hallucinated results. These examples return structured mock data to avoid that; replace with real search in production.

## MCPClient

To use MCPClient, you need a running MCP server. Start `mcp_colocation.py` first, then:

```python
from syrin import Agent, MCPClient

mcp = MCPClient("http://localhost:8000/mcp")
agent = Agent(model=..., tools=[mcp.select("search_products")])
```

## See Also

- `docs/mcp.md` — Full MCP documentation
- `docs/serving.md` — Agent discovery, routes, ServeConfig
