---
title: MCP Client
description: Connect agents to remote MCP servers
weight: 182
---

## Consuming Remote MCP Servers

You know how to create MCP servers. Now let's consume them. The `MCPClient` lets your agents use tools from any MCP-compatible server.

## The Problem We're Solving

You've built a great agent. Now you want it to access:

- A company's internal product catalog (built by another team)
- A weather service (from a third-party provider)
- A code search tool (from yet another team)

Without MCP, you'd need to:
1. Get API documentation from each provider
2. Write custom integration code
3. Handle authentication differently for each
4. Update your code when providers change their APIs

With MCP, you connect to each server with one line of code.

## Your First MCP Client

```python
from syrin import Agent, MCPClient, Model

# Connect to a remote MCP server
mcp = MCPClient("http://localhost:3000/mcp")

# Create an agent that uses the remote tools
agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    tools=[*mcp.tools()],  # Spread tools from MCP server
)
```

**What just happened?**

1. `MCPClient` connected to the remote server
2. It fetched the list of available tools via `tools/list`
3. The tools are converted to Syrin `ToolSpec` format
4. The agent can now use them as if they were local tools

## How Tool Discovery Works

When you call `mcp.tools()`, the client:

1. Sends a JSON-RPC request to the server:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```

2. Receives the tool definitions:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "search_products",
        "description": "Search products by query",
        "inputSchema": {
          "type": "object",
          "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 10}
          },
          "required": ["query"]
        }
      }
    ]
  }
}
```

3. Converts each tool to a Syrin `ToolSpec`
4. Returns the list for use in your agent

## Lazy Discovery

Tool discovery happens on first use, not on client creation:

```python
mcp = MCPClient("http://localhost:3000/mcp")

# No network call yet
# Discovery happens here
tools = mcp.tools()
# Now we know what tools exist
```

This means:
- You can create clients without a server running
- Discovery happens when you actually need the tools
- Errors are caught at usage time, not connection time

## Selective Tool Usage

Don't want to expose all tools? Use `.select()`:

```python
mcp = MCPClient("http://localhost:3000/mcp")

# Only use specific tools
agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    tools=mcp.select('search_products', 'get_product'),
)
```

This is useful when:
- Some tools require different permissions
- You want to limit what users can access
- Different agents need different subsets

## Configuration Options

The `MCPClient` constructor accepts several options:

```python
mcp = MCPClient(
    url="http://localhost:3000/mcp",
    tools=["search_products"],  # Whitelist specific tools
    timeout=30.0,              # HTTP timeout in seconds
    headers={"Authorization": "Bearer token"},  # Custom headers
)
```

### Custom Headers

Pass authentication tokens or other headers:

```python
mcp = MCPClient(
    "https://api.example.com/mcp",
    headers={
        "Authorization": f"Bearer {get_api_token()}",
        "X-Client-Version": "1.0",
    },
)
```

### Timeout Configuration

Control how long to wait for responses:

```python
# 30 seconds default
mcp = MCPClient("http://localhost:3000/mcp", timeout=30.0)

# 60 seconds for slow operations
mcp = MCPClient("http://localhost:3000/mcp", timeout=60.0)
```

## Tool Filtering at Creation

You can whitelist tools at client creation:

```python
# Only these tools will be available
mcp = MCPClient(
    "http://localhost:3000/mcp",
    tools=["search_products", "check_inventory"],
)

# .tools() only returns whitelisted
print([t.name for t in mcp.tools()])
# Output: ['search_products', 'check_inventory']
```

This is different from `.select()`:
- **Constructor `tools`**: Filters at creation time (discovery)
- **`.select()`**: Filters after discovery

## Combining Multiple MCP Servers

Your agent can use tools from multiple MCP servers:

```python
from syrin import Agent, MCPClient, Model

# Connect to multiple servers
products = MCPClient("http://localhost:3001/mcp")
weather = MCPClient("http://localhost:3002/mcp")
calendar = MCPClient("http://localhost:3003/mcp")

# Combine all tools
all_tools = [*products.tools(), *weather.tools(), *calendar.tools()]

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    tools=all_tools,
)
```

The agent now has access to tools from three different servers!

## Error Handling

MCPClient propagates server errors:

```python
mcp = MCPClient("http://localhost:3000/mcp")

try:
    tools = mcp.tools()
except RuntimeError as e:
    print(f"MCP error: {e}")
```

Common errors:

| Error | Cause | Solution |
| --- | --- | --- |
| Connection refused | Server not running | Start the MCP server |
| Timeout | Server too slow | Increase `timeout` |
| Unknown tool | Tool not found | Check server capabilities |
| Invalid parameters | Wrong arguments | Check tool schema |

## Real-World Example

Here's a customer support agent using multiple MCP servers:

```python
from syrin import Agent, MCPClient, Model

class SupportAgent(Agent):
    _agent_name = "support-agent"
    
    # Internal tools
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")
    system_prompt = """You are a customer support agent. 
    Use the product search to find items.
    Use the order lookup to check status.
    Use the knowledge base to answer questions."""
    
    # Remote MCP servers
    tools = [
        *MCPClient("http://catalog.internal/mcp").tools(),
        *MCPClient("http://orders.internal/mcp").tools(),
        *MCPClient("http://kb.internal/mcp").tools(),
    ]
```

Now the agent can:
- Search products from the catalog server
- Check order status from the orders server
- Answer questions from the knowledge base

All without any custom integration code.

## MCP Client vs Direct API Calls

When should you use MCPClient vs direct API calls?

| Use MCPClient | Use Direct API |
| --- | --- |
| Tool is MCP-compatible | Custom protocol |
| Standard interface needed | Performance critical |
| Tool may change | Full control needed |
| Multiple consumers | Single purpose |

## Debugging MCP Connections

Check what's happening with verbose output:

```python
import logging
logging.getLogger("syrin.mcp").setLevel(logging.DEBUG)

mcp = MCPClient("http://localhost:3000/mcp")
tools = mcp.tools()  # See debug logs
```

## What's Next?

- [Knowledge Pool](/integrations/knowledge-pool) — Add RAG to your agents
- [Grounding](/integrations/grounding) — Verify facts and cite sources
- [Agent Tools](/agent/tools) — Define your own tools

## See Also

- [MCP Overview](/integrations/mcp) — Protocol concepts
- [MCP Server](/integrations/mcp-server) — Create MCP servers
- [Tools Reference](/agent/tools) — Tool definitions
