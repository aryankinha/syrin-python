---
title: Streaming
description: Real-time token-by-token responses for ChatGPT-style UIs
weight: 82
---

## Real-Time Responses

You've built a great agent. It works. But when you add it to your app, something feels off.

Users type a question. They wait. And wait. And wait. Then—suddenly—the entire response appears.

It's jarring. It's not what users expect from modern AI apps. They want to see words appear as they're generated. They want that ChatGPT feel.

**This is the streaming problem.** You need to stream tokens as they arrive, not wait for the complete response.

## The Solution: Tokens as They Arrive

Syrin's streaming API lets you yield response chunks in real-time:

```python
from syrin import Agent, Model

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
)

# Stream tokens as they arrive
for chunk in agent.stream("Write a haiku about coding"):
    print(chunk.text, end="", flush=True)
```

**Output:**
```
Code flows like streams
Logic builds on logic blocks
The bug finds its host
```

Words appear letter by letter, just like users expect.

## Why Streaming Matters

### The Wait Problem

Without streaming, users stare at a blank screen:

1. User asks a question
2. Agent thinks... (5-30 seconds)
3. Complete response appears

**This feels slow, even if it isn't.** Users don't know if anything is happening.

### The Streaming Solution

With streaming, users see progress:

1. User asks a question
2. First tokens appear immediately
3. Words keep flowing
4. Complete response arrives

**This feels fast.** Users see the agent working.

## Two Streaming Methods

Syrin provides two streaming APIs:

| Method | Use Case |
|--------|----------|
| `stream()` | Synchronous streaming (CLI, scripts) |
| `astream()` | Async streaming (FastAPI, WebSockets) |

## Synchronous Streaming

For scripts and CLI tools, use `stream()`:

```python
from syrin import Agent, Model

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    system_prompt="You are a helpful assistant.",
)

print("Agent: ", end="", flush=True)
for chunk in agent.stream("What is Python?"):
    print(chunk.text, end="", flush=True)
print()
```

### How It Works

Each `chunk` is a `StreamChunk` with:

```python
for chunk in agent.stream("Hello"):
    print(f"Index: {chunk.index}")
    print(f"Text: '{chunk.text}'")          # Delta (new text)
    print(f"Accumulated: '{chunk.accumulated_text}'")  # Full text so far
    print(f"Cost so far: ${chunk.cost_so_far:.6f}")
```

**Output:**
```
Index: 0
Text: 'Hello'
Accumulated: 'Hello'
Cost so far: $0.000000

Index: 1
Text: ','
Accumulated: 'Hello,'
Cost so far: $0.000010

Index: 2
Text: ' how'
Accumulated: 'Hello, how'
Cost so far: $0.000020
```

### Collecting the Full Response

```python
chunks = list(agent.stream("Tell me a story"))
full_text = "".join(chunk.text for chunk in chunks)

print(f"Total chunks: {len(chunks)}")
print(f"Full text: {full_text[:100]}...")
```

## Async Streaming

For web applications, use `astream()`:

```python
import asyncio
from syrin import Agent, Model

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
)

async def stream_response():
    async for chunk in agent.astream("Write a poem"):
        yield chunk.text

async def main():
    async for text in stream_response():
        print(text, end="", flush=True)

asyncio.run(main())
```

### With FastAPI

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from syrin import Agent, Model

app = FastAPI()

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
)

@app.post("/stream")
async def stream_chat(message: str):
    async def generate():
        async for chunk in agent.astream(message):
            yield f"data: {chunk.text}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )
```

## The StreamChunk Object

Each chunk contains everything you need for a real-time UI:

```python
@dataclass
class StreamChunk:
    index: int              # Chunk number (0, 1, 2, ...)
    text: str              # New text in this chunk (delta)
    accumulated_text: str   # Full text received so far
    cost_so_far: float     # Running cost in USD
    tokens_so_far: TokenUsage  # Running token count
    is_final: bool        # True for the last chunk
    response: Response    # Final Response object (last chunk only)
```

### Building a Progress Indicator

```python
for chunk in agent.stream("Long response here..."):
    # Update progress bar
    progress = f"Tokens: {chunk.tokens_so_far.total_tokens}"
    cost = f"Cost: ${chunk.cost_so_far:.4f}"
    print(f"\r{progress} | {cost}", end="", flush=True)
    
print()  # New line after streaming completes
```

## Streaming with the Playground

The easiest way to see streaming in action is the built-in playground:

```python
from syrin import Agent, Model

class StreamingAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")
    system_prompt = "You are a helpful assistant."

