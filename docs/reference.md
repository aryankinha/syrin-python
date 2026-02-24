# Feature Reference Guide

Complete reference for all Syrin features. Use this as a lookup when building agents.

> **Agent vs standalone:** See [Architecture](ARCHITECTURE.md) to understand which components require an Agent and which work independently.

## Core Components

### Agent

The main class for creating AI agents.

```python
import os
from syrin import Agent, Model

class MyAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
    system_prompt = "You are helpful"
    tools = []  # Optional tools
    
    def __init__(self):
        super().__init__()
        # Optional: add memory, budget, etc.
```

**Key Methods:**
- `agent.response(prompt)` - Get a response
- `agent.astream(prompt)` - Stream response piece by piece
- `agent.aresponse(prompt)` - Async get response

---

## Models

See **[Models Guide](models.md)** for the complete documentation:
- Built-in models (OpenAI, Anthropic, Google, Ollama, LiteLLM)
- Model.Custom for third-party OpenAI-compatible APIs
- Custom models via inheritance and `make_model()`
- Tweakable properties (temperature, max_tokens, context_window, etc.)
- Fallbacks, structured output, centralized definitions

Quick reference:

```python
import os
from syrin import Model

Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
Model.Anthropic("claude-sonnet", api_key=os.getenv("ANTHROPIC_API_KEY"))
Model.Custom("deepseek-chat", api_base="https://api.deepseek.com/v1", api_key="...")
```

---

## Tools

Give agents the ability to do things.

```python
from syrin import tool

@tool
def my_tool(param1: str, param2: int = 10) -> dict:
    """Tool description for AI."""
    return {"result": "value"}

class MyAgent(Agent):
    tools = [my_tool]
```

**Supported Types:**
- `str` - Text
- `int` - Whole numbers
- `float` - Decimals
- `bool` - True/False
- `list` - Arrays
- `dict` - Objects
- `Optional[Type]` - May be None

---

## Budget Management

Control costs (USD) and prevent overspending. Budget is **spend only**; for token usage caps use **TokenLimits** separately — see [Budget Control](budget-control.md).

```python
import os
from syrin import Agent, Budget, RateLimit, Model, raise_on_exceeded
from syrin.threshold import BudgetThreshold

class BudgetAgent(Agent):
    def __init__(self):
        super().__init__()
        self.budget = Budget(
            run=0.10,                              # Max $0.10 per request
            per=RateLimit(hour=5.00, day=50.00, month=500.00),
            on_exceeded=raise_on_exceeded,        # or warn_on_exceeded
            thresholds=[
                BudgetThreshold(at=80, action=lambda ctx: print(f"Budget at {ctx.percentage}%")),
                BudgetThreshold(at=95, action=lambda ctx: ctx.parent.switch_model(Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY")))),
            ]
        )
```

**on_exceeded:** Pass a callback. Use `raise_on_exceeded` to stop and raise, or `warn_on_exceeded` to log and continue.

---

## Memory

Make agents remember things.

```python
from syrin import Agent, Memory

class MemoryAgent(Agent):
    def __init__(self):
        super().__init__()
        self.memory = Memory()
```

**Memory Types:**
- `CORE` - User identity/preferences
- `EPISODIC` - Specific events
- `SEMANTIC` - General facts
- `PROCEDURAL` - Learned behaviors

**Decay Strategies:**
- `EXPONENTIAL` - Old memories fade fast
- `LINEAR` - Fade at constant rate
- `LOGARITHMIC` - Fade slowly
- `STEP` - Disappear suddenly
- `NONE` - Never fade

---

## Response Object

What you get back from `agent.response()`:

```python
response = agent.response("Hello")

response.content          # The answer text
response.cost             # $ spent
response.tokens           # Tokens used
response.model            # Which model
response.duration         # Seconds taken
response.stop_reason      # Why it stopped
response.tool_calls       # Tools used
response.budget_remaining # Budget left
response.budget_used      # Budget used
response.raw             # Raw API response
```

---

## Enums (Options)

Use these constants instead of strings:

```python
from syrin import LoopStrategy

# For budgets
warn_on_exceeded
raise_on_exceeded

# For loops
LoopStrategy.REACT  # Think-Act-Observe (default)
LoopStrategy.SINGLE_SHOT  # Single response
LoopStrategy.PLAN_EXECUTE  # Plan then execute
LoopStrategy.CODE_ACTION  # Generate and execute code
```

---

## Examples by Task

