---
title: Serving - HTTP API
description: Complete HTTP REST API reference for agent serving
weight: 101
---

## Your Agent as a REST API

Every Syrin agent exposes a complete REST API. This page documents every endpoint, request format, response format, and edge case you'll encounter.

## The Core Problem

When you build an agent, you need:
- A way to send messages (POST /chat)
- Real-time streaming for better UX (POST /stream)
- Health checks for orchestration (GET /health, GET /ready)
- Budget visibility for monitoring (GET /budget)
- Agent discovery for agent-to-agent communication (GET /.well-known/agent-card.json)

Building these from scratch takes hours. Syrin provides them out of the box.

## Quick Example

```python
from syrin import Agent, Model, Budget

model = Model.OpenAI("gpt-4o", api_key="your-api-key")

agent = Agent(
    model=model,
    system_prompt="You are a helpful assistant.",
    budget=Budget(max_cost=1.00),
)
agent.serve(port=8000)
```

**Server starts:**
```
Syrin endpoints:
  GET   /health
  GET   /ready
  GET   /budget
  GET   /describe
  POST  /chat
  POST  /stream
  GET   /.well-known/agent-card.json
```

## POST /chat

Run the agent and get a complete response.

### Request

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'
```

**Body parameters** (all optional except `message`):

`message` (string, required) is the user message. `input` and `content` are aliases for `message` — use whichever matches your data model. `conversation_id` (string, optional) is a session identifier for context tracking.

### Response

```json
{
  "content": "Hello! I'm doing well, thank you for asking...",
  "cost": 0.000150,
  "tokens": {
    "input": 15,
    "output": 42,
    "total": 57
  },
  "model": "gpt-4o",
  "stop_reason": "END_TURN",
  "duration": 0.234
}
```

**With `include_metadata=False`**, only `content` is returned.

**With `debug=True`** and `enable_playground=True`, `events` array is included with lifecycle hooks.

### Error Responses

**400 Bad Request** — Missing message:
```json
{"error": "Missing 'message', 'input', or 'content' in body"}
```

**413 Payload Too Large** — Message exceeds `max_message_length`:
```json
{"error": "Message exceeds 100000 characters. Reduce message size or increase max_message_length in ServeConfig."}
```

**500 Internal Server Error** — Agent crashed:
```json
{"error": "Budget exceeded"}
```

## POST /stream

Stream the response as Server-Sent Events (SSE) for real-time UX.

### Request

```bash
curl -X POST http://localhost:8000/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain quantum computing"}'
```

### Response Format

```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

**SSE events:**

```bash
data: {"type": "status", "message": "Thinking…"}

data: {"text": "Quantum", "accumulated": "Quantum"}

data: {"text": " computing", "accumulated": "Quantum computing"}

data: {"text": " is a...", "accumulated": "Quantum computing is a..."}

data: {"type": "budget", "limit": 1.0, "remaining": 0.99985, "spent": 0.00015, "percent_used": 0.015}

data: {"done": true, "type": "done", "cost": 0.00015, "tokens": {...}, "budget": {...}}
```

### Streaming with Debug Mode

When `debug=True` and `enable_playground=True`, events include lifecycle hooks:

```bash
data: {"type": "hook", "hook": "AGENT_RUN_START", "ctx": {"input": "Explain quantum computing", "iteration": 0}}

data: {"type": "hook", "hook": "LLM_CALL_START", "ctx": {...}}

data: {"text": "Quantum", "accumulated": "Quantum"}
...
```

### Streaming Behavior

**With tools on the agent:**
- The agent runs the full REACT loop internally
- You receive the final response (with tool executions completed)
- A "Thinking…" status event is emitted at the start

**Without tools:**
- Tokens stream as they arrive from the model
- Hook events stream in real-time (when debug mode is enabled)

## GET /health

