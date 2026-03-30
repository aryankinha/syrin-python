---
title: Playground
description: Web-based testing interface for agents
weight: 110
---

## See Your Agent in Action

You built a great agent. Now you need to test it, see what it's doing, and debug when things go wrong. The Playground is a built-in web UI that gives you exactly that.

## The Problem

Testing agents is hard:
- Text-based testing doesn't show you what's happening inside
- You can't see which hooks are firing
- Budget consumption is invisible
- Streaming feels laggy without visual feedback

The Playground solves this with a real-time chat interface, budget gauge, and observability panel.

## Quick Start

```python
from syrin import Agent, Model, Budget

model = Model.OpenAI("gpt-4o", api_key="your-api-key")

agent = Agent(
    model=model,
    system_prompt="You are a helpful assistant.",
    budget=Budget(max_cost=1.00),
)

# Enable playground and debug mode
agent.serve(port=8000, enable_playground=True, debug=True)
```

**Visit:** `http://localhost:8000/playground`

**What you'll see:**
- Chat interface for sending messages
- Budget gauge showing remaining balance
- Response streaming in real-time
- Cost and token counts after each response
- (With debug mode) Collapsible observability panel showing hook events

## Features

### Chat Interface

- Send messages and receive streaming responses
- Conversation history within the session
- Dark theme optimized for readability

### Budget Gauge

Shows real-time budget consumption:

```
Budget: $0.0015 spent, $0.9985 remaining (0.15% used)
```

The gauge updates after each response and on `/stream` events.

### Real-Time Streaming

Responses stream as they arrive from the model. You see text appear character by character (or chunk by chunk).

### Observability Panel (Debug Mode)

When `debug=True`, a collapsible panel shows lifecycle hooks:

```
Observability (debug)
├── AGENT_RUN_START
│   └── {iteration: 0, input: "Hello", model: "gpt-4o"}
├── LLM_CALL_START
│   └── {model: "gpt-4o", tokens: {...}}
├── LLM_CALL_END
│   └── {tokens: {...}, cost: 0.0001}
├── TOOL_CALL_START
│   └── {name: "remember_fact", arguments: {...}}
├── TOOL_CALL_END
│   └── {name: "remember_fact", result: "Remembered: user prefers dark mode"}
├── AGENT_RUN_END
│   └── {content: "I've noted your preference...", cost: 0.0003}
```

**Benefits:**
- Verify hooks fire in expected order
- See token counts and costs per operation
- Debug why a tool wasn't called
- Monitor context pressure

### Multi-Agent Selection

With `AgentRouter`, the playground shows an agent selector:

```python
from syrin.serve import AgentRouter

router = AgentRouter(agents=[researcher, writer])
router.serve(config=ServeConfig(enable_playground=True, debug=True))
```

The playground dropdown lets you switch between agents:

```
┌─ Playground ────────────────────────┐
│ Agent: [Researcher ▼]               │
│                                     │
│ Budget: $0.50 spent, $0.50 remaining │
│                                     │
│ [Messages appear here...]            │
│                                     │
│ > Type a message...         [Send]  │
└─────────────────────────────────────┘
```

### Playground Configuration

```python
from syrin import Agent, Model, ServeConfig

agent = Agent(model=model, system_prompt="You are a helpful assistant.")
agent.serve(
    config=ServeConfig(
        enable_playground=True,
        debug=True,  # Enable observability panel
        route_prefix="/playground",  # Available at /playground/chat
    )
)
```

## Configuration Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enable_playground` | `bool` | `False` | Serve the web UI |
| `debug` | `bool` | `False` | Show observability panel |
| `route_prefix` | `str` | `""` | URL prefix for routes |

**Important**: The observability panel only shows when BOTH:
- `enable_playground=True`
- `debug=True`

Without debug mode, you get the chat UI but no hook events.

## How It Works

### Architecture

1. **User sends message** via the chat interface
2. **Frontend calls** `POST /stream` (SSE endpoint)
3. **Backend streams** events as they occur
4. **Frontend renders** tokens, hook events, and budget updates

### Event Types (SSE)

