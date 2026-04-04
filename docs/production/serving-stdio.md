---
title: Serving: STDIO
description: JSON lines protocol for subprocess and background task integration
weight: 103
---

## Agents as Subprocesses

Sometimes your agent needs to run as a subprocess. Maybe you're building an MCP server that hosts your agent, spawning agents from a parent process, running agents in a background worker, or integrating with shell scripts or CI pipelines.

STDIO mode turns your agent into a JSON line processor: read JSON from stdin, write JSON to stdout.

## How It Works

```
stdin:  {"input": "Hello"}
        {"input": "How are you?"}
        EOF

stdout: {"content": "Hello! How can I help you?", "cost": 0.0001, "tokens": 15}
        {"content": "I'm doing well, thank you!", "cost": 0.0002, "tokens": 28}
```

The agent reads one JSON object per line from stdin, processes the message, writes the response as JSON to stdout, and repeats until EOF.

## Quick Start

```python
from syrin import Agent, Model, ServeProtocol

model = Model.OpenAI("gpt-4o", api_key="your-api-key")

agent = Agent(
    model=model,
    system_prompt="You are a helpful assistant.",
)

agent.serve(protocol=ServeProtocol.STDIO)
```

**Run:**
```bash
echo '{"input": "Hello"}' | python my_agent.py
```

**Output:**
```json
{"content": "Hello! How can I help you?", "cost": 0.00015, "tokens": 12}
```

## Protocol Format

### Input Format (stdin)

Each line must be valid JSON with at least one message field. `input` is the primary field for the message to send. `message` and `content` are aliases — use whichever matches your data model. `conversation_id` is optional and identifies a session for context tracking.

### Output Format (stdout)

```json
{"content": "Agent response", "cost": 0.00015, "tokens": 12, "conversation_id": "session-1"}
```

