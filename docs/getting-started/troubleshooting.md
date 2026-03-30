---
title: Troubleshooting
description: Common errors and how to fix them
weight: 4
---

# Troubleshooting

## When Things Go Wrong (They Will, And That's Okay)

Don't panic. Most issues have simple fixes. Let's solve them together.

## Quick Fixes First

Try these before digging deeper:

1. **Restart your Python session** - Import caches sometimes cause issues
2. **Upgrade Syrin** - `pip install --upgrade syrin`
3. **Check your API key** - Make sure it's valid and has credits
4. **Read the error message** - It usually tells you what's wrong

## Common Errors

### Installation Issues

#### `ModuleNotFoundError: No module named 'syrin'`

**Cause:** Syrin is not installed or you're not in the right environment.

**Fix:**

```bash
pip install syrin
```

If you're using a virtual environment, make sure it's activated:

```bash
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install syrin
```

---

#### `ImportError: cannot import name 'Agent'`

**Cause:** You're importing from an old version or the wrong package.

**Fix:**

```bash
pip install --upgrade syrin
```

Then verify:

```python
import syrin
print(syrin.__version__)
```

---

### API Key Issues

#### `AuthenticationError: Invalid API key`

**Cause:** Your API key is wrong, expired, or lacks permissions.

**Fix:**

1. Check your API key is correct (no extra spaces)
2. Verify the key has not expired
3. Check your account has credits/quota

```python
# Make sure you're using the correct key format
model = Model.OpenAI("gpt-4o", api_key="sk-...")
```

---

#### `RateLimitError: You exceeded your current quota`

**Cause:** You've exceeded your API usage limit.

**Fix:**

1. Check your OpenAI dashboard for usage
2. Wait for the quota to reset
3. Consider adding a budget to prevent overspending:

```python
from syrin import Budget

agent = MyAgent(
    model=Model.OpenAI("gpt-4o", api_key="your-key"),
    budget=Budget(max_cost=1.00)  # Stop after $1 spent
)
```

---

### Model Issues

#### `Model not found` / `Invalid model name`

**Cause:** The model name is incorrect or not available.

**Fix:**

Check you're using a valid model name:

| Provider | Valid Models |
|---------|--------------|
| OpenAI | `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-3.5-turbo` |
| Anthropic | `claude-3-5-sonnet-latest`, `claude-3-opus-latest` |
| Google | `gemini-1.5-pro`, `gemini-1.5-flash` |

---

#### `Context length exceeded`

**Cause:** Your conversation is too long for the model's context window.

**Fix:**

Use context management to limit tokens:

```python
from syrin import Context

agent = MyAgent(
    context=Context(max_tokens=6000)  # Keep under limit
)
```

Or enable automatic compaction:

```python
from syrin import Context
from syrin.threshold import ContextThreshold

agent = MyAgent(
    context=Context(
        max_tokens=80000,
        thresholds=[
            ContextThreshold(at=75, action=lambda ctx: ctx.compact() if ctx.compact else None)
        ]
    )
)
```

---

### Serving Issues

#### `uvicorn not found`

**Cause:** The serve extra is not installed.

**Fix:**

```bash
pip install syrin[serve]
```

---

#### `Address already in use` when serving

**Cause:** Port 8000 is already in use.

**Fix:**

Use a different port:

```python
agent.serve(port=8001, enable_playground=True, debug=True)
```

Or find and stop the process using port 8000:

```bash
# Linux/Mac
lsof -i :8000
kill -9 <PID>

# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

---

### Memory Issues

#### `Memory backend error`

**Cause:** There's an issue with the memory storage backend.

**Fix:**

For SQLite backend, make sure the directory exists:

```python
from syrin import Memory
import os

os.makedirs(".syrin", exist_ok=True)

memory = Memory(
    backend=MemoryBackend.SQLITE,
    path=".syrin/memory.db"
)
```

For Redis, ensure the server is running:

```bash
redis-server
```

---

### Response Issues

#### `Response is None` / `No content returned`

**Cause:** The model didn't produce a response.

**Fix:**

1. Check your system prompt is clear
2. Make sure the user message is not empty
3. Verify your API key works with a simple test:

```python
response = agent.run("Hello, please respond with 'Hi'")
if response.content:
    print("Working!")
else:
    print(f"Issue: {response.stop_reason}")
```

---

#### `Stop reason: budget`

**Cause:** You've hit your spending limit.

**Fix:**

Check your budget configuration or increase it:

```python
from syrin import Budget, RateLimit

agent = MyAgent(
    budget=Budget(
        max_cost=5.00,  # Increase to $5 per run
        rate_limits=RateLimit(day=50.00)  # $50 per day
    )
)
```

---

## Debug Mode

Enable debug mode to see what's happening:

```python
agent = MyAgent(
    model=Model.OpenAI("gpt-4o", api_key="your-key"),
    debug=True  # Shows detailed logs
)
```

Or when serving:

```python
agent.serve(port=8000, enable_playground=True, debug=True)
```

Debug mode shows:
- LLM calls and responses
- Token usage
- Tool executions
- Budget tracking
- Timing information

---

## Getting Help

Still stuck? Here's where to get help:

1. **Check the docs** - Search for your error message
2. **GitHub Issues** - Search for similar issues
3. **Discord/Slack community** - Ask the community
4. **Forum** - Post your question

### When Reporting Issues

Include:

- Syrin version (`pip show syrin`)
- Python version (`python --version`)
- Full error message
- Minimal code that reproduces the issue
- Steps to reproduce

---

## What's Next?

- [Quick Start](/agent-kit/getting-started/quick-start) - Back to building
- [Agents Overview](/agent-kit/agent/overview) - Understand agents better
- [Debugging](/agent-kit/debugging/overview) - Advanced debugging tools

## See Also

- [Budget](/agent-kit/core/budget) - Control your spending
- [Memory](/agent-kit/core/memory) - Memory troubleshooting
- [Serving](/agent-kit/production/serving) - Serving issues
