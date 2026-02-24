# Tools

Tools are functions the agent can call during execution. They extend the agent with search, computation, APIs, and other external actions.

## Defining Tools

Use the `@syrin.tool` decorator:

```python
from syrin.tool import tool

@tool
def search(query: str) -> str:
    """Search the web for information."""
    return f"Results for: {query}"

@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression. Use only +, -, *, /, **."""
    return str(eval(expression))
```

The docstring and parameter types become the tool schema sent to the model.

## Adding Tools to an Agent

Pass tools in the constructor or as a class attribute:

```python
agent = Agent(
    model=model,
    tools=[search, calculate],
)
```

## Tool Execution Flow

1. Model returns tool calls (names and arguments).
2. Agent looks up the tool by name.
3. Agent calls `tool.func(**arguments)`.
4. Result is appended to the conversation.
5. Loop continues until no more tool calls.

## ToolSpec

Each tool is represented as a `ToolSpec` with:

- `name` — Tool name (from function name).
- `parameters` — JSON schema for arguments.
- `func` — The underlying callable.

The `@tool` decorator builds `ToolSpec` from the function signature and docstring.

## Parameter Types

Supported types: `str`, `int`, `float`, `bool`, `list`, `dict`, and `Optional[T]`.

```python
@tool
def create_task(title: str, priority: int = 1, tags: list[str] | None = None) -> str:
    """Create a task with title, optional priority and tags."""
    return f"Created: {title} (priority={priority})"
```

## Error Handling

Tool failures raise `ToolExecutionError`:

```python
from syrin.exceptions import ToolExecutionError

try:
    response = agent.response("Search for X")
except ToolExecutionError as e:
    print(f"Tool failed: {e}")
```

## execute_tool (Custom Loops)

Custom loops can call tools via `execute_tool`:

```python
result = await agent.execute_tool("search", {"query": "hello"})
```

## See Also

- [Use Case 2: Research Agent with Tools](../research-agent-with-tools.md)
- [Loop Strategies](loop-strategies.md) — How tools integrate with loops