Liveness probe. Returns 200 if the server is running.

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{"status": "ok"}
```

Use this for Kubernetes liveness probes or load balancer health checks.

## GET /ready

Readiness probe. Returns 200 if the agent is initialized and ready to handle requests.

```bash
curl http://localhost:8000/ready
```

**Response:**
```json
{"ready": true}
```

## GET /budget

Current budget state (if budget is configured).

```bash
curl http://localhost:8000/budget
```

**Response:**
```json
{
  "limit": 1.0,
  "remaining": 0.99985,
  "spent": 0.00015,
  "percent_used": 0.015
}
```

**If no budget configured:**
```json
{"error": "No budget configured"}
```

## GET /describe

Runtime introspection: agent name, tools, budget state.

```bash
curl http://localhost:8000/describe
```

**Response:**
```json
{
  "name": "assistant",
  "description": "Helpful assistant for questions and tasks",
  "tools": [
    {
      "name": "remember_fact",
      "description": "Remember a fact for later",
      "parameters": {...}
    }
  ],
  "budget": {
    "limit": 1.0,
    "remaining": 0.99985,
    "spent": 0.00015,
    "percent_used": 0.015
  },
  "internal_agents": null,
  "setup_type": "single"
}
```

**For DynamicPipeline**, `setup_type` is `"dynamic_pipeline"` and `internal_agents` lists the available agents.

## GET /.well-known/agent-card.json

A2A (Agent-to-Agent) discovery endpoint following the A2A specification.

```bash
curl http://localhost:8000/.well-known/agent-card.json
```

**Response:**
```json
{
  "name": "assistant",
  "description": "Helpful assistant for questions and tasks",
  "url": "http://localhost:8000",
  "version": "0.4.0",
  "provider": {
    "organization": "Syrin",
    "url": "https://github.com/Syrin-Labs/syrin-python"
  },
  "capabilities": {
    "streaming": true,
    "pushNotifications": false
  },
  "authentication": {
    "schemes": ["bearer"]
  },
  "skills": [
    {
      "id": "remember_fact",
      "name": "Remember Fact",
      "description": "Remember a fact for later",
      "inputModes": ["application/json"],
      "outputModes": ["application/json"]
    }
  ],
  "defaultInputModes": ["application/json"],
  "defaultOutputModes": ["application/json"]
}
```

### Customizing the Agent Card

Override any field via the `agent_card` class attribute:

```python
from syrin.serve.discovery import AgentCard, AgentCardProvider

class Assistant(Agent):
    model = model
    agent_card = AgentCard(
        name="my-assistant",
        description="Customer support assistant",
        provider=AgentCardProvider(
            organization="My Company",
            url="https://mycompany.com",
        ),
        authentication=AgentCardAuth(
            schemes=["bearer"],
            oauth_url="https://mycompany.com/oauth",
        ),
    )
```

## Route Prefixes

Add a prefix to all routes:

```python
agent.serve(port=8000, route_prefix="/api/v1/agent")
```

**Endpoints become:**
- `POST /api/v1/agent/chat`
- `POST /api/v1/agent/stream`
- `GET /api/v1/agent/health`
- etc.

## Multiple Agents

With `AgentRouter`, each agent gets its own namespace:

```python
from syrin import Agent, Model
from syrin.serve import AgentRouter

router = AgentRouter(agents=[
    Agent(model=model, system_prompt="You research."),
    Agent(model=model, system_prompt="You write."),
])
router.serve(port=8000)
```

**Endpoints:**
- `POST /agent/researcher/chat`
- `POST /agent/writer/chat`
- `GET /agent/researcher/health`
- etc.

## Configuration Options

### ServeConfig Parameters

Ten parameters control the server. `protocol` (default `HTTP`) selects the transport. `host` (default `"0.0.0.0"`) sets the bind address. `port` (default `8000`) sets the HTTP port. `route_prefix` (default `""`) adds a URL prefix to all routes. `stream` (default `True`) enables the `/stream` SSE endpoint. `include_metadata` (default `True`) includes cost and token counts in responses. `debug` (default `False`) enables verbose logging. `enable_playground` (default `False`) serves the web playground UI. `enable_discovery` (default `None`) controls A2A discovery — auto-enabled when the agent has a name, or set to `False` to disable explicitly. `max_message_length` (default `100000`) caps the maximum number of characters per message.

## What's Next?

- [Serving: CLI](/agent-kit/production/serving-cli) — Interactive terminal testing
- [Serving: Advanced](/agent-kit/production/serving-advanced) — Mounting, middleware, multiple servers
- [Playground](/agent-kit/production/playground) — Web testing interface
- [Remote Config](/agent-kit/production/remote-config) — Runtime configuration updates