| Event Type | Content | Description |
|------------|---------|-------------|
| `status` | `{"type": "status", "message": "Thinking…"}` | Status update |
| `text` | `{"text": "...", "accumulated": "..."}` | New tokens |
| `budget` | `{"limit": 1.0, "remaining": 0.99, ...}` | Budget snapshot |
| `hook` | `{"hook": "HOOK_NAME", "ctx": {...}}` | Lifecycle event (debug) |
| `done` | `{"done": true, ...}` | Stream complete |

### Hook Collection

When `debug=True`, the server collects all lifecycle hooks:

```python
# Simplified flow
@router.post("/stream")
async def stream(body):
    with _collect_events() as events:
        async for chunk in agent.astream(message):
            yield format_event(chunk)
    
    # Events captured during the request
    yield format_done(cost=cost, events=events)
```

Events are truncated to prevent large payloads:
- Data URLs truncated at 100 characters
- Strings truncated at 200 characters
- Binary content replaced with `<bytes len=N>`

## Playground vs Production

| Feature | Development | Production |
|---------|-------------|------------|
| Playground UI | ✅ Enabled | ❌ Disabled |
| Debug mode | ✅ Enabled | ❌ Disabled |
| Observability panel | ✅ Visible | ❌ Hidden |
| Detailed error messages | ✅ Full | ❌ Sanitized |

### Production Configuration

```python
from syrin import ServeConfig

agent.serve(
    config=ServeConfig(
        enable_playground=False,  # Disable in production
        debug=False,
    )
)
```

**Security note**: The playground has no authentication by default. Always disable it in production or add auth middleware.

## API Endpoints

### GET /playground

Returns the playground HTML page.

### GET /playground/config

Returns configuration for the frontend:

```json
{
  "apiBase": "/",
  "agents": [
    {"name": "assistant", "description": "Helpful assistant"}
  ],
  "debug": true,
  "setup_type": "single"
}
```

**For AgentRouter:**
```json
{
  "apiBase": "/",
  "agents": [
    {"name": "researcher", "description": "Researches topics"},
    {"name": "writer", "description": "Writes content"}
  ],
  "debug": true,
  "setup_type": "multi"
}
```

## Customization

### Inline HTML Fallback

The playground has two modes:
1. **Next.js build**: If `playground/out/` exists, serves compiled static files
2. **Inline HTML**: Otherwise, serves embedded HTML (limited features)

For development, the inline HTML provides full functionality.

### Styling

The inline playground uses CSS variables for theming:

```css
:root {
  --bg: #0f0f12;
  --surface: #1a1a1f;
  --border: #2a2a32;
  --text: #e4e4e7;
  --text-muted: #71717a;
  --accent: #6366f1;
  --user-bubble: #3b82f6;
  --assistant-bubble: #27272a;
}
```

### Building the Next.js Playground

For the full-featured playground with custom styling:

```bash
cd playground
npm install
npm run build
```

The build output at `playground/out/` is served automatically.

## Troubleshooting

### Playground Not Loading

1. **Check it's enabled**: `agent.serve(enable_playground=True)`
2. **Check the URL**: `http://localhost:8000/playground` (not `/playground/`)
3. **Check port**: Default is 8000
4. **Check route_prefix**: May be nested (e.g., `/api/v1/playground`)

### Observability Panel Empty

1. **Enable debug mode**: `agent.serve(debug=True)`
2. **Check browser console**: Events might be truncated
3. **Try a simpler prompt**: Complex agents may have many events

### Streaming Feels Slow

1. **Check network latency**: Localhost is fastest
2. **Check model latency**: Some models are slower
3. **Check streaming**: Ensure `/stream` (not `/chat`) is used

## See Also

- [Serving: HTTP API](/agent-kit/production/serving-http) — REST API reference
- [Serving: Advanced](/agent-kit/production/serving-advanced) — Mounting on existing apps
- [Debugging: Hooks](/agent-kit/debugging/hooks) — Lifecycle hooks reference
- [Debugging: Tracing](/agent-kit/debugging/tracing) — Execution traces
