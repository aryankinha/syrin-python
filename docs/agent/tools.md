---
title: Tools
description: Give your agents superpowers with function calling
weight: 70
---

## Your Agent's Superpowers

You've built an agent that can chat. Impressive. But can it search the web? Run code? Send emails? 

Without tools, your agent is just a very expensive autocomplete machine. Tools are how you transform a language model into a useful assistant that can actually *do* things.

## The Problem: LLMs Are Powerless

A raw LLM is like a brilliant researcher locked in a room with no internet, no calculator, and no way to verify facts. They can reason all day, but they can't:

- Look up today's stock price
- Calculate compound interest correctly
- Access your internal database
- Send notifications to your team

Tools solve this by giving your agent "hands" to interact with the real world.

## The Solution: @tool Decorator

Syrin's `@tool` decorator transforms any Python function into a tool your agent can call. The decorator automatically:

- Extracts the function name (or lets you override it)
- Generates parameter schemas from type hints
- Builds the tool specification for the model

```python
from syrin import Agent, Model, tool

# Define a tool with @tool decorator
@tool
def get_weather(city: str) -> str:
    """Get current weather for a city."""
    # In production, call a real weather API
    return f"Weather in {city}: Sunny, 72°F"

# Attach to an agent
agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    system_prompt="You are a helpful weather assistant.",
    tools=[get_weather],
)

result = agent.run("What's the weather in Tokyo?")
print(result.content)
# Agent sees you asked about Tokyo, calls get_weather(city="Tokyo"),
# and incorporates the result into its response.
```

**What just happened:** The `@tool` decorator wrapped your function into a `ToolSpec` that tells the LLM:
1. The tool exists and is named `get_weather`
2. It needs a `city` parameter (string)
3. What the tool does (from the docstring)

## Tool Parameters

Syrin infers parameter types from type hints. The model uses these to generate correct arguments.

### Required vs Optional Parameters

Parameters without defaults are required:

```python
@tool
def send_email(to: str, subject: str, body: str, priority: str = "normal") -> str:
    """Send an email.
    
    Args:
        to: Email address of recipient
        subject: Email subject line
        body: Email body content
        priority: Priority level (low, normal, high)
    """
    return f"Email sent to {to}"

# Model MUST provide: to, subject, body
# Model MAY provide: priority (defaults to "normal")
```

### Type Annotations

Syrin supports these parameter types:

| Type | JSON Schema | Example |
|------|-------------|---------|
| `str` | string | `"hello"` |
| `int` | integer | `42` |
| `float` | number | `3.14` |
| `bool` | boolean | `true` |
| `list[str]` | array of strings | `["a", "b"]` |
| `dict` | object | `{"key": "value"}` |

### Custom Names

Override the tool name when needed:

```python
@tool(name="web_search")
def search_the_internet(query: str, max_results: int = 5) -> str:
    """Search the web for information."""
    return f"Found {max_results} results for: {query}"
```

## Observability: Watching Tool Calls

Every tool call emits hooks you can subscribe to for monitoring:

```python
from syrin import Hook

# Log all tool calls
def log_tool_call(ctx: dict) -> None:
    print(f"Tool called: {ctx['name']}")
    print(f"  Arguments: {ctx['arguments']}")
    print(f"  Duration: {ctx['duration_ms']}ms")

agent.events.on(Hook.TOOL_CALL_END, log_tool_call)

# Track tool errors
def log_tool_error(ctx: dict) -> None:
    print(f"Tool error: {ctx['name']}")
    print(f"  Error: {ctx['error']}")

agent.events.on(Hook.TOOL_ERROR, log_tool_error)
```

Hook payload includes:
- `name`: Tool name
- `arguments`: Dict of arguments passed
- `result`: What the tool returned
- `duration_ms`: Execution time
- `error`: Error message if failed

## Tool Execution Flow

Here's what happens when your agent uses a tool:

1. **Agent thinks** — "The user wants to know the weather in Paris"
2. **LLM decides** — Decides to call `get_weather(city="Paris")`
3. **Syrin executes** — Runs your Python function with the arguments
4. **Result returned** — Your function returns `"Weather in Paris: Rainy..."`
5. **LLM responds** — Incorporates the result into the final response

**Example:**
```
User: "What's the weather in Paris?"
Agent thinks: I need to call a tool
LLM calls: get_weather(city="Paris")
Syrin executes: get_weather("Paris") → "Weather in Paris: Rainy..."
LLM responds: "It's rainy in Paris today..."
```

## Tool Descriptions Matter

The docstring is your API documentation for the LLM. Write it like you're explaining to a smart but literal colleague:

```python
@tool
def calculate(a: float, b: float, operation: str = "add") -> str:
    """Perform basic arithmetic operations.

    Args:
        a: First number
        b: Second number
        operation: One of add, subtract, multiply, divide

    Use when:
        - User asks to calculate something
        - User wants math performed
        - User provides numbers to compute
    """
```

**Tip:** Include "Use when:" sections to help the model know when to call the tool.

## Multiple Tools

Agents can have multiple tools. The model decides which (if any) to use:

```python
@tool
def search_web(query: str) -> str:
    """Search the web for current information."""
    return "Search results..."

@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression."""
    return "42"

@tool
def get_date() -> str:
    """Get the current date and time."""
    from datetime import datetime
    return datetime.now().isoformat()

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    tools=[search_web, calculator, get_date],
)
```

## Tools with RunContext (Dependency Injection)

For tools that need access to agent state or configuration, use `RunContext`:

```python
from syrin import Agent, Model, tool
from syrin.types import RunContext

@tool
def get_user_count(ctx: RunContext) -> str:
    """Get the number of users in the system."""
    # Access injected context for dependencies
    db = ctx.deps.get("database")
    count = db.query("SELECT COUNT(*) FROM users")
    return f"Total users: {count}"

# Define dependencies
class MyDeps:
    def __init__(self):
        self.database = DatabaseConnection()

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    tools=[get_user_count],
)
result = agent.run("How many users do we have?")
```

When the tool's first parameter is named `ctx` with type `RunContext`, Syrin automatically injects it at runtime.

## What's Next?

- [TOON Format](/agent/tools-toon) — Learn about Syrin's token-efficient tool schemas
- [Built-in Tools](/agent/tools-builtin) — Tools that come with Syrin out of the box
- [Guardrails](/agent/guardrails) — Add safety checks around tool execution

## See Also

- [Tasks](/agent/tasks) — Structured agent methods (similar to tools but for agent-level operations)
- [Loop Strategies](/agent/running-agents) — How tools are executed in the reasoning loop
- [Hooks Reference](/debugging/hooks-reference) — All hooks for tool observability
