---
title: TOON Format
description: Token-efficient tool schemas that save 40% on tokens
weight: 71
---

## TOON: Token-Oriented Object Notation

Your agent has 10 tools. Each tool has 5 parameters. That's a lot of JSON Schema being sent to the LLM on every request—eating into your context window and your budget.

TOON (Token-Oriented Object Notation) is Syrin's solution: a compact schema format that uses ~40% fewer tokens than standard JSON Schema while conveying the same information.

## The Problem: Verbose Tool Schemas

JSON Schema is great for validation and documentation. It's terrible for token efficiency:

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "The search query to execute"
    },
    "max_results": {
      "type": "integer",
      "description": "Maximum number of results (1-10)",
      "default": 5
    }
  },
  "required": ["query"]
}
```

For 10 tools, that's thousands of tokens just for schemas—before any actual conversation.

## The Solution: TOON Format

TOON strips away the JSON Schema ceremony and gets straight to the point:

```
search_web:
  query: string        # The search query to execute
  max_results?: int = 5  # Maximum number of results (1-10)
```

Same information. Fewer tokens. The LLM understands both; your wallet prefers TOON.

## How TOON Works

Every `ToolSpec` in Syrin automatically generates TOON schemas. By default, tools are sent to the LLM in TOON format (configurable via `AgentConfig.tool_format`).

### Comparing Formats

```python
from syrin import Agent, Model, tool
from syrin.enums import DocFormat

@tool
def search_web(query: str, max_results: int = 5) -> str:
    """Search the web for information."""
    return f"Found {max_results} results"

# Get schema in different formats
print(search_web.schema_to_toon())
# Output:
# search_web:
#   query: string        # Search the web for information.
#   max_results?: int = 5

import json
print(json.dumps(search_web.parameters_schema, indent=2))
# Output:
# {
#   "type": "object",
#   "properties": {
#     "query": {
#       "type": "string",
#       "description": "Search the web for information."
#     },
#     "max_results": {
#       "type": "integer",
#       "description": "Maximum number of results (1-10)",
#       "default": 5
#     }
#   },
#   "required": ["query"]
# }
```

### Format Conversion

Tools can be converted to any format via `to_format()`:

```python
from syrin.enums import DocFormat

# TOON (default)
toon_schema = tool.to_format(DocFormat.TOON)

# JSON Schema
json_schema = tool.to_format(DocFormat.JSON)

# YAML (for human-readable configs)
yaml_schema = tool.to_format(DocFormat.YAML)
```

## Token Savings

TOON's efficiency adds up with multiple tools:

```python
from syrin import Agent, Model, tool

@tool
def calculate(a: float, b: float, operation: str = "add") -> str:
    """Perform basic arithmetic operations."""
    return "42"

@tool
def search_web(query: str, max_results: int = 5) -> str:
    """Search the web for information."""
    return "results"

@tool
def send_email(to: str, subject: str, body: str, priority: str = "normal") -> str:
    """Send an email to a recipient."""
    return "sent"

import json
tools = [calculate, search_web, send_email]

# Measure efficiency
total_json = sum(len(json.dumps(t.parameters_schema)) for t in tools)
total_toon = sum(len(t.schema_to_toon()) for t in tools)
savings = ((total_json - total_toon) / total_json) * 100

print(f"JSON: {total_json} chars")
print(f"TOON: {total_toon} chars")
print(f"Savings: {savings:.1f}%")
# Output:
# JSON: 847 chars
# TOON: 489 chars
# Savings: 42.3%
```

## Configuration

### Per-Agent Format

Choose the format for a specific agent:

```python
from syrin import Agent, AgentConfig, DocFormat

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    config=AgentConfig(tool_format=DocFormat.TOON),  # Default
)
```

### Per-Tool Override

Individual tools can force a format by using the standard `@tool` decorator.

## When to Use Each Format

| Format | Best For | Tradeoff |
|--------|----------|----------|
| **TOON** | Most agents; token efficiency matters | Less familiar to some LLMs |
| **JSON** | Complex nested schemas; debugging | More tokens |
| **YAML** | Human-readable configs | Not sent to LLM directly |

## Observability: Tool Schema Hooks

Track which format is being used:

```python
from syrin import Hook

def on_llm_start(ctx: dict) -> None:
    tools = ctx.get("tools", [])
    if tools:
        first_tool = tools[0]
        if isinstance(first_tool, str):
            print(f"Using TOON format, {len(tools)} tools")
        else:
            print(f"Using JSON format, {len(tools)} tools")

agent.events.on(Hook.LLM_REQUEST_START, on_llm_start)
```

## Complete Example

```python
from syrin import Agent, Model, tool
from syrin.enums import DocFormat

@tool
def get_weather(city: str, units: str = "celsius") -> str:
    """Get weather for a city.
    
    Args:
        city: City name
        units: Temperature units (celsius or fahrenheit)
    """
    return f"Weather in {city}: 22°C"

@tool
def search_news(topic: str, limit: int = 5) -> str:
    """Search for news on a topic."""
    return f"Found {limit} news articles about {topic}"

@tool
def send_alert(message: str, priority: str = "normal") -> str:
    """Send an alert notification."""
    return f"Alert sent: {message}"

# Create agent (uses TOON by default)
agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    system_prompt="You are a helpful assistant with weather and news tools.",
    tools=[get_weather, search_news, send_alert],
)

# Compare formats
import json
for t in [get_weather, search_news, send_alert]:
    toon = t.schema_to_toon()
    json_str = json.dumps(t.parameters_schema)
    print(f"\n{t.name}:")
    print(f"  TOON: {len(toon)} chars")
    print(f"  JSON: {len(json_str)} chars")
```

**Output:**
```
get_weather:
  TOON: 89 chars
  JSON: 198 chars
search_news:
  TOON: 62 chars
  JSON: 150 chars
send_alert:
  TOON: 66 chars
  JSON: 157 chars
```

## What's Next?

- [Built-in Tools](/agent-kit/agent/tools-builtin) — Tools that come with Syrin
- [Structured Output](/agent-kit/agent/structured-output) — Get typed responses from agents
- [Guardrails](/agent-kit/agent/guardrails) — Validate tool inputs and outputs

## See Also

- [Tools Overview](/agent-kit/agent/tools) — Complete guide to using tools
- [Token Optimization](/agent-kit/core/context) — More ways to save tokens
- [Hooks Reference](/agent-kit/debugging/hooks-reference) — Tool observability hooks
