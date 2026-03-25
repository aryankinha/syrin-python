---
title: Built-in Tools
description: Pre-built tools that ship with Syrin for common agent capabilities.
weight: 72
---

## Built-In Superpowers

Why build a web search tool from scratch when you need search? Why write a calculator when you need math? Syrin ships with battle-tested tools for common use cases—tested in production, handling edge cases, optimized for performance.

```python
from syrin import Agent, Model
from syrin.tools import WebSearch, Calculator, DateTimeTool

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    system_prompt="You are a research assistant.",
    tools=[
        WebSearch(api_key="your-search-api-key"),
        Calculator(),
        DateTimeTool(),
    ],
)
```

**What just happened:** We added three commonly needed tools with a single line each. The agent can now search the web, do math, and get the current date/time.

## What's Available

### WebSearch

Search the web for current information:

```python
from syrin.tools import WebSearch

search = WebSearch(
    api_key="your-api-key",
    engine="google",        # or "bing", "duckduckgo"
    max_results=5,           # Limit results
    cache_ttl=3600,         # Cache for 1 hour
)
```

**What it does:** Takes a query string, returns a list of search results with titles, URLs, and snippets. Handles rate limiting and pagination automatically.

### Calculator

Evaluate mathematical expressions:

```python
from syrin.tools import Calculator

calc = Calculator(
    precision=10,           # Decimal places
    safe_mode=True,        # Block dangerous operations
)
```

**What it does:** Parses and evaluates math expressions. Supports basic operations, functions (sin, cos, log), and constants (pi, e).

### DateTimeTool

Get current date and time:

```python
from syrin.tools import DateTimeTool

dt = DateTimeTool(
    timezone="America/New_York",
    format="%Y-%m-%d %H:%M:%S",
)
```

**What it does:** Returns the current datetime in various formats. Useful for time-sensitive queries.

### FileRead

Read file contents:

```python
from syrin.tools import FileRead

reader = FileRead(
    allowed_dirs=["/data/docs"],  # Restrict to specific directories
    max_size=1024 * 1024,        # 1MB max
)
```

**What it does:** Safely reads text files with directory restrictions. Prevents path traversal attacks.

### FileWrite

Write content to files:

```python
from syrin.tools import FileWrite

writer = FileWrite(
    allowed_dir="/data/output",
    create_dirs=True,
)
```

**What it does:** Writes content to files with safety checks. Creates parent directories if needed.

### HTTPRequest

Make HTTP requests:

```python
from syrin.tools import HTTPRequest

http = HTTPRequest(
    timeout=30,
    headers={"User-Agent": "Syrin-Agent/1.0"},
    allowed_domains=["api.example.com"],
)
```

**What it does:** Performs HTTP GET/POST requests with rate limiting and domain restrictions.

### ImageAnalysis

Analyze images using vision models:

```python
from syrin.tools import ImageAnalysis

analyzer = ImageAnalysis(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    max_tokens=500,
)
```

**What it does:** Sends images to vision-capable models and returns descriptions. Supports URLs, base64, and file paths.

### WikipediaSearch

Search Wikipedia for encyclopedic information:

```python
from syrin.tools import WikipediaSearch

wiki = WikipediaSearch(
    language="en",
    max_results=3,
)
```

**What it does:** Searches Wikipedia's database for factual information. Returns summaries and links.

## Shared Configuration Options

All built-in tools share common configuration patterns:

```python
tool = SomeTool(
    name="custom_name",        # Override the default name
    description="Custom desc", # Override the default description
    requires_approval=True,    # Require human approval before execution
)
```

## Combining Tools

Chain tools for complex workflows:

```python
from syrin.tools import WebSearch, Calculator

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    tools=[
        WebSearch(),
        Calculator(),
    ],
    # The agent can now:
    # 1. Search for current data
    # 2. Perform calculations on results
    # 3. Search again with refined queries
)
```

**What just happened:** With both tools available, the agent can orchestrate multi-step workflows—searching for data, computing results, then searching for more based on those results.

## Watching Tool Execution

Monitor tool calls with hooks:

```python
agent.events.on("tool.call.start", lambda e: 
    print(f"Calling tool: {e['tool_name']}")
)

agent.events.on("tool.call.end", lambda e: 
    print(f"Tool {e['tool_name']} completed in {e['duration_ms']}ms")
)

agent.events.on("tool.error", lambda e: 
    print(f"Tool {e['tool_name']} failed: {e['error']}")
)
```

## Build Your Own

For specialized capabilities, create custom tools:

```python
from syrin import tool

@tool
def get_stock_price(symbol: str) -> str:
    """Get the current stock price for a given ticker symbol."""
    price = stock_api.get_price(symbol)
    return f"{symbol}: ${price:.2f}"
```

See [Tools](/agent/tools) for the complete guide to creating custom tools.

---

## What's Next?

- [Tools: TOON Schema](/agent/tools-toon) — Token-efficient tool definitions
- [Tools: Custom](/agent/tools) — Create your own tools
- [Agents: Tasks](/agent/tasks) — Structured agent methods

## See Also

- [Core Concepts: Memory](/core/memory) — Remember tool results
- [Integrations: MCP](/integrations/mcp) — Use Model Context Protocol tools
- [Debugging: Hooks Reference](/debugging/hooks-reference) — Tool-related hooks
