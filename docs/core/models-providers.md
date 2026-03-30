---
title: Providers
description: A complete guide to all AI model providers supported by Syrin
weight: 11
---

## Your AI Brains, One Place (No More Juggling Libraries)

Syrin speaks to all major AI providers out of the box. OpenAI, Anthropic, Google, Ollama—pick the one that fits your needs, and Syrin handles the rest.

Let's meet each provider.

---

## OpenAI

**Best for:** General purpose, fast iteration, best ecosystem

OpenAI's GPT models are the industry standard. They're reliable, well-documented, and have the best tooling support.

### Quick Setup

```python
from syrin import Model

model = Model.OpenAI(
    "gpt-4o",
    api_key="your-api-key"
)
```

### Available Models

| Model | Best For | Context | Notes |
|-------|----------|---------|-------|
| **GPT-4o** | Complex reasoning, best overall | 128k | Flagship, most capable |
| **GPT-4o-mini** | Fast, cost-effective | 128k | Great value |
| **GPT-4 Turbo** | Complex tasks | 128k | Strong reasoning |
| **GPT-3.5 Turbo** | High volume, simple tasks | 16k | Cheapest option |

### Pro Tips

```python
# Use environment variable for security
import os
model = Model.OpenAI("gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

# Use a proxy or custom endpoint
model = Model.OpenAI(
    "gpt-4o",
    api_base="https://your-proxy.com/v1",  # For company proxies
    api_key=os.getenv("OPENAI_API_KEY")
)
```

### When to Use OpenAI

- Building production apps that need reliability
- When you need the best tooling ecosystem
- Fast iteration and prototyping
- When cost is not the primary concern

---

## Anthropic

**Best for:** Complex reasoning, safety-focused applications, long context

Anthropic's Claude models excel at nuanced tasks and have a strong focus on safety and helpfulness.

### Quick Setup

```python
from syrin import Model

model = Model.Anthropic(
    "claude-sonnet-4-5",
    api_key="your-api-key"
)
```

### Available Models

| Model | Best For | Context | Notes |
|-------|----------|---------|-------|
| **Claude Opus 4** | Complex reasoning, analysis | 200k | Most capable |
| **Claude Sonnet 4** | Balanced, everyday tasks | 200k | Great value |
| **Claude 3.5 Haiku** | Fast, simple tasks | 200k | Quick responses |

### Pro Tips

```python
# Set max output tokens (required by Anthropic)
model = Model.Anthropic(
    "claude-sonnet-4-5",
    api_key="your-api-key",
    max_tokens=4096  # Anthropic requires this
)

# Environment variable
import os
model = Model.Anthropic(
    "claude-sonnet-4-5",
    api_key=os.getenv("ANTHROPIC_API_KEY")
)
```

### When to Use Anthropic

- When safety and helpfulness are priorities
- Long documents (200k context!)
- Complex reasoning and analysis
- When OpenAI's output isn't cutting it

---

## Google (Gemini)

**Best for:** Cost-effective, multimodal, Google's ecosystem

Google's Gemini models offer great value and native multimodal capabilities.

### Quick Setup

```python
from syrin import Model

model = Model.Google(
    "gemini-2.0-flash",
    api_key="your-api-key"
)
```

### Available Models

| Model | Best For | Context | Notes |
|-------|----------|---------|-------|
| **Gemini 2.0 Flash** | Fast, cost-effective | 1M | Amazing value! |
| **Gemini 1.5 Pro** | Complex reasoning | 1M | Long context, capable |
| **Gemini 1.5 Flash** | Balance of speed/cost | 1M | Great everyday model |

### Pro Tips

```python
# Gemini 2.0 Flash is incredibly cheap
model = Model.Google(
    "gemini-2.0-flash",
    api_key=os.getenv("GOOGLE_API_KEY")
)
```

### When to Use Google

- Cost-sensitive applications
- Need the cheapest option possible
- Multimodal inputs (images, video)
- Google's ecosystem integration

---

## Ollama (Local)

**Best for:** Privacy, offline, no API costs

Run AI models locally on your machine. Zero API costs, complete privacy, runs offline.

### Quick Setup

```bash
# Install Ollama first: https://ollama.ai
# Then pull a model:
ollama pull llama3
ollama pull mistral
```

```python
from syrin import Model

# No API key needed - runs locally!
model = Model.Ollama("llama3")

# Or specify the server
model = Model.Ollama(
    "llama3",
    api_base="http://localhost:11434"  # Default
)
```

### Available Models