### Simple Q&A
See [Use Case 1: Simple Q&A Agent](simple-qa-agent.md)

### With Tools
See [Use Case 2: Research Agent with Tools](research-agent-with-tools.md)

### With Memory
See [Use Case 3: Agent with Memory](agent-with-memory.md)

### Budget Control
See [Use Case 4: Budget Control](budget-control.md)

### Multi-Agent Teams
See [Use Case 5: Multi-Agent Orchestration](multi-agent.md)

### Streaming
See [Use Case 6: Streaming](streaming.md)

---

## Quick Reference: Common Patterns

### Pattern 1: Basic Agent

```python
import os
from syrin import Agent, Model

class SimpleAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
    system_prompt = "Help users"

agent = SimpleAgent()
response = agent.response("Your question")
print(response.content)
```

### Pattern 2: Agent with Tools

```python
import os
from syrin import Agent, Model, tool

@tool
def do_something(param: str) -> dict:
    """Do something."""
    return {"result": param.upper()}

class ToolAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
    tools = [do_something]

agent = ToolAgent()
response = agent.response("Use your tool")
```

### Pattern 3: Agent with Memory

```python
import os
from syrin import Agent, Memory, Model

class MemoryAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
    
    def __init__(self):
        super().__init__()
        self.memory = Memory()

agent = MemoryAgent()
agent.response("Remember: my name is Alice")
agent.response("What's my name?")  # It remembers!
```

### Pattern 4: Agent with Budget

```python
import os
from syrin import Agent, Budget, Model, raise_on_exceeded

class BudgetAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
    
    def __init__(self):
        super().__init__()
        self.budget = Budget(
            run=0.10,
            on_exceeded=raise_on_exceeded
        )

agent = BudgetAgent()
response = agent.response("Do something")
print(f"Cost: ${response.cost:.4f}")
```

### Pattern 5: Multiple Agents

```python
import os
from syrin import Agent, Model

class Agent1(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
    system_prompt = "You are Agent 1"

class Agent2(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
    system_prompt = "You are Agent 2"

a1 = Agent1()
a2 = Agent2()

r1 = a1.response("Question 1")
r2 = a2.response("Question 2")
```

### Pattern 6: Streaming

```python
import os
from syrin import Agent, Model

class StreamAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))

agent = StreamAgent()

for chunk in agent.astream("Your prompt"):
    print(chunk.text, end="", flush=True)
```

---

## Troubleshooting

**"API key not found"**
- Pass `api_key` explicitly: `Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))`
- The library does not auto-read API keys from environment variables

**"Model not found"**
- Check model name spelling
- Make sure API credentials are valid
- Verify you have API credits

**"Budget exceeded"**
- Check your budget settings
- Use cheaper models (gpt-4o-mini, claude-3-haiku)
- Reduce the scope of requests

**"Tool not working"**
- Make sure tool returns a dict
- Check parameter types match usage
- Verify tool is in agent.tools list

---

## Performance Tips

1. **Use right model**
   - Testing: Use gpt-4o-mini
   - Production: Use gpt-4o or claude-3-sonnet
   - Advanced: Use gpt-4 or claude-3-opus

2. **Set budgets**
   - Always set per-request budget
   - Add daily/monthly limits

3. **Use tools wisely**
   - Keep tools simple
   - Don't overload with tools
   - Document tool purpose clearly

4. **Stream for large responses**
   - Use `astream()` for essays/stories
   - Use `run()` for short responses

5. **Cache prompts**
   - Reuse agent instances
   - Don't recreate agents per request

---

## Useful Links

- [OpenAI Models](https://platform.openai.com/docs/models)
- [Anthropic Claude](https://console.anthropic.com/)
- [Google Gemini](https://ai.google.dev/)
- [Local Models with Ollama](https://ollama.ai/)

---

## Examples Repository

All examples are in `/examples/` directory:
- `examples/phase1_basic_agent.py` - Basic agent
- `examples/phase2_memory_system.py` - Memory
- `examples/phase3_multi_agent.py` - Multi-agent
- `examples/phase4_budget_testing.py` - Budget
- `examples/phase5_async_streaming.py` - Streaming
- `examples/advanced/` - Advanced patterns

---

## Next Steps

- Pick a [Use Case Guide](#examples-by-task)
- Try building your own agent
- Check examples in `/examples/`
- Read [Getting Started](getting-started.md) again if stuck

---

**Need help?** Check the [FAQ](getting-started.md#common-questions)
