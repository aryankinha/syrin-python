---
title: Serving Overview
description: Deploy agents via HTTP, CLI, or STDIO protocols
weight: 100
---

## The Gap Between Code and Production

You have a working agent. It responds to queries, uses tools, respects budgets. But how do you ship it?

- A colleague needs to test it without running Python
- Your frontend team wants to integrate via REST API
- DevOps needs a way to monitor health and budget
- You want a web UI for interactive testing

Building a serving layer from scratch means writing FastAPI routes, handling streaming, implementing health checks, managing CORS, and dozens of other details that have nothing to do with your agent's core logic.

Syrin solves this with one line: `agent.serve()`. This page explains your deployment options.

## Serving Protocols

Syrin supports three deployment modes:

| Protocol | Use Case | Blocking? |
|----------|----------|-----------|
| **HTTP** | REST API, webhooks, frontend integration | No (runs server) |
| **CLI** | Interactive testing in terminal | Yes (REPL) |
| **STDIO** | Subprocess spawning, MCP hosts, background tasks | Yes (reads stdin) |

### HTTP Server

The most common deployment. Exposes REST endpoints and optionally a web playground:

```python
from syrin import Agent, Model

model = Model.OpenAI("gpt-4o", api_key="your-api-key")


class Assistant(Agent):
    model = model
    system_prompt = "You are a helpful assistant."


agent = Assistant()

# Serve on port 8000 with web playground
agent.serve(port=8000, enable_playground=True, debug=True)
```

**What just happened**: An HTTP server started on port 8000. Visit `http://localhost:8000/playground` for the web UI, or call `POST /chat` for programmatic access.

### Interactive CLI

For testing in your terminal:

```python
agent.serve(protocol=ServeProtocol.CLI)
```

**Output:**
```
[Syrin] assistant agent ready. Type your message. Ctrl+C to exit.

Budget: $0.48 / $0.50 remaining

> Hello
Hello! How can I help you today?
Cost: $0.0001 | Tokens: 12 | Budget remaining: $0.4999
>
```

### STDIO for Subprocesses

For spawning from other processes or integrating with MCP:

```bash
echo '{"input": "Hello", "conversation_id": "session-1"}' | python -m my_agent
```

**Output:**
```json
{"content": "Hello! How can I help you today?", "cost": 0.0001, "tokens": 12, "conversation_id": "session-1"}
```

## Core Endpoints (HTTP)

Every agent exposes these endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Run agent, get full response |
| `/stream` | POST | Stream response as SSE |
| `/health` | GET | Liveness probe |
| `/ready` | GET | Readiness probe |
| `/budget` | GET | Current budget state |
| `/describe` | GET | Agent schema and tools |
| `/config` | GET | Config schema (remote config) |
| `/config` | PATCH | Apply config overrides |
| `/.well-known/agent-card.json` | GET | A2A discovery |

## Common Patterns

### Basic HTTP with Playground

```python
from syrin import Agent, Model, ServeConfig

model = Model.OpenAI("gpt-4o", api_key="your-api-key")

agent = Agent(model=model, system_prompt="You are a helpful assistant.")
agent.serve(
    port=8000,
    enable_playground=True,
    debug=True,  # Enable event collection for observability
)
```

**Features enabled:**
- Web playground at `/playground`
- Event stream at `/stream` with budget updates
- Full lifecycle hooks in debug output

### Production HTTP

```python
from syrin import Agent, Model, ServeConfig

agent = Agent(model=model, system_prompt="You are a helpful assistant.")
agent.serve(
    config=ServeConfig(
        host="0.0.0.0",
        port=8080,
        enable_playground=False,  # No UI in production
        debug=False,
        include_metadata=True,
    )
)
```

### Mount on Existing FastAPI App

```python
from fastapi import FastAPI
from syrin import Agent, Model

app = FastAPI(title="My API")
agent = Agent(model=model, system_prompt="You are a helpful assistant.")

app.include_router(agent.as_router(), prefix="/agent")
```

**Routes available:**
- `POST /agent/chat`
- `POST /agent/stream`
- `GET /agent/health`
- `GET /core/budget`

### Multiple Agents

```python
from syrin import Agent, Model
from syrin.serve import AgentRouter

router = AgentRouter(agents=[
    Agent(model=model, system_prompt="You research."),
    Agent(model=model, system_prompt="You write."),
])
router.serve(port=8000)
```

**Routes available:**
- `POST /agent/researcher/chat`
- `POST /agent/writer/chat`
- `GET /agent/researcher/health`
- etc.

## Configuration Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `protocol` | `ServeProtocol` | HTTP | Transport protocol |
| `host` | `str` | `"0.0.0.0"` | Bind address |
| `port` | `int` | `8000` | HTTP port |
| `route_prefix` | `str` | `""` | URL prefix (e.g., `"/agent"`) |
| `stream` | `bool` | `True` | Enable `/stream` endpoint |
| `include_metadata` | `bool` | `True` | Include cost/tokens in responses |
| `debug` | `bool` | `False` | Enable debug mode |
| `enable_playground` | `bool` | `False` | Serve web playground |
| `enable_discovery` | `bool \| None` | `None` | A2A discovery (auto if named) |
| `max_message_length` | `int` | `100000` | Max characters per message |

## Key Behaviors

### Workers and In-Memory State

HTTP mode runs with `workers=1`. This is intentional—in-memory state like conversation history and budget tracking is per-process. Multiple workers would each have separate state, breaking these features.

**For multi-worker deployments**, use shared backends:
- **Memory**: Use `Memory(backend=MemoryBackend.REDIS)` or `MemoryBackend.POSTGRES`
- **Budget**: Use rate-limited budgets with distributed tracking
- **Checkpoints**: Use file-based or database checkpoint storage

### Discovery Auto-Detection

A2A agent card discovery (`/.well-known/agent-card.json`) is auto-enabled when the agent has a name. Disable with `enable_discovery=False`:

```python
agent.serve(config=ServeConfig(enable_discovery=False))
```

### Authentication Warning

The HTTP server logs a warning when serving without authentication. For production, add auth middleware or mount behind an authenticated gateway.

## See Also

- [Serving: HTTP](/agent-kit/production/serving-http) — Complete HTTP API reference
- [Serving: CLI](/agent-kit/production/serving-cli) — Interactive terminal usage
- [Serving: Advanced](/agent-kit/production/serving-advanced) — Mounting, middleware, load balancing
- [Playground](/agent-kit/production/playground) — Web testing interface
- [Remote Config](/agent-kit/production/remote-config) — Runtime configuration updates
