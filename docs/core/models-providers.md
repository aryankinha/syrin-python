---
title: Model Providers
description: Configuration details for every AI provider Syrin supports
weight: 11
---

## Every Provider, One Interface

Syrin speaks to all major AI providers through the same `Model` API. Swap providers by changing one line. Everything else — budget, memory, tools, hooks — stays the same.

## OpenAI

Strong ecosystem, reliable, well-documented. The default choice for most applications.

```python
import os
from syrin import Model

# Basic setup
model = Model.OpenAI("gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

# With tuning parameters
model = Model.OpenAI(
    "gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.3,     # 0 = deterministic, 1 = varied
    max_tokens=2000,     # Cap response length
)

# With a custom proxy or company endpoint
model = Model.OpenAI(
    "gpt-4o",
    api_key=os.getenv("OPENAI_API_KEY"),
    api_base="https://your-company-proxy.com/v1",
)
```

Common OpenAI model IDs: `"gpt-4o"`, `"gpt-4o-mini"`, `"gpt-4-turbo"`, `"gpt-3.5-turbo"`.

`gpt-4o-mini` is the best starting point for most applications — cheap, fast, capable, and 128k context.

## Anthropic (Claude)

Long context (200k tokens), strong reasoning, safety-focused. Good for complex analysis and long documents.

```python
import os
from syrin import Model

model = Model.Anthropic(
    "claude-sonnet-4-6-20251001",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
)

# Anthropic benefits from explicit max_tokens
model = Model.Anthropic(
    "claude-haiku-4-5-20251001",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    max_tokens=4096,
)
```

Common Claude model IDs:
- `"claude-opus-4-6"` — most capable, highest cost
- `"claude-sonnet-4-6-20251001"` — balanced capability and cost
- `"claude-haiku-4-5-20251001"` — fast and cheap

## Google (Gemini)

Very large context windows (up to 1M tokens), competitive pricing, native multimodal.

```python
import os
from syrin import Model

model = Model.Google("gemini-2.0-flash", api_key=os.getenv("GOOGLE_API_KEY"))

# Pro version for complex tasks
model = Model.Google("gemini-1.5-pro", api_key=os.getenv("GOOGLE_API_KEY"))
```

Common Gemini model IDs: `"gemini-2.0-flash"`, `"gemini-1.5-pro"`, `"gemini-1.5-flash"`.

`gemini-2.0-flash` is the fastest and cheapest option for high-volume, cost-sensitive applications. It has a free tier.

## Ollama (Local)

Run models on your own machine. Zero API costs, complete privacy, works offline.

```python
from syrin import Model

# Runs locally — no API key
model = Model.Ollama("llama3.2")
model = Model.Ollama("mistral")
model = Model.Ollama("codellama")

# Custom Ollama server address
model = Model.Ollama("llama3.2", api_base="http://your-server:11434")
```

Ollama must be running before you use these models. Install from ollama.ai, then pull a model with `ollama pull llama3.2`.

Models are downloaded automatically on first use. Sizes range from 2GB (Phi) to 70GB+ (Llama 3 70B). Make sure you have enough disk space.

## LiteLLM (100+ providers, one interface)

LiteLLM proxies requests to hundreds of models from dozens of providers. Use it when you need provider flexibility or your company standardizes on LiteLLM.

```python
from syrin import Model

# OpenAI via LiteLLM
model = Model.LiteLLM("openai/gpt-4o-mini", api_key="your-openai-key")

# Anthropic via LiteLLM
model = Model.LiteLLM("anthropic/claude-3-haiku-20240307", api_key="your-anthropic-key")

# Groq (fast inference)
model = Model.LiteLLM("groq/llama-3-8b-8192", api_key="your-groq-key")

# Cohere
model = Model.LiteLLM("cohere/command-r", api_key="your-cohere-key")
```

## Custom / OpenAI-Compatible APIs

Many providers (DeepSeek, Grok, Together AI, Moonshot, etc.) use OpenAI-compatible APIs. Use `Model.Custom()` with the provider's base URL:

```python
from syrin import Model

# DeepSeek
model = Model.Custom(
    "deepseek-chat",
    api_base="https://api.deepseek.com/v1",
    api_key="your-deepseek-key",
)

# Grok (xAI)
model = Model.Custom(
    "grok-3",
    api_base="https://api.x.ai/v1",
    api_key="your-xai-key",
)

# Moonshot (KIMI)
model = Model.Custom(
    "moonshot-v1-8k",
    api_base="https://api.moonshot.ai/v1",
    api_key="your-moonshot-key",
)
```

Any API that follows the OpenAI `/v1/chat/completions` format works with `Model.Custom()`.

## Switching Providers

The point of the `Model` abstraction is that your agent code doesn't change when you switch providers. Only the `model` line changes:

```python
from syrin import Agent, Model
import os

class MyAgent(Agent):
    # Change this one line to switch providers
    model = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
    # model = Model.Anthropic("claude-sonnet-4-6-20251001", api_key=os.getenv("ANTHROPIC_API_KEY"))
    # model = Model.Google("gemini-2.0-flash", api_key=os.getenv("GOOGLE_API_KEY"))
    # model = Model.Ollama("llama3.2")

    system_prompt = "You are a helpful assistant."
```

## Choosing a Provider

For **general-purpose chat and Q&A**: `gpt-4o-mini` or `gemini-2.0-flash`. Both are cheap, fast, and capable.

For **complex reasoning or long documents**: `gpt-4o` or `claude-sonnet-4-6-20251001`. Both handle nuanced tasks well.

For **code generation**: `gpt-4o` or `claude-sonnet-4-6-20251001`. Both perform well on code. `codellama` via Ollama is free and runs locally.

For **high-volume, cost-sensitive**: `gemini-2.0-flash` is very fast and has a free tier.

For **private or air-gapped deployments**: Ollama with a local model.

For **testing and development**: `Model.mock()` — no API key, no cost, always.

## What's Next

- [Models Overview](/agent-kit/core/models) — Model parameters, switching, and fallback
- [Custom Models](/agent-kit/core/models-custom) — Build a provider for any LLM
- [Model Routing](/agent-kit/core/models-routing) — Automatically route to different models
