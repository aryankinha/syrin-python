---
title: Model Routing
description: Automatically select the best model for each request
weight: 13
---

## Why Use One Model When You Can Use the Right One?

Here's the hidden cost of a single-model setup: you're either overpaying for simple questions or underperforming on hard ones. "Hello, how are you?" doesn't need GPT-4o. A complex debugging session doesn't need GPT-4o-mini.

Model routing lets your agent automatically pick the right model for each request — cheap and fast for simple tasks, powerful for complex ones.

## Basic Setup

Define multiple models with their strengths, and let the router decide:

```python
from syrin import Agent
from syrin.model import Model
from syrin.router import RoutingConfig, RoutingMode, TaskType

agent = Agent(
    model=[
        Model.Anthropic(
            "claude-sonnet-4-6-20251001",
            api_key="your-key",
            profile_name="code",
            strengths=[TaskType.CODE, TaskType.REASONING],
        ),
        Model.OpenAI(
            "gpt-4o-mini",
            api_key="your-key",
            profile_name="general",
            strengths=[TaskType.GENERAL],
        ),
    ],
    model_router=RoutingConfig(routing_mode=RoutingMode.AUTO),
)

r = agent.run("Hello! How are you?")
print(r.model_used)  # "gpt-4o-mini" — simple task

r = agent.run("Write a function to sort a list")
print(r.model_used)  # "claude-sonnet-4-6-20251001" — code task
```

The router detects the task type from the prompt and picks the model whose `strengths` match.

## Task Types

The router classifies every prompt into one of these task types:

`TaskType.GENERAL` — Simple conversations and factual questions: "Hi", "What's the weather?"

`TaskType.CODE` — Code generation, debugging, and explanation: "Write a function", "Fix this bug"

`TaskType.REASONING` — Logic, math, and analysis: "Solve this equation", "Analyze this dataset"

`TaskType.CREATIVE` — Writing, brainstorming, storytelling: "Write a story", "Brainstorm ideas"

`TaskType.VISION` — Image understanding (requires a vision-capable model)

`TaskType.PLANNING` — Task decomposition: "How do I build this system?"

`TaskType.TRANSLATION` — Language conversion: "Translate to Spanish"

## Routing Modes

Three modes control how the router selects from capable models.

`RoutingMode.AUTO` (default) — Balances cost and capability. Picks the cheapest model that can handle the task. Good for most applications.

`RoutingMode.COST_FIRST` — Always picks the cheapest capable model, even if a better one is available. Use this for high-volume, cost-sensitive apps.

`RoutingMode.QUALITY_FIRST` — Always picks the highest-priority capable model. Use this when quality is the only thing that matters.

## Budget-Aware Routing

When your budget is running low, routing can automatically fall back to cheaper models:

```python
from syrin import Agent, Budget
from syrin.model import Model
from syrin.router import RoutingConfig, RoutingMode

agent = Agent(
    model=[
        Model.OpenAI("gpt-4o", api_key="key", profile_name="premium"),
        Model.OpenAI("gpt-4o-mini", api_key="key", profile_name="budget"),
    ],
    model_router=RoutingConfig(
        routing_mode=RoutingMode.AUTO,
        budget_optimisation=True,
        prefer_cheaper_below_budget_ratio=0.20,  # Prefer cheap when 20% budget left
        force_cheapest_below_budget_ratio=0.10,  # Force cheap when 10% left
    ),
    budget=Budget(max_cost=1.00),
)
```

With more than 20% budget remaining, routing works normally. Between 10% and 20%, the router prefers cheaper models. Below 10%, it forces the cheapest capable model regardless of task type.

## Vision Routing

When a user sends an image, the router needs a vision-capable model:

```python
from syrin.enums import Media
from syrin.model import Model
from syrin.router import RoutingConfig, RoutingMode, TaskType

agent = Agent(
    model=[
        Model.OpenAI(
            "gpt-4o-mini",
            api_key="key",
            strengths=[TaskType.GENERAL],
            input_media={Media.TEXT},  # Text only
        ),
        Model.OpenAI(
            "gpt-4o",
            api_key="key",
            strengths=[TaskType.VISION, TaskType.GENERAL],
            input_media={Media.TEXT, Media.IMAGE},  # Supports images
        ),
    ],
    model_router=RoutingConfig(routing_mode=RoutingMode.AUTO),
)
```

