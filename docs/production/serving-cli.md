---
title: Serving: CLI
description: Interactive terminal REPL for testing agents
weight: 102
---

## Testing Agents in Your Terminal

Sometimes you just want to talk to your agent. No HTTP server, no browser—just your terminal and the agent.

The CLI REPL gives you an interactive prompt where you type messages, the agent responds, and you see cost and budget in real-time.

## The Problem

Testing agents during development is tedious:
- Starting an HTTP server just to test one query
- Writing test scripts that print output
- Manual curl commands with JSON payloads

The CLI REPL solves this with instant, interactive testing.

## Quick Start

```python
from syrin import Agent, Model, ServeProtocol

model = Model.OpenAI("gpt-4o", api_key="your-api-key")

agent = Agent(model=model, system_prompt="You are a helpful assistant.")
agent.serve(protocol=ServeProtocol.CLI)
```

**Output:**
```
[Syrin] assistant agent ready. Type your message. Ctrl+C to exit.

Budget: $0.50 / $0.50 remaining

> 
```

Type your message and press Enter:

```
> Hello
Hello! How can I help you today?
Cost: $0.0001 | Tokens: 12 | Budget remaining: $0.4999
>
```

## Features

### Real-Time Cost Display

After each response, you see:
- **Cost**: Cost in USD (trailing zeros stripped)
- **Tokens**: Total tokens used
- **Budget remaining**: If budget is configured

### Budget Visibility

If your agent has a budget configured, the remaining balance shows:

```
[Syrin] assistant agent ready. Type your message. Ctrl+C to exit.

Budget: $0.48 / $0.50 remaining

> 
```

### Conversation History

The CLI maintains conversation context within the session:

```
> Hello
Hello! How can I help you today?
Cost: $0.0001 | Tokens: 12 | Budget remaining: $0.4999

> My name is Alice
Nice to meet you, Alice! How can I assist you today?
Cost: $0.0002 | Tokens: 28 | Budget remaining: $0.4998

> What did I say my name was?
You said your name is Alice.
Cost: $0.0003 | Tokens: 45 | Budget remaining: $0.4995
```

### Interrupt Handling

Press `Ctrl+C` to interrupt a running request:

```
> Explain quantum entanglement in detail...
^C
Interrupted.
>
```

Press `Ctrl+D` or `Ctrl+C` to exit:

```
> Bye.
> 
^C
Bye.
```

## With Multiple Agents

When using `AgentRouter`, the CLI prompts you to select an agent:

```python
from syrin import Agent, Model, ServeProtocol
from syrin.serve import AgentRouter

router = AgentRouter(agents=[
    Agent(model=model, system_prompt="You research topics."),
    Agent(model=model, system_prompt="You write content."),
])
router.serve(protocol=ServeProtocol.CLI)
```

**Output:**
```
[Syrin] Multi-agent CLI. Choose an agent to chat with.

Select agent:
  1) researcher — Researches topics and summarizes findings
  2) writer — Writes content in a professional style

> 1
[Syrin] researcher agent ready. Type your message. Ctrl+C to exit.
```

## Exit Commands

| Command | Action |
|---------|--------|
| `Ctrl+C` | Interrupt current request or exit |
| `Ctrl+D` | Exit (EOF) |
| `exit` or `quit` | Not supported (just Ctrl+C/D) |

## Common Patterns

### Testing Tool Execution

```python
from syrin import Agent, Model, tool, ServeProtocol

model = Model.OpenAI("gpt-4o", api_key="your-api-key")


@tool(description="Get the current weather")
def get_weather(location: str) -> str:
    return f"Sunny, 72°F in {location}"


class WeatherAgent(Agent):
    model = model
    tools = [get_weather]
    system_prompt = "You are a weather assistant. Use the get_weather tool."


WeatherAgent().serve(protocol=ServeProtocol.CLI)
```

**Session:**
```
> What's the weather in San Francisco?
The weather in San Francisco is sunny and 72°F.
Cost: $0.0002 | Tokens: 35 | Budget remaining: $0.4998
```

### Testing Memory

```python
from syrin import Agent, Model, Memory, ServeProtocol

model = Model.OpenAI("gpt-4o", api_key="your-api-key")

agent = Agent(
    model=model,
    system_prompt="You are a helpful assistant. Remember important details.",
    memory=Memory(),
)
agent.serve(protocol=ServeProtocol.CLI)
```

**Session:**
```
> My favorite color is blue.
Got it! I'll remember that your favorite color is blue.
Cost: $0.0001 | Tokens: 15

> What did I say my favorite color was?
You said your favorite color is blue.
Cost: $0.0002 | Tokens: 28
```

### Testing Budget Limits

```python
from syrin import Agent, Model, Budget, ServeProtocol

model = Model.OpenAI("gpt-4o", api_key="your-api-key")

agent = Agent(
    model=model,
    budget=Budget(max_cost=0.01),  # Very small budget
)
agent.serve(protocol=ServeProtocol.CLI)
```

**When budget runs out:**
```
> Explain machine learning
Error: Budget exceeded (BudgetExceededError)
Budget remaining: $0.00
```

## Configuration

### ServeConfig for CLI

```python
from syrin import ServeConfig, ServeProtocol

agent.serve(
    config=ServeConfig(
        protocol=ServeProtocol.CLI,
        include_metadata=True,  # Show cost/tokens (CLI default)
    )
)
```

Most CLI-specific options are limited since the REPL is intentionally simple.

## Limitations

- **No streaming**: Responses print when complete
- **No HTTP endpoints**: Only the interactive prompt
- **Single session**: Conversation resets when you restart
- **No web UI**: No visual chat interface

For streaming or web integration, use HTTP mode with `enable_playground=True`.

## When to Use CLI vs HTTP

| Scenario | Use CLI | Use HTTP |
|----------|---------|----------|
| During development | ✅ | |
| Testing prompts | ✅ | |
| Testing tools | ✅ | |
| Frontend integration | | ✅ |
| Webhook receivers | | ✅ |
| Production serving | | ✅ |
| Streaming UX | | ✅ |
| Playground testing | | ✅ |

## See Also

- [Serving: HTTP API](/production/serving-http) — REST API reference
- [Serving: STDIO](/production/serving-stdio) — JSON lines for subprocesses
- [Serving: Advanced](/production/serving-advanced) — Mounting on existing apps
- [Playground](/production/playground) — Web UI for testing
