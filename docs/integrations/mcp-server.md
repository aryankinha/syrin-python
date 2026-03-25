---
title: MCP Server
description: Create MCP servers with the syrin.MCP base class
weight: 181
---

## Building Your First MCP Server

You've learned what MCP is. Now let's build one. An MCP server is simply a collection of tools that can be discovered and called by any MCP-compatible client.

In this guide, you'll create a product catalog MCP server from scratch.

## The Problem We're Solving

Let's say you run an e-commerce platform. You want AI agents to be able to:

- Search your product catalog
- Get product details
- Check inventory
- Get pricing information

Without MCP, you'd need to:
1. Build a REST API
2. Document the API
3. Help each AI framework integrate with it
4. Maintain multiple integrations

With MCP, you define the tools once. Any MCP-compatible agent can use them.

## Your First MCP Server

```python
from syrin import MCP, tool

class ProductMCP(MCP):
    name = "product-catalog"
    description = "Product catalog search and information"
    
    @tool
    def search_products(self, query: str, limit: int = 10) -> str:
        """Search products by name, category, or description."""
        # In production, this queries your actual database
        return f"Found products matching '{query}': [list of items]"
    
    @tool
    def get_product(self, product_id: str) -> str:
        """Get detailed product information by ID."""
        return f"Product {product_id}: name, price, description, specs"
    
    @tool
    def check_inventory(self, product_id: str) -> str:
        """Check current inventory level for a product."""
        return f"Product {product_id}: 50 units in stock"
```

**What just happened?**

1. You created `ProductMCP` extending `MCP`
2. You defined `name` and `description` for discovery
3. You used `@tool` to mark methods as tools
4. Each tool has a docstring that becomes its description

## The @tool Decorator

The `@tool` decorator works the same way in MCP as it does for agents. It creates a `ToolSpec` with:

- **Name**: Method name (can be overridden)
- **Description**: From the docstring
- **Parameters**: From the function signature

```python
@tool
def search_products(
    self,
    query: str,           # Required parameter
    limit: int = 10,      # Optional with default
    category: str = None  # Optional, nullable
) -> str:
    """Search products. Returns list of matching items."""
    ...
```

## Accessing Tools

After creating the server, you can access its tools:

```python
mcp = ProductMCP()

# Get all tools
all_tools = mcp.tools()
print([t.name for t in all_tools])
# Output: ['search_products', 'get_product', 'check_inventory']

# Get specific tools
selected = mcp.select('search_products', 'get_product')
```

This is useful when you want to:
- Debug what tools are exposed
- Share only specific tools with certain agents
- Filter tools based on user permissions

## Serving the MCP Server

Once you have a server, you need to serve it. Syrin supports two transports:

### HTTP Transport

HTTP is best for web deployments:

```python
mcp = ProductMCP()
mcp.serve(port=3000, host="0.0.0.0")
```

The server starts at `http://localhost:3000/mcp`. Clients can:
- POST JSON-RPC requests to `/mcp`
- Get tool lists
- Execute tools

### STDIO Transport

STDIO is best for subprocess integration:

```python
import sys
mcp = ProductMCP()
mcp.serve(stdin=sys.stdin, stdout=sys.stdout)
```

This reads JSON-RPC messages from stdin and writes responses to stdout. Parent processes can communicate with the MCP server as a child process.

## Co-location with Agents

The most powerful feature is **co-location** — placing an MCP server inside an agent:

```python
class ProductAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")
    tools = [ProductMCP()]  # Co-located MCP
```

When you serve this agent:

```python
agent = ProductAgent()
agent.serve(port=8000)
```

The agent now exposes:

- `/chat` — Chat endpoint for the agent
- `/mcp` — MCP endpoint for the product tools

Remote agents can connect to your MCP server directly:

```python
# In another agent
mcp = MCPClient("http://localhost:8000/mcp")
agent = Agent(tools=[*mcp.tools()])
```

## Adding Security with Guardrails

You can add guardrails to validate tool inputs and outputs:

