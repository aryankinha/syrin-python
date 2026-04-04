---
title: Tools
description: Give your agent real-world abilities — function calling, tool schemas, and TOON format
weight: 70
---

## What Are Tools?

An LLM by itself knows a lot, but it cannot do anything. It cannot check the weather. It cannot run a database query. It cannot send an email. It can only generate text.

Tools change that. A tool is a Python function your agent can call. The LLM decides when to call it and with what arguments. Syrin runs the function, captures the result, and feeds it back to the LLM. The LLM incorporates the result and either calls another tool or gives you a final answer.

This is the ReACT loop in action: Reason (what do I need?), Act (call the tool), Observe (here is the result), Reason again (what does this mean?).

## Defining a Tool

Decorate any Python function with `@tool`:

```python
from syrin import Agent, Model, tool

@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city.

    Args:
        city: The city name, e.g. 'Tokyo' or 'London'

    Returns:
        A string describing the current weather conditions.
    """
    weather_data = {"Tokyo": "Sunny, 22°C", "London": "Cloudy, 15°C", "NYC": "Rainy, 18°C"}
    return weather_data.get(city, f"No data for {city}")

print(f"Tool name:        {get_weather.name}")
print(f"Tool description: {get_weather.description}")
print(f"city description: {get_weather.parameters_schema['properties']['city']['description']}")
```

Output:

```
Tool name:        get_weather
Tool description: Get the current weather for a city.
city description: The city name, e.g. 'Tokyo' or 'London'
```

`@tool` reads four things from your function automatically:

| Source | What it reads |
|--------|---------------|
| Function name | Tool name shown to the LLM |
| First docstring line | Tool description — the LLM uses this to decide *when* to call it |
| `Args:` docstring section | Per-parameter descriptions — the LLM uses these to decide *what to pass* |
| `Returns:` docstring section | Return value description — the LLM uses this to interpret results |

The `Args:` and `Returns:` sections are standard Google-style Python docstrings — the same format used by IDEs, `help()`, and documentation generators. Zero extra syntax to learn.

## Documenting Without a Docstring

For functions that do not need a docstring (generated code, short lambdas, functions with obvious names), use the decorator keyword arguments instead. The result is identical to the docstring approach:

```python
from syrin import tool

@tool(
    description="Get the current weather for a city.",
    param_descriptions={
        "city": "The city name, e.g. 'Tokyo' or 'London'",
    },
    returns="A string describing the current weather conditions.",
    examples=[
        "get_weather('Tokyo')",
        "get_weather('London')",
    ],
)
def get_weather(city: str) -> str:
    weather_data = {"Tokyo": "Sunny, 22°C", "London": "Cloudy, 15°C"}
    return weather_data.get(city, f"No data for {city}")
```

**`description`** — the main tool description. What does it do? When should the LLM call it?

**`param_descriptions`** — a dict mapping each parameter name to its description. The LLM uses these to know what value to pass. Be specific: `"ISO 4217 currency code, e.g. 'USD' or 'EUR'"` is better than `"currency"`.

**`returns`** — what the tool returns. The LLM uses this to interpret the result. If your tool returns JSON, describe the keys: `"JSON with keys: title, url, snippet"`.

**`examples`** — 1–3 representative call patterns. The LLM uses these to pick arguments that match your intent beyond what type hints alone can express.

When both a docstring section and an explicit keyword argument are present, **the keyword argument always wins**. This lets you write full docstrings for your IDE while overriding just the LLM-facing text when needed.

## `depends_on` — Signal Tool Chaining

`depends_on` tells the LLM which tools are typically used *after* this one. This helps the LLM plan multi-step tool sequences:

```python
from syrin import tool

@tool(
    description="Search the web for current information.",
    examples=["search('latest AI news')", "search('Python 3.12 changes')"],
    depends_on=["summarise"],  # or pass the ToolSpec object: depends_on=[summarise_tool]
)
def search(query: str, max_results: int = 5) -> str:
    """Search the web."""
    return f"Results for: {query}"

@tool(
    description="Summarise a block of text into bullet points.",
    depends_on=[search],  # pass the ToolSpec directly — no string typos
)
def summarise(text: str) -> str:
    """Summarise text."""
    return f"Summary: {text[:50]}..."
```

