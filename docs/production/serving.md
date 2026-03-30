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

## Start Here

If you are deciding how to expose an agent, use this progression:

1. Start with `examples/16_serving/http_serve.py` if you want a plain HTTP API.
2. Move to `examples/16_serving/playground_single.py` if you want a browser playground.
3. Use `examples/16_serving/cli_serve.py` for terminal-only testing.
4. Use `examples/16_serving/stdio_serve.py` when another process will own orchestration.
5. Use `examples/16_serving/mount_on_existing_app.py` when you already have a FastAPI app.
6. Use `examples/16_serving/multi_agent_router.py` when you need multiple agents behind one server.

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

This flow is demonstrated directly in `examples/16_serving/http_serve.py` and `examples/16_serving/playground_single.py`.

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

Use `examples/16_serving/cli_serve.py` when you want this exact local testing loop.

### STDIO for Subprocesses

For spawning from other processes or integrating with MCP:

```bash
echo '{"input": "Hello", "conversation_id": "session-1"}' | python -m my_agent
```

**Output:**
```json
{"content": "Hello! How can I help you today?", "cost": 0.0001, "tokens": 12, "conversation_id": "session-1"}
```

Use `examples/16_serving/stdio_serve.py` when your agent is being driven by another runtime and stdin/stdout is the contract boundary.

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

### One Example Per Serving Style

| Goal | Example |
|------|---------|
| Plain HTTP | `examples/16_serving/http_serve.py` |
| Browser playground | `examples/16_serving/playground_single.py` |
| CLI REPL | `examples/16_serving/cli_serve.py` |
| STDIO subprocess | `examples/16_serving/stdio_serve.py` |
| Mount into existing app | `examples/16_serving/mount_on_existing_app.py` |
| Multi-agent server | `examples/16_serving/multi_agent_router.py` |
| Discovery override | `examples/16_serving/discovery_override.py` |

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

If you want lower-level composition instead of `agent.as_router()`, use `create_http_app()` or `build_router()` from `syrin.serve` and mount them into your own application stack.

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

This is the right pattern when you want one deployment surface with several specialized agents behind it.

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

If you need to customize the discovery payload itself, see `examples/16_serving/discovery_override.py`.

### Authentication Warning

The HTTP server logs a warning when serving without authentication. For production, add auth middleware or mount behind an authenticated gateway.

## Public Serving Helpers

The serving package also exports:

- `AGENT_CARD_PATH` for the well-known discovery path.
- `Servable` for typing objects that can be served.
- `create_http_app()` and `build_router()` for composing serving into your own application stack.
- `build_agent_card_json()` when you need to generate agent-card payloads directly.

## Practical Advice

- Use HTTP plus playground during development.
- Use CLI when the fastest feedback loop is a terminal.
- Use STDIO when another supervisor process owns lifecycle and transport.
- Use router-based serving when you need multiple named agents in one service.
- Use mount/composition helpers when serving is only one part of a larger FastAPI application.

## See Also

- [Serving: HTTP](/agent-kit/production/serving-http) — Complete HTTP API reference
- [Serving: CLI](/agent-kit/production/serving-cli) — Interactive terminal usage
- [Serving: Advanced](/agent-kit/production/serving-advanced) — Mounting, middleware, load balancing
- [Playground](/agent-kit/production/playground) — Web testing interface
- [Remote Config](/agent-kit/production/remote-config) — Runtime configuration updates
