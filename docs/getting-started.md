# Syrin: Getting Started for Beginners

Welcome to **Syrin**! This guide will help you understand the basics and get your first agent running in minutes.

## What is Syrin?

Think of Syrin as a toolkit for building **AI agents** - programs that can talk to AI (like ChatGPT), remember conversations, do tasks, and control their own costs.

**In simple terms:**
- An **Agent** is a program that can ask an AI questions and get answers
- An **Agent** can remember what happened before (memory)
- An **Agent** can do real work (like search the web, send emails, etc.) using **Tools**
- An **Agent** can have a budget so it doesn't spend too much money

## Installation

```bash
pip install syrin
```

Set your API key (or use `Model.Almock()` to run without one — see [Models Guide](models.md#almock-an-llm-mock)):
```bash
export OPENAI_API_KEY="sk-..."  # or ANTHROPIC_API_KEY for Claude
```

## Your First Completion (Easiest)

The simplest way to get started: call a model directly. No Agent, no classes — just a few lines. Use this when you only need simple Q&A; use an Agent when you need tools, memory, or budget control.

```python
import os
from syrin import Model
from syrin.types import Message
from syrin.enums import MessageRole

# model = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
model = Model.Almock()  # No API Key needed
messages = [
    Message(role=MessageRole.SYSTEM, content="You are helpful."),
    Message(role=MessageRole.USER, content="What is 2 + 2?"),
]
response = model.complete(messages)
print(response.content)  # "4" or "The answer is 4"
```

Use `await model.acomplete(messages)` for async. See the [Models Guide](models.md) for more.

## Your First Agent (30 seconds)

For prompts with tools, memory, or budget, use an Agent:

```python
import os
from syrin import Agent, Model

class SimpleAgent(Agent):
    # model = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
    model = Model.Almock()  # No API Key needed
    system_prompt = "You are a helpful assistant."

agent = SimpleAgent()
response = agent.response("What is 2 + 2?")
print(response.content)  # Output: "4" or "The answer is 4"
```

That's it! You just created an AI agent that can answer questions.

**Tip:** You can tweak model properties: `temperature`, `max_tokens`, `context_window`, etc. See the [Models Guide](models.md) for the full list.

### What just happened?

1. We created a class called `SimpleAgent` that inherited from `Agent`
2. We told it which AI model to use (`gpt-4o-mini` - cheap and fast)
3. We told it how to behave (`system_prompt`)
4. We asked it a question using `agent.response()`
5. We got back a response with the answer

## Next Steps

You can now read the **Use Case Guides** below:

- **[Use Case 1: Simple Q&A Agent](simple-qa-agent.md)** - Ask questions and get answers
- **[Use Case 2: Research Agent with Tools](research-agent-with-tools.md)** - Give your agent the ability to search, calculate, or do other tasks
- **[Use Case 3: Agent with Memory](agent-with-memory.md)** - Make your agent remember past conversations
- **[Use Case 4: Budget Control & Cost Management](budget-control.md)** - Keep your AI spending under control
- **[Use Case 5: Multi-Agent Orchestration](multi-agent.md)** - Create multiple agents that work together
- **[Use Case 6: Streaming & Real-time Updates](streaming.md)** - Get responses as they're being generated

## Important Concepts

### Response Object

When you call `agent.response()`, you get back a `Response` object with useful information:

```python
response = agent.response("Hello!")

response.content         # The actual answer text
response.cost             # How much money was spent (in USD)
response.tokens          # How many tokens were used
response.model           # Which AI model was used
response.duration        # How long it took
```

### Enums (Special Option Lists)

In Syrin, you pass **callbacks** for behavior like "what to do when budget is exceeded". Use the built-in helpers or your own function:

```python
from syrin import Budget, warn_on_exceeded

# Warn and continue when budget exceeded:
budget = Budget(run=1.00, on_exceeded=warn_on_exceeded)

# Or use raise_on_exceeded to stop and raise an error.
```

## Common Questions

**Q: What AI models can I use?**
A: OpenAI, Anthropic, Google, and many more. See the model examples in each use case.

**Q: Will this cost me money?**
A: Yes, AI API calls cost money. But you control the budget! See Use Case 4.

**Q: Can my agent remember things?**
A: Yes! See Use Case 3 about Memory.

**Q: How do I make my agent do things like search the web?**
A: Using Tools! See Use Case 2.

**Q: Can I run code while my agent is thinking?**
A: Yes! See Use Case 6 about Streaming.

## Troubleshooting

### "API Key not found"
- Make sure you set your API key: `export OPENAI_API_KEY="sk-..."`
- Or set it in your code: `os.environ["OPENAI_API_KEY"] = "sk-..."`

### "Model not found"
- Make sure your API key is correct
- Make sure you have credits in your API account

### "Permission denied"
- Make sure your API key has the right permissions
- Try creating a new key in your API dashboard

---

**Ready to dive deeper?** Pick a use case guide above and start building!