`depends_on` accepts either tool names (strings) or `ToolSpec` objects directly. Use `ToolSpec` objects to get a compile-time error if you rename or delete a tool.

## Full Example: All Options Together

```python
from syrin import Agent, Model, tool

@tool(
    description="Search the web for current information on any topic.",
    param_descriptions={
        "query": "The search query. Use natural language or keywords.",
        "max_results": "Maximum number of results to return. Default: 5.",
    },
    returns="JSON array of objects, each with keys: title, url, snippet.",
    examples=[
        "search('latest AI news')",
        "search('Python 3.12 release notes', max_results=3)",
    ],
)
def search(query: str, max_results: int = 5) -> str:
    return f'[{{"title": "Result", "url": "https://...", "snippet": "{query}"}}]'

class ResearchAgent(Agent):
    model = Model.mock()
    system_prompt = "You are a research assistant."
    tools = [search]

agent = ResearchAgent()
response = agent.run("What are the latest developments in quantum computing?")
print(response.content[:60])
```

Output:

```
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed
```

## Giving Tools to an Agent

Pass tools in the `tools` list when defining your agent class or creating an instance:

```python
from syrin import Agent, Model, tool

@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city.

    Args:
        city: The city name
    """
    weather_data = {"Tokyo": "Sunny, 22°C", "London": "Cloudy, 15°C", "NYC": "Rainy, 18°C"}
    return weather_data.get(city, f"No data for {city}")

@tool
def calculate(expression: str) -> str:
    """Evaluate a simple math expression.

    Args:
        expression: A Python math expression like '2 + 2' or '10 * 3'

    Returns:
        The result as a string, or an error message.
    """
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"

class AssistantAgent(Agent):
    model = Model.mock()
    system_prompt = "You are a helpful assistant with weather and calculator abilities."
    tools = [get_weather, calculate]

agent = AssistantAgent()
print(f"Agent tools: {[t.name for t in agent.tools]}")
response = agent.run("What is the weather in Tokyo and what is 15 * 8?")
print(f"Response: {response.content[:60]}")
```

Output:

```
Agent tools: ['get_weather', 'calculate']
Response: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed
```

With a real model, the agent calls `get_weather("Tokyo")` and `calculate("15 * 8")`, gets the results, and incorporates them into its final response. With the mock model, the mock returns placeholder text — but the tool registration and schema generation work correctly.

## Tools From Class Methods

Define tools as methods on a helper class when your tools share state (database connections, API clients, configuration):

```python
from syrin import Agent, Model, tool

class WeatherTools:
    def __init__(self, api_key: str):
        self.api_key = api_key

    @tool
    def get_current_weather(self, city: str) -> str:
        """Get current weather for a city.

        Args:
            city: The city name
        """
        return f"Weather in {city}: Sunny, 22°C"

    @tool
    def get_forecast(self, city: str, days: int = 7) -> str:
        """Get a multi-day weather forecast.

        Args:
            city: The city name
            days: Number of forecast days
        """
        return f"{days}-day forecast for {city}: Mix of sun and clouds"

weather = WeatherTools(api_key="secret-key-123")

class WeatherAgent(Agent):
    model = Model.mock()
    system_prompt = "You provide weather information."
    tools = [weather]  # Pass the instance — Syrin binds the methods
```

Syrin calls `weather.get_current_weather` and `weather.get_forecast` as bound methods, so `self.api_key` is always available.

## Inheritance Merges Tools

Tools from parent classes are merged when you inherit:

```python
from syrin import Agent, Model, tool

@tool
def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"Sunny in {city}"

@tool
def translate(text: str, target: str) -> str:
    """Translate text.

    Args:
        text: Text to translate
        target: Target language code, e.g. 'fr' or 'es'
    """
    return f"[{target}] {text}"

class BaseAgent(Agent):
    model = Model.mock()
    tools = [get_weather]

class EnhancedAgent(BaseAgent):
    tools = [translate]  # Added — does NOT replace get_weather

agent = EnhancedAgent()
print(f"Tools: {[t.name for t in agent.tools]}")
```

Output:

```
Tools: ['get_weather', 'translate']
```

## Runtime Tool Management