When the user sends a message with an image, the router detects the image and routes to a model with `Media.IMAGE` in its `input_media` set.

## Manual Task Override

When the router gets it wrong, override the task type:

```python
# "Fix this" — ambiguous, could be general or code
# Tell the router explicitly
r = agent.run("Fix this syntax error", task_type=TaskType.CODE)
```

Use this for debugging routing decisions or when the prompt is genuinely ambiguous.

## Custom Routing Logic

Add custom rules with a callback:

```python
from syrin.router import RoutingConfig, TaskType

def my_routing(prompt: str, task_type: TaskType, profile_names: list[str]) -> str | None:
    # VIP requests always get the premium model
    if "VIP" in prompt:
        return "premium"

    # Return None to let the default routing proceed
    return None

agent = Agent(
    model=[...],
    model_router=RoutingConfig(routing_rule_callback=my_routing),
)
```

Returning a profile name selects that specific model. Returning `None` falls through to the default routing logic.

## Checking the Routing Decision

Every routed response explains why it chose a specific model:

```python
r = agent.run("Write a sorting function")

print(r.routing_reason.selected_model)           # "code"
print(r.routing_reason.task_type)                # TaskType.CODE
print(r.routing_reason.reason)                   # "Matched CODE, highest priority capable"
print(r.routing_reason.cost_estimate)            # 0.0034
print(r.routing_reason.classification_confidence) # 0.89
```

## Force a Specific Model

Bypass routing entirely for debugging or special cases:

```python
from syrin.model import Model
from syrin.router import RoutingConfig

agent = Agent(
    model=[...],
    model_router=RoutingConfig(
        force_model=Model.Anthropic("claude-opus-4-6", api_key="key"),
    ),
)
```

All requests go to the forced model, routing logic ignored.

## OpenRouter: Many Providers, One Key

OpenRouter proxies to OpenAI, Anthropic, Google, and more with a single API key:

```python
from syrin.model import Model, OpenRouterBuilder
from syrin.router import RoutingConfig, RoutingMode

builder = OpenRouterBuilder(api_key="your-openrouter-key")

claude = builder.model("anthropic/claude-sonnet-4-6-20251001")
gpt = builder.model("openai/gpt-4o-mini")
gemini = builder.model("google/gemini-2.0-flash")

agent = Agent(
    model=[claude, gpt, gemini],
    model_router=RoutingConfig(routing_mode=RoutingMode.AUTO),
)
```

## Complete Example

```python
from syrin import Agent, Budget
from syrin.enums import Media
from syrin.model import Model
from syrin.router import RoutingConfig, RoutingMode, TaskType

class SmartAgent(Agent):
    model = [
        Model.Anthropic(
            "claude-opus-4-6",
            api_key="your-key",
            profile_name="premium",
            strengths=[TaskType.CODE, TaskType.REASONING, TaskType.PLANNING],
            priority=100,
        ),
        Model.OpenAI(
            "gpt-4o-mini",
            api_key="your-key",
            profile_name="general",
            strengths=[TaskType.GENERAL, TaskType.CREATIVE],
            input_media={Media.TEXT, Media.IMAGE},
            priority=80,
        ),
    ]

    model_router = RoutingConfig(
        routing_mode=RoutingMode.AUTO,
        budget_optimisation=True,
        prefer_cheaper_below_budget_ratio=0.20,
        force_cheapest_below_budget_ratio=0.10,
    )

    budget = Budget(max_cost=10.00)
    system_prompt = "You are a helpful AI assistant."

agent = SmartAgent()

r = agent.run("Hello!")
print(f"Model: {r.model_used}")  # gpt-4o-mini (GENERAL task)

r = agent.run("Write a quicksort implementation in Python")
print(f"Model: {r.model_used}")  # claude-opus-4-6 (CODE task)
```

## What's Next?

- [Model Providers](/core/models-providers) — All supported providers
- [Custom Models](/core/models-custom) — Add your own provider
- [Budget](/core/budget) — Control spending across routing decisions