| Model | Best For | Size | Notes |
|-------|----------|------|-------|
| **Llama 3** | General purpose | 8B-70B | Meta's open model |
| **Mistral** | Fast, efficient | 7B | Great performance |
| **CodeLlama** | Code generation | 7B-34B | Specialized for code |
| **Phi** | Small, fast | 2.7B | Minimal resources |

### Pro Tips

```python
# Start Ollama server (runs in background)
# Then connect:

model = Model.Ollama(
    "llama3",
    temperature=0.7,  # Adjust like any other model
    max_tokens=2048
)
```

### When to Use Ollama

- Privacy-sensitive applications
- No API costs (your electricity is the cost)
- Development and testing
- Offline deployments

---

## LiteLLM

**Best for:** Multiple providers, unified API, 100+ models

LiteLLM provides a unified API across 100+ models from different providers. Switch providers without changing code.

### Quick Setup

```python
from syrin import Model

# OpenAI via LiteLLM
model = Model.LiteLLM(
    "openai/gpt-4o",
    api_key="your-openai-key"
)

# Anthropic via LiteLLM
model = Model.LiteLLM(
    "anthropic/claude-3-5-sonnet",
    api_key="your-anthropic-key"
)
```

### When to Use LiteLLM

- Need to switch between providers
- Using multiple providers in one app
- When your company standardizes on LiteLLM

---

## Custom Providers (OpenAI-Compatible)

**Best for:** DeepSeek, KIMI, Grok, and other OpenAI-compatible APIs

Many AI providers use OpenAI-compatible APIs. Syrin supports them all.

### Quick Setup

```python
from syrin import Model

# DeepSeek
model = Model.Custom(
    "deepseek-chat",
    api_base="https://api.deepseek.com/v1",
    api_key="your-deepseek-key"
)

# Grok (xAI)
model = Model.Custom(
    "grok-3",
    api_base="https://api.x.ai/v1",
    api_key="your-xai-key"
)

# KIMI (Moonshot)
model = Model.Custom(
    "moonshot-v1-8k",
    api_base="https://api.moonshot.ai/v1",
    api_key="your-moonshot-key"
)
```

### Common Custom Providers

| Provider | API Base | Notes |
|----------|---------|-------|
| DeepSeek | `https://api.deepseek.com/v1` | Great value, strong reasoning |
| Grok | `https://api.x.ai/v1` | xAI's offering |
| KIMI | `https://api.moonshot.ai/v1` | China's Moonshot AI |
| Together AI | `https://api.together.ai/v1` | Hosting many open models |

---

## Provider Comparison

| Provider | Best For | Cost | Context | Multimodal | Local? |
|----------|---------|------|---------|------------|--------|
| **OpenAI** | Reliability, ecosystem | $$ | 128k | Yes | No |
| **Anthropic** | Safety, reasoning | $$$ | 200k | Yes | No |
| **Google** | Cost, multimodal | $ | 1M | Yes | No |
| **Ollama** | Privacy, no costs | Free | Varies | No | Yes |
| **LiteLLM** | Multi-provider | $$ | Varies | Varies | No |

**Cost scale:** $ = cheap, $$ = moderate, $$$ = expensive

---

## Which Provider Should You Choose?

### Choose OpenAI when:
- Building production apps
- Need best tooling support
- Cost is not primary concern

### Choose Anthropic when:
- Safety is critical
- Need long context (200k)
- Complex reasoning tasks

### Choose Google when:
- Cost is the primary concern
- Need native multimodal
- High volume applications

### Choose Ollama when:
- Privacy matters
- No API costs desired
- Offline deployment needed

### Choose LiteLLM when:
- Using multiple providers
- Need provider flexibility
- Standardized API required

---

## Switching Providers

The beauty of Syrin? Switch providers without rewriting your agent:

```python
# Same agent code, different brain
class MyAgent(Agent):
    # Just change this one line
    model = Model.OpenAI("gpt-4o", api_key="...")
    # model = Model.Anthropic("claude-sonnet", api_key="...")
    # model = Model.Google("gemini-2.0-flash", api_key="...")
    # model = Model.Ollama("llama3")  # No API key needed!
    
    system_prompt = "You are a helpful assistant."

agent = MyAgent()
```

---

## What's Next?

- [Models Overview](/agent-kit/core/models) - Recap of models and settings
- [Custom Models](/agent-kit/core/models-custom) - Create your own provider
- [Model Routing](/agent-kit/core/models-routing) - Automatically switch models

## See Also

- [Budget](/agent-kit/core/budget) - Control your spending per provider
- [Context](/agent-kit/core/context) - Handle large contexts
- [Memory](/agent-kit/core/memory) - Make agents remember
