---
title: Streaming
description: Real-time token-by-token responses for ChatGPT-style UIs
weight: 82
---

## The Wait Problem

You've built a great agent. Users type a question. They wait. And wait. And wait. Then — suddenly — the entire response appears.

It's jarring. Modern AI apps don't work like that. Users want to see words appear as they're generated, like they're watching someone type. That's streaming.

## Basic Streaming

Use `agent.stream()` instead of `agent.run()`. It returns an iterator of `StreamChunk` objects:

```python
from syrin import Agent, Model

agent = Agent(
    model=Model.mock(),
    system_prompt="You are a helpful assistant.",
)

for chunk in agent.stream("Write a haiku about coding"):
    print(chunk.text, end="", flush=True)
print()
```

Output:

```
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor...
```

With a real model, words would arrive one by one. With the mock model, they all come in one chunk (the mock doesn't stream token by token). The API is the same either way.

## The StreamChunk Object

Each chunk you receive has these fields:

**`chunk.text`** — the new text in this chunk (the delta — just what arrived since the last chunk).

**`chunk.accumulated_text`** — all text received so far in this stream.

**`chunk.cost_so_far`** — running USD cost.

**`chunk.tokens_so_far`** — running `TokenUsage` object with `.input_tokens`, `.output_tokens`, `.total_tokens`.

**`chunk.is_final`** — `True` on the last chunk.

**`chunk.response`** — the complete `Response` object, available only on the final chunk.

**`chunk.index`** — which chunk this is (0-based).

```python
from syrin import Agent, Model

agent = Agent(model=Model.mock(), system_prompt="You are helpful.")

for chunk in agent.stream("Hello!"):
    print(f"Index: {chunk.index}")
    print(f"Text: {chunk.text!r}")
    print(f"Accumulated: {chunk.accumulated_text[:30]!r}")
    print(f"Cost so far: ${chunk.cost_so_far:.6f}")
    print(f"Is final: {chunk.is_final}")
```

Output (mock model returns everything in one chunk):

```
Index: 0
Text: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod...'
Accumulated: 'Lorem ipsum dolor sit amet, co'
Cost so far: $0.000000
Is final: False
```

With a real model like `Model.OpenAI("gpt-4o-mini")`, you'd see many chunks arrive one after another, each with a few tokens of text, and `is_final=True` on the last one.

## Async Streaming

For web applications, use `agent.astream()` — the async version:

```python
import asyncio
from syrin import Agent, Model

agent = Agent(model=Model.mock(), system_prompt="You are helpful.")

async def main():
    async for chunk in agent.astream("Write a poem"):
        print(chunk.text, end="", flush=True)
    print()

asyncio.run(main())
```

### Streaming in FastAPI

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import json
from syrin import Agent, Model

app = FastAPI()
agent = Agent(model=Model.OpenAI("gpt-4o-mini", api_key="your-key"), system_prompt="You are helpful.")

@app.post("/chat/stream")
async def chat_stream(message: str):
    async def event_generator():
        async for chunk in agent.astream(message):
            yield f"data: {json.dumps({'text': chunk.text})}\n\n"
        yield 'data: {"done": true}\n\n'

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

## Getting the Final Response

After streaming, the last chunk's `.response` field contains the complete `Response` object with all the usual fields (cost, tokens, stop_reason, etc.):

```python
from syrin import Agent, Model

agent = Agent(model=Model.mock(), system_prompt="You are helpful.")
full_text = ""
final_response = None

for chunk in agent.stream("Tell me something"):
    full_text += chunk.text
    if chunk.is_final and chunk.response:
        final_response = chunk.response

if final_response:
    print(f"Total cost: ${final_response.cost:.6f}")
    print(f"Stop reason: {final_response.stop_reason}")
else:
    # Mock model doesn't set is_final=True, so collect from accumulated_text
    chunks = list(agent.stream("Tell me something"))
    full_text = chunks[-1].accumulated_text
    print(f"Text: {full_text[:40]}")
```

## Important: No Tools During Streaming

`agent.stream()` and `agent.astream()` make one LLM call and yield tokens. That's it. Tool execution, memory operations, and guardrails do not run during streaming.

If you need tools to execute, use `agent.run()` or `agent.arun()`. For UIs that need both functionality and a streaming feel, run the agent normally and progressively display the `response.content` as it arrives — or design your tools to run before the final response step.

## Streaming Hooks

Subscribe to `Hook.LLM_STREAM_CHUNK` to observe chunks from within the hook system:

```python
from syrin import Agent, Model
from syrin.enums import Hook

agent = Agent(model=Model.mock(), system_prompt="You are helpful.")

agent.events.on(
    Hook.LLM_STREAM_CHUNK,
    lambda ctx: print(f"Chunk: {ctx.get('text', '')!r}")
)

list(agent.stream("Hello!"))
```

## Tracking Cost During a Stream

Use `chunk.cost_so_far` to update a UI budget indicator in real time:

```python
from syrin import Agent, Model

agent = Agent(model=Model.OpenAI("gpt-4o-mini", api_key="your-key"), system_prompt="You are helpful.")

for chunk in agent.stream("Explain machine learning"):
    print(chunk.text, end="", flush=True)
    if chunk.cost_so_far > 0.05:
        print("\n[Budget warning: approaching $0.05]")
        break

print()
```

## Chat Loop with Streaming

A simple terminal chat interface using streaming:

```python
from syrin import Agent, Model

class ChatAgent(Agent):
    model = Model.mock()
    system_prompt = "You are a helpful assistant. Be concise."

agent = ChatAgent()

print("Chat with your agent (type 'quit' to exit)")

while True:
    user_input = input("\nYou: ")
    if user_input.lower() == "quit":
        break

    print("Agent: ", end="")
    total_cost = 0
    for chunk in agent.stream(user_input):
        print(chunk.text, end="", flush=True)
        total_cost = chunk.cost_so_far
    print(f"\n[${total_cost:.6f}]")
```

Output:

```
Chat with your agent (type 'quit' to exit)

You: Hello!
Agent: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed...
[$0.000000]
```

## What's Next

- [Running Agents](/agent-kit/agent/running-agents) — `run()`, `arun()`, and the Response object
- [Serving](/agent-kit/production/serving) — Serve your agent as an HTTP API with built-in streaming
- [Response Object](/agent-kit/agent/response-object) — What you get after the stream completes