Enable and disable tools after the agent is created:

```python
from syrin import Agent, Model, tool

@tool
def expensive_search(query: str) -> str:
    """Run an expensive semantic search."""
    return f"Search results for: {query}"

agent = Agent(model=Model.mock(), system_prompt="You are helpful.", tools=[expensive_search])

agent.disable_tool("expensive_search")
print(f"Active tools: {[t.name for t in agent.tools]}")

agent.enable_tool("expensive_search")
print(f"Active tools: {[t.name for t in agent.tools]}")
```

## TOON Format: 40-46% Fewer Tokens

Every tool definition sent to an LLM costs tokens. Syrin uses TOON (Token-Oriented Object Notation) — a compact schema format that carries the same information in significantly fewer characters.

```python
import json
from syrin import tool

@tool
def calculate(a: float, b: float, operation: str = "add") -> str:
    """Perform basic arithmetic.

    Args:
        a: First number
        b: Second number
        operation: One of add, subtract, multiply, divide
    """
    ops = {"add": a + b, "subtract": a - b, "multiply": a * b, "divide": a / b if b else 0}
    return str(ops.get(operation, "Unknown"))

json_schema = json.dumps(calculate.parameters_schema, indent=2)
toon_schema = calculate.schema_to_toon()
savings = ((len(json_schema) - len(toon_schema)) / len(json_schema)) * 100

print(f"JSON schema: {len(json_schema)} chars")
print(f"TOON schema: {len(toon_schema)} chars")
print(f"Savings: {savings:.1f}%")
```

Output:

```
JSON schema: 318 chars
TOON schema: 155 chars
Savings: 51.3%
```

You do not have to do anything to get this benefit — Syrin uses TOON by default.

## Tool Error Handling

By default, exceptions inside a `@tool` function propagate immediately. Use `AgentConfig.tool_error_mode` to change this:

```python
from syrin import Agent, AgentConfig, Model, tool
from syrin.enums import ToolErrorMode

@tool
def flaky_api(query: str) -> str:
    """Call an unreliable API."""
    raise ConnectionError("API unavailable")

agent = Agent(
    model=Model.mock(),
    system_prompt="You are helpful.",
    tools=[flaky_api],
    config=AgentConfig(tool_error_mode=ToolErrorMode.RETURN_AS_STRING),
)
# The agent receives the error as a string and can inform the user.
response = agent.run("Query the API for 'weather'")
```

| Mode | Behaviour |
|------|-----------|
| `ToolErrorMode.PROPAGATE` | **Default.** Re-raise immediately. Best during development — crashes loudly. |
| `ToolErrorMode.RETURN_AS_STRING` | Return the error as a string to the LLM. The agent handles it or informs the user. Good for production. |
| `ToolErrorMode.STOP` | Raise `ToolExecutionError` to the caller. Use when you want explicit error handling in your own code. |

## Tool Result Limits

Syrin truncates tool results over `max_tool_result_length` (default: 10,000 characters):

```python
agent = Agent(
    model=Model.mock(),
    system_prompt="You are helpful.",
    max_tool_result_length=2000,
)
```

## Human Approval for Tool Calls

For sensitive tools (sending emails, making purchases, modifying databases), require human approval before execution with `requires_approval=True`. More on this in [Human-in-the-Loop](/agent-kit/multi-agent/human-in-loop).

## MCP Tools

Syrin supports the Model Context Protocol (MCP). Any MCP server's tools become first-class Syrin tools with one line:

```python
from syrin import MCPClient

client = MCPClient(url="http://localhost:8080")
agent = Agent(
    model=Model.mock(),
    system_prompt="You are helpful.",
    tools=[client],
)
```

More on MCP in [MCP Client](/agent-kit/integrations/mcp-client).

## What's Next

- [TOON Format](/agent-kit/agent/tools-toon) — Deep dive into TOON and its token savings
- [Structured Output](/agent-kit/agent/structured-output) — Typed responses alongside tools
- [Hooks](/agent-kit/debugging/hooks) — Subscribe to `TOOL_CALL_START` and `TOOL_CALL_END` events
- [Human-in-the-Loop](/agent-kit/multi-agent/human-in-loop) — Require approval before tool execution
