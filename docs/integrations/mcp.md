---
title: MCP (Model Context Protocol)
description: A standard protocol for AI tool discovery and execution
weight: 180
---

## The Tool Fragmentation Problem

Imagine you've built an amazing product search tool for your AI agent. You want to share it with other developers. How do you do it?

You could:
- Write documentation and hope they implement it correctly
- Share code and hope they integrate it properly
- Create an API, but then they need to understand your data model

This is the **tool fragmentation problem**. Every AI framework has its own way of defining tools. Tools built for one framework don't work with another. Developers waste time reimplementing the same functionality.

## What is MCP?

The **Model Context Protocol (MCP)** is a standardized protocol for AI tool discovery and execution. Think of it as **USB for AI tools** — a common interface that lets any MCP-compatible tool work with any MCP-compatible agent.

Just as USB standardized hardware connections, MCP standardizes the connection between AI agents and tools. With MCP:

- **Tool creators** define tools once using the MCP specification
- **Agent developers** connect to any MCP server without reimplementation
- **Users** can mix and match tools from different sources

## Why MCP Matters

### Before MCP: Tool Chaos

Without MCP, each framework needs its own integration:

- Your Agent (Framework A) connects via Custom API to Your Product Tool
- Other Agent (Framework B) connects via Different API to Same Tool (reimplemented)
- Third Agent (Framework C) connects via Another API to Same Tool (reimplemented again)

Each tool needed custom integration code for each framework. Tool creators spent more time on integration than on making the tool better.

### After MCP: Tool Interoperability

With MCP, one implementation works everywhere:

- MCP Server hosts your tool
- Multiple agents connect via the same MCP Protocol
- Your Agent, Other Agent, and Third Agent can all use the same tool

The tool creator focuses on making the tool better. The agent frameworks just implement MCP.

## How MCP Works

MCP uses **JSON-RPC 2.0** for communication. It's a simple request/response protocol:

1. **Discovery**: The agent asks the server "what tools do you have?"
2. **Schema**: The server responds with tool names, descriptions, and parameter schemas
3. **Execution**: The agent calls a tool by name with parameters
4. **Result**: The server executes the tool and returns the result

### The Three Operations

MCP defines three core operations, all sent from the client to the server. `initialize` establishes the connection and negotiates the protocol version. `tools/list` discovers the tools available on the server. `tools/call` executes a specific tool by name with the provided parameters.

### Transport Options

MCP can run over different transports:

- **HTTP**: REST-style over HTTP POST. Good for web-based deployments.
- **STDIO**: JSON-RPC over standard input/output. Good for local subprocess integration.

Syrin supports both transports transparently.

## Why MCP Works

MCP succeeds because it solves the right problem at the right layer:

1. **Simplicity**: Three operations cover 90% of tool use cases
2. **Standardization**: JSON-RPC 2.0 is well-understood and widely supported
3. **Extensibility**: Additional operations can be added without breaking compatibility
4. **Tool autonomy**: Tools maintain their own logic and data; MCP just provides the interface

The key insight is that **MCP doesn't try to be everything**. It's a thin layer for discovery and invocation. The actual tool logic stays where it belongs — in the tool itself.

## Syrin's MCP Implementation

Syrin provides two components for MCP. `MCP` is the base class for creating MCP servers — subclass it and decorate methods with `@tool` to expose them. `MCPClient` is the client for connecting to remote MCP servers, enabling your agents to use tools from any MCP-compatible endpoint.

### MCP Server

Create tools by subclassing `MCP` and using the `@tool` decorator:

```python
from syrin import MCP, tool

class ProductMCP(MCP):
    @tool
    def search_products(self, query: str, limit: int = 10) -> str:
        """Search the product catalog."""
        # Your implementation here
        return results
```

### MCP Client

Connect to any MCP server with a single line:

```python
from syrin import MCPClient

mcp = MCPClient("http://localhost:3000/mcp")
agent = Agent(tools=[*mcp.tools()])
```

## Co-location: Best of Both Worlds

Syrin's MCP implementation supports **co-location** — when you place an MCP instance in an agent's tools, the agent automatically:

- Mounts an `/mcp` route on its HTTP server
- Exposes a discovery endpoint for remote agents
- Shares tools with local and remote consumers

```python
agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    tools=[ProductMCP()],  # Co-located MCP
)

# Agent now has /chat AND /mcp endpoints
# Remote clients can discover and use these tools
```

## What You Can Customize

With Syrin's MCP implementation, you can customize:

- **Tool implementations**: Add any Python logic with `@tool`
- **Transport**: HTTP for web, STDIO for subprocess
- **Security**: Add guardrails for input/output validation
- **Audit**: Log all tool calls with AuditLog integration
- **Tool selection**: Use `.select()` to expose only specific tools

## Hooks for MCP

MCP emits lifecycle hooks you can subscribe to:

```python
def on_mcp_connected(ctx):
    print(f"MCP connected: {ctx}")

def on_tool_call(ctx):
    print(f"Tool {ctx.tool_name} called")

def on_tool_result(ctx):
    print(f"Tool {ctx.tool_name} completed")

agent.events.on(Hook.MCP_CONNECTED, on_mcp_connected)
agent.events.on(Hook.MCP_TOOL_CALL_START, on_tool_call)
agent.events.on(Hook.MCP_TOOL_CALL_END, on_tool_result)
```

## What's Next?

- [Create an MCP Server](/agent-kit/integrations/mcp-server) — Build your first MCP server
- [Connect to Remote MCP Servers](/agent-kit/integrations/mcp-client) — Use tools from other sources
- [Tools Reference](/agent-kit/agent/tools) — Learn about the @tool decorator

## See Also

- [Agent Tools](/agent-kit/agent/tools) — Defining tools for agents
- [Hooks System](/agent-kit/debugging/hooks) — Reacting to lifecycle events
- [Audit Logging](/agent-kit/debugging/logging) — Tracking tool calls
