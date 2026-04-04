---
title: Serving
description: Deploy your agent as an HTTP API, CLI, or with a built-in chat playground
weight: 100
---

## From Python Class to Running Service

You built your agent. Now you want people to use it. Syrin can serve any agent as an HTTP API in one line — no FastAPI boilerplate, no routing code, no schema definitions.

Install the serving dependencies first:

```bash
pip install "syrin[serve]"
```

## HTTP Serving

The simplest case — one line to get an HTTP API with a chat interface:

```python
from syrin import Agent, Budget, Model
from syrin.enums import ExceedPolicy

class Assistant(Agent):
    model = Model.mock()
    system_prompt = "You are a helpful assistant. Be concise."
    budget = Budget(max_cost=5.00, exceed_policy=ExceedPolicy.WARN)

agent = Assistant()
agent.serve(port=8000, enable_playground=True)
```

Visit `http://localhost:8000/playground` and you get a full chat interface — type a message, see the response, and watch the cost tick up in real time.

The server exposes these endpoints automatically:
- `POST /chat` — send a message, get a response
- `GET /stream` — server-sent events for streaming responses
- `GET /health` — liveness check
- `GET /ready` — readiness check (verifies model connection)
- `GET /budget` — current budget state (limit, spent, remaining)
- `GET /describe` — agent metadata (name, description, tools, capabilities)
- `GET /playground` — the chat UI (when `enable_playground=True`)

## Calling the API

Once the server is running, call it from any HTTP client:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello! What can you do?"}'
```

Response:

```json
{
  "content": "I can answer questions, help with tasks, and have conversations.",
  "cost": 0.000040,
  "model": "almock/default",
  "stop_reason": "end_turn",
  "tokens": {
    "input_tokens": 12,
    "output_tokens": 18,
    "total_tokens": 30
  }
}
```

Or from Python:

```python
import requests

response = requests.post(
    "http://localhost:8000/chat",
    json={"message": "What is the capital of France?"}
)
print(response.json()["content"])
```

## ServeConfig

For more control, use `ServeConfig` instead of keyword arguments:

```python
from syrin import Agent, Model, ServeConfig

class Assistant(Agent):
    model = Model.mock()
    system_prompt = "You are helpful."

agent = Assistant()
agent.serve(ServeConfig(
    port=8000,
    host="0.0.0.0",           # Bind to all interfaces
    enable_playground=True,    # Enable the chat UI
    enable_discovery=True,     # List agent capabilities at /describe
    stream=True,               # Enable streaming by default
    debug=False,               # Disable verbose logging in production
    max_message_length=100000, # Max input message length
))
```

## Mounting on an Existing FastAPI App

If you already have a FastAPI application, mount your agent as a router — no new process, no port conflict:

```python
from fastapi import FastAPI
from syrin import Agent, Model

class Assistant(Agent):
    model = Model.mock()
    system_prompt = "You are helpful."

app = FastAPI()
agent = Assistant()

# Mount at /agent — all agent routes appear under /agent/*
router = agent.as_router()
app.include_router(router, prefix="/agent")

# Your existing routes continue to work
@app.get("/health")
def health():
    return {"status": "ok"}
```

With this approach, `POST /agent/chat`, `GET /agent/budget`, and `GET /agent/describe` are all available alongside your existing routes.

## CLI Serving

For interactive terminal use, serve via CLI:

```python
from syrin import Agent, Model, ServeConfig
from syrin.enums import ServeProtocol

agent = Agent(model=Model.mock(), system_prompt="You are helpful.")
agent.serve(ServeConfig(protocol=ServeProtocol.CLI))
```

Or run it from the command line:

```bash
syrin serve examples.my_agent:agent
```

This opens an interactive REPL where you type messages and see responses. The CLI mode is useful for testing, scripting, and local use without a browser.

## STDIO Serving

For integrations with other tools (editors, automation pipelines), STDIO serving reads from stdin and writes to stdout in JSON format:

```python
from syrin import Agent, Model, ServeConfig
from syrin.enums import ServeProtocol

agent = Agent(model=Model.mock(), system_prompt="You are helpful.")
agent.serve(ServeConfig(protocol=ServeProtocol.STDIO))
```

Send a JSON message to stdin:

```
{"message": "Hello!"}
```

Get a JSON response on stdout:

```json
{"content": "Hello! How can I help you?", "cost": 0.000040}
```

## Serving a Swarm

Swarms can also be served as HTTP endpoints:

```python
import asyncio
from syrin import Agent, Model
from syrin.swarm import Swarm

class ResearchAgent(Agent):
    model = Model.mock()
    system_prompt = "You research topics."

class WriterAgent(Agent):
    model = Model.mock()
    system_prompt = "You write summaries."

swarm = Swarm(
    agents=[ResearchAgent(), WriterAgent()],
    goal="AI research assistant",
)
swarm.serve(port=8000)
```

The swarm server exposes `POST /chat` (sends the message as the swarm goal) and `GET /graph` (returns the execution graph for WORKFLOW topology).

## Environment Variables for Production

In production, never hardcode API keys in your serve command. Use environment variables:

```python
import os
from syrin import Agent, Model

class ProductionAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
    system_prompt = "You are a helpful production assistant."
```

Set the key before starting the server:

```bash
export OPENAI_API_KEY="sk-..."
python my_agent_server.py
```

## GitHub Examples

Full working serving examples are in the repository:

- [`examples/16_serving/http_serve.py`](https://github.com/syrin-labs/syrin-python/blob/main/examples/16_serving/http_serve.py) — Basic HTTP serving with playground
- [`examples/16_serving/cli_serve.py`](https://github.com/syrin-labs/syrin-python/blob/main/examples/16_serving/cli_serve.py) — CLI interactive mode
- [`examples/16_serving/mount_on_existing_app.py`](https://github.com/syrin-labs/syrin-python/blob/main/examples/16_serving/mount_on_existing_app.py) — FastAPI router mounting
- [`examples/16_serving/chatbot.py`](https://github.com/syrin-labs/syrin-python/blob/main/examples/16_serving/chatbot.py) — Chat agent with memory

## What's Next

- [Serving HTTP](/agent-kit/production/serving-http) — Full HTTP serving reference and endpoint schema
- [Serving CLI](/agent-kit/production/serving-cli) — CLI mode and the syrin command
- [Checkpointing](/agent-kit/production/checkpointing) — Survive server restarts
- [Remote Config](/agent-kit/production/remote-config) — Change agent configuration without redeploying
- [Deployment](/agent-kit/production/deployment) — Docker, environment setup, production checklist