agent = StreamingAgent()
agent.serve(port=8000, enable_playground=True, debug=True)
```

Visit **http://localhost:8000/playground** to chat with your agent and see tokens stream in real-time.

## Important: Streaming vs Full Execution

**Critical difference:** `stream()` and `astream()` do **one LLM call only**. No tools execute during streaming.

| Feature | `response()` / `arun()` | `stream()` / `astream()` |
|---------|--------------------------|-------------------------|
| Tool execution | ✅ Full loop | ❌ None |
| Memory ops | ✅ | ❌ |
| Guardrails | ✅ | ❌ |
| Returns | `Response` object | `Iterator[StreamChunk]` |

### Why No Tools During Streaming?

Streaming is a low-level LLM feature. The model generates tokens; Syrin passes them through. Tool execution requires state management between calls.

**For full functionality, use `response()` or `arun()`.** If you also want streaming, build your UI to progressively display the response.

## Observability: Streaming Hooks

Track streaming with hooks:

```python
from syrin import Agent, Model, Hook

agent = Agent(
    model=Model.OpenAI("gpt-4o"),
)

def on_llm_start(ctx: dict) -> None:
    print("Streaming started...")

def on_llm_stream(ctx: dict) -> None:
    print(f"Chunk {ctx.get('index', 0)}: {ctx.get('text', '')}")

def on_llm_end(ctx: dict) -> None:
    print(f"Streaming ended. Total cost: ${ctx.get('cost', 0):.6f}")

agent.events.on(Hook.LLM_REQUEST_START, on_llm_start)
agent.events.on(Hook.LLM_STREAM_CHUNK, on_llm_stream)
agent.events.on(Hook.LLM_REQUEST_END, on_llm_end)
```

## Complete Example: Chat Interface

```python
from syrin import Agent, Model

class ChatAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key")
    system_prompt = "You are a helpful assistant. Be concise."

agent = ChatAgent()

print("Chat with your agent (type 'quit' to exit)")
print("-" * 40)

while True:
    user_input = input("\nYou: ")
    if user_input.lower() == "quit":
        break
    
    print("\nAgent: ", end="")
    
    total_cost = 0
    for chunk in agent.stream(user_input):
        print(chunk.text, end="", flush=True)
        total_cost = chunk.cost_so_far
    
    print(f"\n[Cost: ${total_cost:.6f}]")
```

**Output:**
```
Chat with your agent (type 'quit' to exit)
----------------------------------------

You: What is AI?

Agent: AI, or Artificial Intelligence, is the simulation of human 
intelligence by machines. It enables computers to learn from 
experience, understand language, recognize images, and make decisions.
[Cost: $0.000142]
```

## Server-Sent Events (SSE)

For web clients, stream using Server-Sent Events:

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import json

app = FastAPI()

@app.post("/chat/stream")
async def chat_stream(message: str):
    async def event_generator():
        async for chunk in agent.astream(message):
            # SSE format: "data: <message>\n\n"
            yield f"data: {json.dumps({'text': chunk.text})}\n\n"
        # Send completion signal
        yield "data: {\"done\": true}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
```

**Client-side JavaScript:**
```javascript
const response = await fetch('/chat/stream', {
    method: 'POST',
    body: JSON.stringify({ message: 'Hello!' }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const text = decoder.decode(value);
    const data = JSON.parse(text.replace('data: ', ''));
    
    if (data.done) {
        console.log('Stream complete!');
    } else {
        document.getElementById('output').textContent += data.text;
    }
}
```

## Budget Tracking During Streaming

Costs accumulate during streaming. Track them with each chunk:

```python
for chunk in agent.stream("Expensive query"):
    # Update UI with current cost
    update_cost_display(chunk.cost_so_far)
    
    # Check if approaching budget limit
    if chunk.cost_so_far > 0.10:
        print("\n⚠️ Approaching budget limit!")
        break

# After streaming: check final budget state
print(f"Final cost: ${agent.budget_state.spent:.6f}")
```

## Troubleshooting

### Streaming is slow to start

The first token depends on the model's time-to-first-token. Large models like GPT-4 are slower than GPT-4o-mini.

```python
# Faster: gpt-4o-mini starts outputting faster
agent = Agent(model=Model.OpenAI("gpt-4o-mini"))

# Or: Reduce latency by lowering max_tokens
result = list(agent.stream("Short answer", max_tokens=100))
```

### Chunks are too large/small

Chunk sizes depend on the model and provider. Some models buffer more than others.

```python
# Accumulate chunks for smoother display
buffer = ""
buffer_size = 5  # Words per update

for chunk in agent.stream("Text"):
    buffer += chunk.text
    if len(buffer.split()) >= buffer_size:
        print(buffer, end="", flush=True)
        buffer = ""
```

### Handling disconnection

If the client disconnects mid-stream:

```python
async def safe_stream(message: str):
    try:
        async for chunk in agent.astream(message):
            yield chunk.text
    except Exception as e:
        print(f"Stream interrupted: {e}")
```

## What's Next?

- [Structured Output](/agent-kit/agent/structured-output) — Get typed responses
- [Tools](/agent-kit/agent/tools) — Extend agent capabilities
- [Serving](/agent-kit/production/serving) — Serve agents over HTTP

## See Also

- [Running Agents](/agent-kit/agent/running-agents) — All execution modes
- [Response Object](/agent-kit/agent/response-object) — Full Response breakdown
- [Agent Configuration](/agent-kit/agent/agent-configuration) — All options
