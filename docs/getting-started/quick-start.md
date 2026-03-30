---
title: Quick Start
description: Build and run your first AI agent in 5 minutes
weight: 3
---

# Quick Start

## Build Your First Agent (Finally, Something That Works)

> **Note:** This guide uses OpenAI by default. If you don't have an API key, use `Model.Almock()` instead (a mock that returns lorem ipsum—just to see the library working).

Let's build a simple helpful assistant. No complex setup, no scattered libraries—just you and a working agent.

### Step 1: Create Your Agent

Make a file called `my_agent.py`:

```python
from syrin import Agent, Model

# Define your agent as a Python class
class MyAgent(Agent):
    # The brain: which AI model to use
    model = Model.OpenAI("gpt-4o", api_key="your-api-key-here")
    # No API key? Use: model = Model.Almock()  # Returns lorem ipsum

    # The instruction: how your agent should behave
    system_prompt = "You are a helpful assistant. Be concise."
```

> **Tip:** In production, use environment variables instead of hardcoding keys:
> ```python
> import os
> model = Model.OpenAI("gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
> ```

**What just happened?**
- You created an agent class that inherits from `Agent`
- `model` tells the agent which AI to use
- `system_prompt` gives your agent personality and rules

### Step 2: Run Your Agent

Add this to the same file and run it:

```python
# Create an instance of your agent
agent = MyAgent()

# Send a message and get a response
response = agent.run("Hello! What can you do?")

# Print what the agent said
print(response.content)
```

Run it:

```bash
python my_agent.py
```

**You should see something like:**

```
Hello! I'm a helpful assistant. I can answer questions, help with tasks, and have conversations. What would you like help with?
```

**What just happened?**
- `MyAgent()` creates a running instance of your agent
- `agent.run("...")` sends a message and waits for the answer
- `response.content` is the text the AI generated

### Step 3: Meet the Response

The `response` object contains more than just text. Let's see what else is there:

```python
response = agent.run("What is 2 + 2?")

print(f"Answer: {response.content}")
print(f"Cost: ${response.cost:.6f}")
print(f"Tokens used: {response.total_tokens}")
print(f"Stop reason: {response.stop_reason}")
```

**Output:**

```
Answer: 2 + 2 equals 4.
Cost: $0.000123
Tokens used: 42
Stop reason: end_turn
```

| Property | What It Means |
|----------|---------------|
| `content` | The text response from the AI |
| `cost` | How much this call cost in USD |
| `total_tokens` | Total tokens used (input + output) |
| `stop_reason` | Why the AI stopped (end_turn, tool_call, etc.) |

> **Want to see what happened inside?** Set `debug=True` when creating your agent:
> ```python
> agent = MyAgent(debug=True)  # Prints all events to console
> ```
> Or subscribe to specific hooks: `agent.events.on(Hook.LLM_REQUEST_END, handler)`

### Step 4: Add a Task

Tasks are structured methods your agent can perform. Let's add one:

```python
from syrin import Agent, Model
from syrin.task import task

class MyAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key-here")
    # No API key? Use: model = Model.Almock()
    system_prompt = "You are a helpful assistant. Be concise."

    @task
    def summarize(self, text: str) -> str:
        """Summarize the given text in one sentence."""
        return self.run(f"Give me a one-sentence summary: {text}").content
```

Now you can call your task directly:

```python
agent = MyAgent()

# Call the task like any other method
long_text = "Python is a programming language that was created by Guido van Rossum. It was first released in 1991. Python is known for its simple syntax and readability."

summary = agent.summarize(long_text)
print(summary)
```

**Output:**

```
Python is a high-level, general-purpose programming language created by Guido van Rossum in 1991, known for its simple syntax and readability.
```

### Step 5: Serve Your Agent

Want to chat with your agent in a browser? One line:

```python
from syrin import Agent, Model

class MyAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key-here")
    # No API key? Use: model = Model.Almock()
    system_prompt = "You are a helpful assistant. Be concise."

agent = MyAgent()

# Serve with a web playground
agent.serve(port=8000, enable_playground=True, debug=True)
```

Run it and visit: **http://localhost:8000/playground**

You'll see a chat interface where you can talk to your agent!

## What Just Happened?

Here's the flow:

1. **Define Agent Class** — Set `model` and `system_prompt`
2. **Create Instance** — `agent = MyAgent()`
3. **Send Message** — `response = agent.run("Hello!")`
4. **Get Response** — Access `response.content`

## Structured Output

Use `Output(MyModel)` to receive typed, validated responses instead of raw strings. Pass a Pydantic model and syrin enforces the schema automatically.

```python
from pydantic import BaseModel
from syrin import Agent, Model, Output

class Summary(BaseModel):
    headline: str
    body: str
    word_count: int

class MyAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key-here")
    system_prompt = "You are a helpful assistant."

agent = MyAgent()

# Output(MyModel) ensures the response matches your schema
response = agent.run(
    "Summarize the history of Python.",
    output=Output(Summary),
)

result: Summary = response.output
print(result.headline)
print(result.word_count)
```

`Output(MyModel)` works the same way across all five common patterns:

```python
# 1. Simple Q&A
response = agent.run("What is the capital of France?", output=Output(Answer))

# 2. Extraction
response = agent.run("Extract entities from: ...", output=Output(Entities))

# 3. Classification
response = agent.run("Classify the sentiment of: ...", output=Output(Sentiment))

# 4. Planning
response = agent.run("Create a weekly plan for: ...", output=Output(Plan))

# 5. Summarization
response = agent.run("Summarize this document: ...", output=Output(Summary))
```

> **Note:** `response.output` holds the parsed model instance. `response.content` still holds the raw text.

## Budget Management

syrin enforces cost limits at the agent level. Set a `budget` to cap spending, then optionally switch the model when the budget runs low.

```python
from syrin import Agent, Model
from syrin.budget import Budget
from syrin.enums import OnExceeded

class MyAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key-here")
    system_prompt = "You are a helpful assistant."
    budget = Budget(limit=0.10, on_exceeded=OnExceeded.ERROR)  # $0.10 cap

agent = MyAgent()

# Switch to a cheaper model if budget is running low
if agent.budget_remaining < 0.02:
    agent.switch_model(Model.OpenAI("gpt-4o-mini", api_key="your-api-key-here"))

response = agent.run("Hello!")
print(f"Remaining budget: ${agent.budget_remaining:.4f}")
```

`switch_model()` takes effect immediately on the next `run()` call without recreating the agent. All context, memory, and hooks remain intact.

### Wrapping Non-Agent Callables with syrin.budget_wrap()

If you have existing functions that call LLMs directly, `syrin.budget_wrap()` enforces a budget without requiring you to refactor them into an `Agent` subclass.

```python
import syrin
from syrin.budget import Budget
from syrin.enums import OnExceeded

async def fetch_summary(text: str) -> str:
    # An existing function that calls an LLM internally
    ...

# Wrap with a $0.05 budget; raises BudgetExceededError when limit is hit
guarded = syrin.budget_wrap(
    fetch_summary,
    budget=Budget(limit=0.05, on_exceeded=OnExceeded.ERROR),
)

result = await guarded("Summarize this article...")
```

`budget_wrap()` tracks cumulative cost across repeated calls to the same wrapped function instance, so the $0.05 cap applies to the total spend over the lifetime of `guarded`, not per call.

## Memory

`syrin.Memory()` gives your agent persistent, typed memory across runs. There are four memory types: `Core`, `Episodic`, `Semantic`, and `Procedural`. All memory operations are budget-aware.

```python
from syrin import Agent, Model
from syrin.memory import Memory, MemoryType

class MyAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key-here")
    system_prompt = "You are a helpful assistant."
    memory = Memory()

agent = MyAgent()

# Store a fact
agent.memory.remember("User prefers concise answers.", kind=MemoryType.CORE)

# Recall relevant memories before running
recalled = agent.memory.recall("user preferences")
print(recalled)

# Forget a specific memory by ID
agent.memory.forget(memory_id="mem-001")
```

> **Note:** Always pass `kind=` as a keyword argument. Positional argument order for `MemoryType` is not guaranteed across versions.

## Complete Example

Here's everything together:

```python
from pydantic import BaseModel
from syrin import Agent, Model, Output
from syrin.budget import Budget
from syrin.enums import OnExceeded
from syrin.memory import Memory, MemoryType
from syrin.task import task

class Summary(BaseModel):
    headline: str
    body: str

class MyAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key-here")
    # No API key? Use: model = Model.Almock()
    system_prompt = "You are a helpful assistant. Be concise."
    budget = Budget(limit=0.10, on_exceeded=OnExceeded.ERROR)
    memory = Memory()

    @task
    def summarize(self, text: str) -> str:
        """Summarize text in one sentence."""
        return self.run(f"Summarize: {text}").content

# Create and use
agent = MyAgent()
agent.memory.remember("User prefers bullet points.", kind=MemoryType.CORE)

# Plain text response
response = agent.run("Hello!")
print(response.content)

# Structured output
structured = agent.run("Summarize Python's history.", output=Output(Summary))
print(structured.output.headline)

# Or call a task
summary = agent.summarize("Python is a great programming language.")
print(summary)

# Or serve it
agent.serve(port=8000, enable_playground=True, debug=True)
```

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Agent is not defined` | Forgot to import | Add `from syrin import Agent` |
| `No module named 'syrin'` | Not installed | Run `pip install syrin` |
| `Model.Almock not found` | Wrong import | Use `Model.Almock()` not `Model.Almock` |
| `BudgetExceededError` | Agent hit its cost cap | Raise the `Budget.limit` or use `OnExceeded.WARN` |

## What's Next?

- [Agents Overview](/agent-kit/agent/overview) - Understand how agents work
- [Models](/agent-kit/core/models) - Use real AI models (OpenAI, Claude)
- [Tools](/agent-kit/agent/tools) - Give your agent special abilities
- [Memory](/agent-kit/core/memory) - Make your agent remember things

## See Also

- [Tasks](/agent-kit/agent/tasks) - More about @task decorator
- [Response Object](/agent-kit/agent/response-object) - Full Response breakdown
- [Serving](/agent-kit/production/serving) - More serving options
- [Hooks & Events](/agent-kit/debugging/hooks) - Full observability with hooks
- [Budget Management](/agent-kit/core/budget) - Full budget reference
- [Structured Output](/agent-kit/agent/structured-output) - Output schemas in depth