Every response includes `content` (the agent's text), `cost` (USD), and `tokens` (total tokens used). `conversation_id` is echoed back if it was provided in the input. On errors, an `error` field appears instead of `content`.

## Examples

### Single Request

```bash
echo '{"input": "What is 2 + 2?"}' | python my_agent.py
```

**Output:**
```json
{"content": "2 + 2 equals 4.", "cost": 0.0001, "tokens": 8}
```

### Multiple Requests

```bash
echo '{"input": "Hello"}
{"input": "What is Python?"}
{"input": "Goodbye"}' | python my_agent.py
```

**Output:**
```json
{"content": "Hello! How can I help you?", "cost": 0.0001, "tokens": 12}
{"content": "Python is a high-level programming language...", "cost": 0.0003, "tokens": 45}
{"content": "Goodbye! Have a great day!", "cost": 0.0001, "tokens": 10}
```

### With Conversation ID

```bash
echo '{"input": "My name is Alice", "conversation_id": "user-123"}' | python my_agent.py
```

**Output:**
```json
{"content": "Nice to meet you, Alice!", "cost": 0.0001, "tokens": 15, "conversation_id": "user-123"}
```

The conversation_id is echoed back, allowing the parent process to correlate requests with responses.

### Error Handling

**Invalid JSON:**
```bash
echo 'not valid json' | python my_agent.py
```

**Output:**
```json
{"error": "Invalid JSON: Expecting value: line 1 column 1 (char 0)"}
```

**Missing message:**
```bash
echo '{"conversation_id": "test"}' | python my_agent.py
```

**Output:**
```json
{"error": "Missing 'input', 'message', or 'content'"}
```

**Agent error:**
```bash
echo '{"input": "Make it crash"}' | python my_agent.py
```

**Output:**
```json
{"error": "Budget exceeded", "conversation_id": null}
```

## Common Use Cases

### MCP Server Host

MCP servers can spawn agents as subprocesses:

```python
#!/usr/bin/env python3
"""MCP server that hosts a Syrin agent."""

import json
from syrin import Agent, Model, Budget, ServeProtocol

model = Model.OpenAI("gpt-4o", api_key="your-api-key")

agent = Agent(
    model=model,
    system_prompt="You are a helpful coding assistant.",
    budget=Budget(max_cost=0.50),
)

if __name__ == "__main__":
    agent.serve(protocol=ServeProtocol.STDIO)
```

The MCP host communicates via JSON lines:

```python
# In your MCP host
import subprocess
import json

proc = subprocess.Popen(
    ["python", "mcp_agent.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)

# Send request
request = {"input": "Write a hello world function", "conversation_id": "req-1"}
proc.stdin.write(json.dumps(request) + "\n")
proc.stdin.flush()

# Read response
response = json.loads(proc.stdout.readline())
print(response["content"])
```

### Background Worker

Process messages from a queue:

```python
#!/usr/bin/env python3
"""Background worker that processes messages from stdin."""

import json
import queue
import threading
from syrin import Agent, Model, Budget, ServeProtocol

messages = queue.Queue()


def worker():
    while True:
        msg = messages.get()
        if msg is None:
            break
        # Process message
        agent.run(msg)


agent = Agent(model=model, budget=Budget(max_cost=10.00))
threading.Thread(target=worker, daemon=True).start()

# Read from stdin
import sys
for line in sys.stdin:
    messages.put(line.strip())
```

### Shell Script Integration

```bash
#!/bin/bash
# ci_script.sh

AGENT="./my_agent.py"

# Run agent and capture response
RESPONSE=$(echo '{"input": "Summarize: The project is complete"}' | $AGENT)

# Extract content using jq
SUMMARY=$(echo "$RESPONSE" | jq -r '.content')

echo "Agent summary: $SUMMARY"
```

### CI/CD Pipeline

```yaml
# .github/workflows/agent.yml
- name: Run Agent
  run: |
    echo '{"input": "Review this code: ${{ github.event.pull_request.diff }}"}' \
      | python agent.py \
      | jq -r '.content' \
      > review.md
```

## Testing Without Subprocess

For unit tests, pass custom stdin/stdout:

```python
import io
import json
from syrin import Agent, Model

agent = Agent(model=Model.mock())

# Simulate input
stdin = io.StringIO('{"input": "Hello"}\n{"input": "How are you?"}')
stdout = io.StringIO()

agent.serve(protocol=ServeProtocol.STDIO, stdin=stdin, stdout=stdout)

# Check output
output = stdout.getvalue()
responses = [json.loads(line) for line in output.strip().split("\n")]

assert responses[0]["content"] == "Hello! How can I help you?"
assert responses[1]["content"] == "I'm doing well!"
```

## Configuration

### ServeConfig for STDIO

```python
from syrin import ServeConfig, ServeProtocol

agent.serve(
    config=ServeConfig(
        protocol=ServeProtocol.STDIO,
        include_metadata=True,  # Always True for STDIO
    )
)
```

### Agent Configuration

All agent options work normally:

```python
from syrin import Agent, Model, Budget, Memory

agent = Agent(
    model=model,
    system_prompt="You are a helpful assistant.",
    budget=Budget(max_cost=10.00),
    memory=Memory(),  # Conversation context persists across requests
)
```

**Note**: Memory persists across requests within the same STDIO session. Each new run starts fresh.

## Protocol Reference

### Input Validation

Valid JSON with a message field processes normally. Invalid JSON returns `{"error": "Invalid JSON: ..."}`. JSON without any message field (`input`, `message`, or `content`) returns `{"error": "Missing 'input', 'message', or 'content'"}`. Empty lines and whitespace-only lines are silently skipped.

### Output Fields

`content` (string) is the agent's response text. `cost` (float) is the USD cost of the request. `tokens` (int) is the total token count. `conversation_id` (string or null) echoes the value from input if one was provided. `error` (string) appears only on failure, in place of `content`.

### Conversation Context

The `conversation_id` field enables session tracking:

```python
# First message
{"input": "My name is Alice", "conversation_id": "alice-001"}
# Response includes conversation_id

# Second message (same conversation)
{"input": "What is my name?", "conversation_id": "alice-001"}
# Agent should remember Alice (if memory is configured)
```

## Limitations

- **No streaming**: Responses are complete before writing to stdout
- **Blocking**: Processes one request at a time
- **No HTTP endpoints**: Only stdin/stdout communication
- **EOF to exit**: Agent runs until stdin closes

For streaming or concurrent requests, use HTTP mode instead.

## When to Use STDIO vs HTTP

Use STDIO when spawning the agent as a subprocess, running it inside an MCP server, processing messages in a background worker, or calling it from shell scripts and CI pipelines. These scenarios all benefit from the simplicity of one JSON line in, one JSON line out.

Use HTTP when you need frontend integration, webhooks, streaming responses, concurrent request handling, or playground testing. HTTP handles multiple simultaneous requests and supports server-sent events for streaming.

## See Also

- [Serving: HTTP API](/agent-kit/production/serving-http) — REST API for HTTP-based integration
- [Serving: CLI](/agent-kit/production/serving-cli) — Interactive terminal testing
- [Serving: Advanced](/agent-kit/production/serving-advanced) — Production deployment patterns
- [MCP Integration](/agent-kit/integrations/mcp) — Model Context Protocol