```python
from syrin.guardrails import GuardrailChain, ContentBlock

guardrail = GuardrailChain([
    ContentBlock(
        name="no_pii",
        check=pii_check,
    ),
])

mcp = ProductMCP(guardrails=guardrail)
```

Now every tool call goes through validation before and after execution.

## Adding Audit Logging

Track all tool calls for debugging and compliance:

```python
from syrin import AuditLog

audit = AuditLog(path="./product_audit.jsonl")
mcp = ProductMCP(audit=True, audit_log=audit)
```

Each tool call is logged with:
- Timestamp
- Tool name and parameters
- Execution result
- Duration

## MCP Lifecycle Hooks

Subscribe to MCP lifecycle events:

```python
def on_connect(ctx):
    print(f"Client connected from {ctx.client_info}")

def on_tool_start(ctx):
    print(f"Starting: {ctx.tool_name} with {ctx.arguments}")

def on_tool_end(ctx):
    print(f"Completed: {ctx.tool_name}")

agent.events.on(Hook.MCP_CONNECTED, on_connect)
agent.events.on(Hook.MCP_TOOL_CALL_START, on_tool_start)
agent.events.on(Hook.MCP_TOOL_CALL_END, on_tool_end)
```

## A Real-World Example

Here's a more complete product catalog MCP:

```python
from syrin import MCP, tool

_MOCK_DB = {
    "SKU001": {
        "name": "Wireless Mouse",
        "price": 29.99,
        "stock": 150,
        "description": "Ergonomic wireless mouse with USB receiver"
    },
    "SKU002": {
        "name": "Mechanical Keyboard",
        "price": 89.99,
        "stock": 45,
        "description": "RGB mechanical keyboard with Cherry MX switches"
    },
}

class ProductMCP(MCP):
    name = "product-catalog"
    description = "E-commerce product catalog"
    
    @tool
    def search_products(
        self,
        query: str,
        limit: int = 10,
        category: str | None = None
    ) -> str:
        """Search products by name or description."""
        results = []
        for sku, product in _MOCK_DB.items():
            if query.lower() in product["name"].lower():
                results.append({
                    "id": sku,
                    "name": product["name"],
                    "price": product["price"]
                })
            if len(results) >= limit:
                break
        return str(results)
    
    @tool
    def get_product(self, product_id: str) -> str:
        """Get full product details."""
        if product_id not in _MOCK_DB:
            return f"Product {product_id} not found"
        return str(_MOCK_DB[product_id])
    
    @tool
    def check_inventory(self, product_id: str) -> str:
        """Check current inventory level."""
        if product_id not in _MOCK_DB:
            return f"Product {product_id} not found"
        stock = _MOCK_DB[product_id]["stock"]
        return f"Product {product_id}: {stock} units in stock"
    
    @tool
    def get_price(self, product_id: str, quantity: int = 1) -> str:
        """Get price with quantity discount."""
        if product_id not in _MOCK_DB:
            return f"Product {product_id} not found"
        unit_price = _MOCK_DB[product_id]["price"]
        # Simple bulk discount
        if quantity >= 10:
            unit_price *= 0.9  # 10% off
        elif quantity >= 50:
            unit_price *= 0.8  # 20% off
        return f"Total: ${unit_price * quantity:.2f}"
```

## Testing Your MCP Server

Use the Syrin CLI to test:

```bash
# Test connection
syrin test --connection --url http://localhost:3000/mcp

# List tools
syrin list tools --url http://localhost:3000/mcp

# Analyze for issues
syrin analyse --url http://localhost:3000/mcp
```

## What's Next?

- [MCP Client](/integrations/mcp-client) — Connect to remote MCP servers
- [Tools Reference](/agent/tools) — Master the @tool decorator
- [Guardrails](/agent/guardrails) — Add input/output validation

## See Also

- [MCP Overview](/integrations/mcp) — Protocol concepts
- [Agent Tools](/agent/tools) — Tool definitions
- [Audit Logging](/debugging/logging) — Track tool calls
