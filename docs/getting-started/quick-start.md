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

## Complete Example

Here's everything together:

```python
from syrin import Agent, Model
from syrin.task import task

class MyAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key-here")
    # No API key? Use: model = Model.Almock()
    system_prompt = "You are a helpful assistant. Be concise."
    
    @task
    def summarize(self, text: str) -> str:
        """Summarize text in one sentence."""
        return self.run(f"Summarize: {text}").content

# Create and use
agent = MyAgent()
response = agent.run("Hello!")
print(response.content)

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

## What's Next?

- [Agents Overview](/agent/overview) - Understand how agents work
- [Models](/core/models) - Use real AI models (OpenAI, Claude)
- [Tools](/agent/tools) - Give your agent special abilities
- [Memory](/core/memory) - Make your agent remember things

## See Also

- [Tasks](/agent/tasks) - More about @task decorator
- [Response Object](/agent/response-object) - Full Response breakdown
- [Serving](/production/serving) - More serving options
- [Hooks & Events](/debugging/hooks) - Full observability with hooks
