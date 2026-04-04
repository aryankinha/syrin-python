---
title: Models
description: Every AI provider Syrin supports, how to configure them, and how to switch models at runtime
weight: 10
---

## The Brain of Your Agent

A model is the intelligence behind your agent. It receives your messages and generates responses. The model you choose determines the quality of responses, the speed of execution, and the cost of each call.

Syrin does not lock you in. You can use OpenAI, Anthropic, Google, Ollama, LiteLLM, or write your own provider — and switch between them with one line of code.

## The Mock Model (Start Here)

`Model.mock()` is a built-in mock that returns placeholder text. It costs nothing, needs no API key, and is perfect for testing everything — budget tracking, memory, hooks, the response object — without spending a cent.

```python
from syrin import Agent, Model

agent = Agent(
    model=Model.mock(),
    system_prompt="You are helpful.",
)
response = agent.run("Hello!")
print(f"Response: {response.content[:60]}")
print(f"Cost:     ${response.cost:.6f}")
print(f"Model:    {response.model}")
```

Output:

```
Response: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed
Cost:     $0.000040
Model:    almock/default
```

The mock simulates real model behavior including latency, token counting, and cost tracking. You can customize it for specific testing scenarios:

```python
# Control response latency for timing tests
fast_mock = Model.mock(latency_min=0.1, latency_max=0.3)

# Control the token count and cost tier
expensive_mock = Model.mock(pricing_tier="high")

# Set a specific response for deterministic tests
predictable_mock = Model.mock(custom_response="The answer is 42.")
```

## Real Model Providers

When you are ready for actual AI responses, pick your provider:

**OpenAI:**

```python
from syrin import Model
import os

model = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
# Or the larger model:
model = Model.OpenAI("gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
```

**Anthropic (Claude):**

```python
model = Model.Anthropic(
    "claude-3-haiku-20240307",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
)
# Or Claude Sonnet 4:
model = Model.Anthropic("claude-sonnet-4-6-20251001", api_key=os.getenv("ANTHROPIC_API_KEY"))
```

**Google (Gemini):**

```python
model = Model.Google("gemini-2.0-flash", api_key=os.getenv("GOOGLE_API_KEY"))
# Or the pro version:
model = Model.Google("gemini-1.5-pro", api_key=os.getenv("GOOGLE_API_KEY"))
```

**Ollama (local, no API key):**

```python
# Runs models on your machine — completely free, completely private
model = Model.Ollama("llama3.2")
model = Model.Ollama("mistral")
model = Model.Ollama("codellama")
```

Ollama must be running locally (`ollama serve`). Models are downloaded on first use.

**LiteLLM (100+ providers via one interface):**

```python
# Any model accessible via LiteLLM
model = Model.LiteLLM("openai/gpt-4o-mini")
model = Model.LiteLLM("anthropic/claude-3-haiku-20240307")
model = Model.LiteLLM("groq/llama-3-8b-8192")
```

## Model Parameters

Every model accepts common tuning parameters:

```python
model = Model.OpenAI(
    "gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.3,       # 0 = deterministic, 1 = more varied, 2 = very creative
    max_tokens=2000,       # Cap response length (in tokens)
    context_window=128000, # Match to what the model supports
)
```

**Temperature** is the most important parameter. At `0.0`, the model always picks the most likely next token — responses are focused and predictable. At `1.0` (the default), there is more variation. At `2.0`, responses are highly creative but may be incoherent. For factual agents, use `0.1`–`0.3`. For creative writing, use `0.7`–`1.0`.

**max_tokens** caps how long a response can be. Without it, the model may generate up to its context window. Useful for cost control on short-answer tasks.

## Switching Models at Runtime

You can change the model on a running agent without recreating it. All context, memory, and budget state is preserved:

```python
from syrin import Agent, Model

agent = Agent(model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"), system_prompt="You are helpful.")
# model = Model.mock()  # no API key needed for testing

print(f"Before: {agent.model_config.model_id}")
agent.run("First question")

# Switch to a different model
agent.switch_model(Model.OpenAI("gpt-4o-mini", api_key="your-api-key"))  # Or Model.mock() for testing
print(f"After: {agent.model_config.model_id}")
agent.run("Second question")  # Uses the new model
```

This is useful for budget-based model routing: run expensive requests with GPT-4o, switch to GPT-4o-mini when the budget gets low.

## Model Fallback

Configure an automatic fallback if the primary model fails:

```python
import os
from syrin import Model

primary = Model.OpenAI("gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
fallback = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))

model = primary.with_fallback(fallback)
# If gpt-4o times out or errors, automatically retries with gpt-4o-mini
```

## Choosing a Model

The right model depends on what you are building:

For **general-purpose chat and Q&A** with good cost efficiency: `gpt-4o-mini` or `gemini-2.0-flash`.

For **complex reasoning, long documents, or nuanced writing**: `gpt-4o` or `claude-sonnet-4-6-20251001`.

For **code generation**: `gpt-4o` or `claude-sonnet-4-6-20251001` perform well. `codellama` (via Ollama) is free and runs locally.

For **high-volume, cost-sensitive workloads**: `gemini-2.0-flash` is very fast and has a free tier.

For **private or air-gapped deployments**: Ollama with a local model.

For **testing and development**: `Model.mock()` — always.

## Custom Models

If your provider is not listed, inherit from `Model` and override `complete()`:

```python
from syrin import Model

class MyCustomModel(Model):
    def complete(self, messages, **kwargs):
        # Call your model API here
        response = my_api.generate(messages)
        return response.text

agent = Agent(model=MyCustomModel(), system_prompt="You are helpful.")
```

More on this in [Custom Models](/agent-kit/core/models-custom).

## What's Next

- [Model Providers](/agent-kit/core/models-providers) — Detailed configuration for every provider
- [Custom Models](/agent-kit/core/models-custom) — Inherit from Model to use any LLM
- [Model Routing](/agent-kit/core/models-routing) — Route to different models based on cost and task type
- [Budget](/agent-kit/core/budget) — Control spending across all model calls
