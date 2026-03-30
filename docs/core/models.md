---
title: Models
description: Choose and configure AI models for your agents
weight: 10
---

## The Brain of Your Agent (And Why It Matters)

Think of an AI model as the **brain** of your agent.

Just like a human brain decides how to think and respond, the model decides how your agent thinks, reasons, and answers. Choose a smart brain for complex tasks, a fast brain for simple ones, or a cheap brain when you're watching your budget.

The better the model, the better your agent's responses—but smart comes with a price tag.

## What Is a Model in Syrin?

In Syrin, a **Model** is your gateway to AI. It's the component that:

- Takes your messages and system prompt
- Thinks (using the AI's reasoning)
- Returns text, tool calls, or structured data

Syrin doesn't lock you into one provider. Use OpenAI, Anthropic, Google, or even run models locally. Switch models with one line of code.

## Your First Model

Here's the simplest way to use a model:

```python
from syrin import Agent, Model

class MyAgent(Agent):
    # One line to set your AI brain
    model = Model.OpenAI("gpt-4o", api_key="your-key")
    
    system_prompt = "You are a helpful assistant."

agent = MyAgent()
response = agent.run("Hello!")
print(response.content)
```

**That's it.** No complex setup, no vendor lock-in.

## Quick Example: Comparing Models

Want to try different brains? Just change the model:

```python
# GPT-4o - The powerhouse (expensive but smart)
gpt4 = Model.OpenAI("gpt-4o", api_key="your-key")

# GPT-4o-mini - The efficient one (cheaper, still smart)
gpt_mini = Model.OpenAI("gpt-4o-mini", api_key="your-key")

# Claude - Anthropic's brain
claude = Model.Anthropic("claude-sonnet-4-5", api_key="your-key")

# Gemini - Google's brain
gemini = Model.Google("gemini-2.0-flash", api_key="your-key")
```

Same agent, different brains:

```python
class MyAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")  # Change here
    system_prompt = "You are a helpful assistant."

agent = MyAgent()
```

## Model Settings (The Knobs You Can Turn)

Every model has settings you can tweak. Here's what each one does:

| Setting | What It Does | Default | When to Tweak |
|--------|-------------|---------|---------------|
| `temperature` | Controls randomness | `1.0` | Lower = focused, Higher = creative |
| `max_tokens` | Max response length | `None` (provider default) | When you need strict length limits |
| `top_p` | Nucleus sampling | `None` | Rarely needed, leave default |
| `top_k` | Top-k sampling | `None` | Rarely needed, leave default |
| `stop` | Stop sequences | `None` | When you want early stopping |
| `context_window` | Max input + output | Provider default | Match to your needs |

### Understanding Temperature

The most important setting. Think of it as "how wild is this AI's imagination?"

| Temperature | Effect | Best For |
|------------|--------|----------|
| **0.0 - 0.3** | Focused, deterministic, reliable | Code, facts, instructions |
| **0.4 - 0.7** | Balanced, natural | General conversation |
| **0.8 - 1.5** | Creative, surprising, varied | Brainstorming, stories |
| **1.6+** | Very random, chaotic | Experimental, rarely needed |

**Examples:**

```python
# Focused and reliable (good for coding)
model = Model.OpenAI("gpt-4o", api_key="your-key", temperature=0.3)

# Creative and varied (good for brainstorming)
model = Model.OpenAI("gpt-4o", api_key="your-key", temperature=0.9)

# Balanced (default behavior)
model = Model.OpenAI("gpt-4o", api_key="your-key", temperature=0.7)
```

### Understanding Max Tokens

Controls how long the response can be.

```python
# Short, concise responses (max 100 tokens)
model = Model.OpenAI("gpt-4o", api_key="your-key", max_tokens=100)

# Longer responses (max 4000 tokens)
model = Model.OpenAI("gpt-4o", api_key="your-key", max_tokens=4000)
```

**Tip:** If you need exactly 500 tokens, set `max_tokens=500`. The model will stop at 500 tokens even if it has more to say.

---

## Complete Model Configuration

Here's a fully configured model:

```python
from syrin import Model

model = Model.OpenAI(
    "gpt-4o",
    api_key="your-key",
    temperature=0.7,           # Balanced creativity
    max_tokens=2000,           # Cap response at 2000 tokens
    context_window=128000,     # Support up to 128k context
    top_p=None,                # Use default
    stop=None,                # No early stopping
)
```

## Testing with Almock

No API key? No problem. Use `Almock` for testing:

```python
from syrin import Model

# Almock returns lorem ipsum - perfect for testing
model = Model.Almock()

# Customize for different testing scenarios
fast_mock = Model.Almock(latency_min=0.1, latency_max=0.3)
expensive_mock = Model.Almock(pricing_tier="high")  # For budget testing
```

---

## Model vs Provider

You might see these terms. Here's the difference:

| Term | What It Means |
|------|--------------|
| **Model** | The AI brain (GPT-4, Claude, Gemini) |
| **Provider** | The company/service hosting the AI (OpenAI, Anthropic, Google) |
| **API Key** | Your access credential for the provider |

Syrin abstracts the provider so you can switch models easily:

```python
# All these use the same agent code, just different brains
agent1 = MyAgent(model=Model.OpenAI("gpt-4o", api_key="..."))
agent2 = MyAgent(model=Model.Anthropic("claude-sonnet", api_key="..."))
agent3 = MyAgent(model=Model.Google("gemini-2.0-flash", api_key="..."))
```

## Pricing Reference

Different models have different costs. Here's a quick reference:

### OpenAI

| Model | Input ($/1M tokens) | Output ($/1M tokens) |
|-------|---------------------|----------------------|
| GPT-4o | $5.00 | $15.00 |
| GPT-4o-mini | $0.15 | $0.60 |
| GPT-4 Turbo | $10.00 | $30.00 |
| GPT-3.5 Turbo | $0.50 | $1.50 |

### Anthropic

| Model | Input ($/1M tokens) | Output ($/1M tokens) |
|-------|---------------------|----------------------|
| Claude Opus 4 | $15.00 | $75.00 |
| Claude Sonnet 4 | $3.00 | $15.00 |
| Claude 3.5 Haiku | $1.00 | $5.00 |

### Google

| Model | Input ($/1M tokens) | Output ($/1M tokens) |
|-------|---------------------|----------------------|
| Gemini 2.0 Flash | $0.00 | $0.00 |
| Gemini 1.5 Pro | $1.25 | $5.00 |
| Gemini 1.5 Flash | $0.075 | $0.30 |

**Tip:** Syrin automatically tracks these costs. Set a [Budget](/agent-kit/core/budget) to control spending.

## Which Model Should You Use?

Here's a quick decision guide:

| Need | Recommended Model |
|------|------------------|
| General chat, fast responses | GPT-4o-mini |
| Complex reasoning, long context | GPT-4o or Claude Opus |
| Code generation | GPT-4o or Claude Sonnet |
| Cost-sensitive, high volume | GPT-3.5 Turbo or Gemini 1.5 Flash |
| Creative writing, brainstorming | Claude Sonnet or GPT-4o |
| Local/private deployment | Ollama (local models) |

## Public Cost Helpers

The public cost package also exposes reusable pricing tables and calculators:

- `EMBEDDING_PRICING`, `IMAGE_PRICING`, `VIDEO_PRICING`, and `VOICE_PRICING` for modality-specific pricing maps.
- `calculate_cost()` and `estimate_cost_for_call()` for general model cost estimation.
- `calculate_embedding_cost()`, `calculate_image_cost()`, `calculate_video_cost()`, and `calculate_voice_cost()` for modality-specific cost calculations.

## What's Next?

- [Providers](/agent-kit/core/models-providers) - Detailed guide for each provider
- [Custom Models](/agent-kit/core/models-custom) - Create your own model
- [Model Routing](/agent-kit/core/models-routing) - Automatically switch models based on task
- [Budget](/agent-kit/core/budget) - Control your AI spending

## See Also

- [Tools](/agent-kit/agent/tools) - Give your agent abilities
- [Prompts](/agent-kit/core/prompts) - Instruct your agent effectively
- [Memory](/agent-kit/core/memory) - Make your agent remember
