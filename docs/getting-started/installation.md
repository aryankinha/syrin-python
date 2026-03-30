---
title: Installation
description: Set up Syrin and your first AI agent in minutes
weight: 2
---

## Get Up and Running in 5 Minutes (Without Pulling Your Hair Out)

Get Syrin installed and ready to use in under 5 minutes.

## Prerequisites

- **Python 3.10+** - Syrin requires Python 3.10 or higher
- **API Keys** (optional) - For production use with real AI models

## Install via pip

```bash
pip install syrin
```

## Optional Extras

Install additional dependencies based on your needs:

```bash
# For serving agents via HTTP/CLI
pip install syrin[serve]

# For document processing (PDF, Word, etc.)
pip install syrin[docling]

# For all optional dependencies
pip install syrin[all]
```

| Extra | Dependencies | When to Use |
|-------|-------------|-------------|
| `serve` | FastAPI, uvicorn | Deploying agents as HTTP API |
| `docling` | Document loaders | Processing PDFs, Word docs |
| `all` | All optional dependencies | Full feature set |

## Verify Installation

Run this to confirm Syrin is installed correctly:

```python
import syrin

print(syrin.__version__)  # Should print the version
```

Or from command line:

```bash
python -c "import syrin; print(syrin.__version__)"
```

## Set Up API Keys

For production use with real AI models, set your API keys as environment variables:

```bash
# OpenAI
export OPENAI_API_KEY="your-openai-key"

# Anthropic
export ANTHROPIC_API_KEY="your-anthropic-key"

# Google (Gemini)
export GOOGLE_API_KEY="your-google-key"
```

Or add them to a `.env` file in your project:

```bash
# .env
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
GOOGLE_API_KEY=your-google-key
```

Then load it in your code:

```python
from dotenv import load_dotenv

load_dotenv()  # Loads .env file
```

## Quick Test: Run Your First Agent

Create a file `test_agent.py`:

```python
from syrin import Agent, Model

class MyAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-api-key-here")
    # No API key? Use: model = Model.Almock()
    system_prompt = "You are helpful."

agent = MyAgent()
response = agent.run("Hello!")
print(response.content)
```

Run it:

```bash
python test_agent.py
```

You should see a response printed. If you get an error, see [Troubleshooting](/agent-kit/getting-started/troubleshooting).

## Common Installation Errors

### `ModuleNotFoundError: No module named 'syrin'`

**Solution:** Run `pip install syrin` in your virtual environment.

### `ImportError: cannot import name 'Agent'`

**Solution:** Ensure you have the latest version: `pip install --upgrade syrin`.

### `uvicorn not found` when using `agent.serve()`

**Solution:** Install the serve extra: `pip install syrin[serve]`.

### API key errors

**Solution:** Verify your environment variables are set correctly. Try:
```python
import os
print(os.getenv("OPENAI_API_KEY"))  # Should print your key
```

## What's Next?

- [Quick Start](/agent-kit/getting-started/quick-start) - Build your first working agent in 5 minutes
- [Understanding Agents](/agent-kit/agent/overview) - Learn how agents work
- [Models](/agent-kit/core/models) - Configure AI models

## See Also

- [Troubleshooting](/agent-kit/getting-started/troubleshooting) - Common errors and fixes
- [Models: Providers](/agent-kit/core/models-providers) - All supported AI providers
