---
title: Installation
description: Get Syrin installed and your first agent running in under 2 minutes
weight: 2
---

## Two Minutes to Your First Agent

You need Python 3.10 or newer. That is the only hard requirement. You do not need an API key to get started — Syrin ships with a built-in mock model.

## Install

```bash
pip install syrin
```

Or with `uv` (faster):

```bash
uv add syrin
```

## Verify It Worked

```bash
python -c "import syrin; print(syrin.__version__)"
```

You should see:

```
0.11.0
```

## Run Your First Agent (No API Key Needed)

Create a file called `hello.py`:

```python
from syrin import Agent, Model

agent = Agent(
    model=Model.mock(),
    system_prompt="You are helpful.",
)
response = agent.run("Hello!")
print(response.content)
print(f"Syrin is working! Version: ", end="")
import syrin
print(syrin.__version__)
```

Run it:

```bash
python hello.py
```

You should see:

```
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore
Syrin is working! Version: 0.11.0
```

`Model.mock()` is a zero-cost mock that returns placeholder text. It lets you explore the full library — budget tracking, memory, hooks, the response object — without spending anything. When you want real answers, swap one line to a real model.

## Optional Extras

Syrin's core is lightweight. Install extras only when you need them:

```bash
# To serve your agent as an HTTP endpoint or chat UI
pip install "syrin[serve]"

# To process PDFs, Word documents, and other files
pip install "syrin[docling]"

# Everything at once
pip install "syrin[all]"
```

What each extra adds:

- **`serve`** — FastAPI and uvicorn, needed for `agent.serve()` and the playground UI
- **`docling`** — Document loaders for PDFs, Word docs, spreadsheets, and web pages
- **`all`** — Both extras plus any other optional dependencies

## Set Up API Keys (When You Need Real Models)

For production agents powered by real LLMs, set your API key as an environment variable:

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic (Claude)
export ANTHROPIC_API_KEY="sk-ant-..."

# Google (Gemini)
export GOOGLE_API_KEY="AIza..."
```

Then pass it to the model:

```python
from syrin import Agent, Model
import os

class MyAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
    system_prompt = "You are helpful."
```

Or use a `.env` file in your project root:

```bash
# .env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

Then load it at startup:

```python
from dotenv import load_dotenv
load_dotenv()
```

Install `python-dotenv` with `pip install python-dotenv`.

## Common Installation Errors

**`ModuleNotFoundError: No module named 'syrin'`**

You are not in the right virtual environment, or Syrin is not installed there.

```bash
pip install syrin
python -c "import syrin; print('OK')"
```

**`ImportError: cannot import name 'Agent'`**

Your Syrin version is older than 0.11.0. Update it:

```bash
pip install --upgrade syrin
```

**`ModuleNotFoundError: No module named 'fastapi'`** when calling `agent.serve()`

Install the serve extra:

```bash
pip install "syrin[serve]"
```

**API key errors when using a real model**

Check that your environment variable is actually set:

```python
import os
print(os.getenv("OPENAI_API_KEY"))  # Should print your key, not None
```

## What's Next

You have Syrin installed and confirmed working. Now build your first real agent:

- [Quick Start](/agent-kit/quick-start) — Build a full agent with budget, memory, and tasks in 10 minutes
- [Core Concepts](/agent-kit/concepts) — Understand how Syrin thinks before you build
- [Models](/agent-kit/core/models) — All supported AI providers and how to configure them
