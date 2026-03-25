---
title: Model Routing
description: Automatically select the best model for each request
weight: 13
---

## Why Use One Model When You Can Use the Right Model?

Here's the problem with using a single model for everything:

- **Simple question?** Still paying GPT-4o prices
- **Complex code?** GPT-3.5 Turbo isn't cutting it
- **Budget running low?** No way to automatically switch to cheaper options

What if your agent could automatically choose the right brain for each task?

That's what model routing does.

---

## The Problem: One Size Doesn't Fit All

Think about it this way:

| Task | Best Model | Why |
|------|-----------|-----|
| "Hello, how are you?" | GPT-4o-mini | Simple task, no reasoning needed |
| "Write a quicksort function" | Claude Sonnet | Code generation is its specialty |
| "Explain quantum entanglement" | GPT-4o | Complex reasoning, need the best |
| "What's 2+2?" | GPT-3.5 Turbo | Barely needs a brain |

Using one model means either:
- **Overpaying** for simple tasks (GPT-4o for "Hi")
- **Underperforming** on complex tasks (GPT-3.5 for complex code)

**Model routing solves this.**

---

## The Solution: Route by Task

With routing, you define your models and their strengths:

```python
from syrin import Agent
from syrin.model import Model
from syrin.router import RoutingConfig, RoutingMode, TaskType

# Define your models with their strengths
agent = Agent(
    model=[
        # Claude is great at code and reasoning
        Model.Anthropic(
            "claude-sonnet-4-5",
            api_key="your-key",
            profile_name="code",
            strengths=[TaskType.CODE, TaskType.REASONING],
        ),
        # GPT-4o-mini is fast and cheap for general tasks
        Model.OpenAI(
            "gpt-4o-mini",
            api_key="your-key",
            profile_name="general",
            strengths=[TaskType.GENERAL],
        ),
    ],
    model_router=RoutingConfig(routing_mode=RoutingMode.AUTO),
)
```

**Now watch it work:**

```python
# This gets routed to GPT-4o-mini (GENERAL task)
r = agent.run("Hello! How are you?")
print(r.model_used)  # "gpt-4o-mini"

# This gets routed to Claude (CODE task)
r = agent.run("Write a function to sort a list")
print(r.model_used)  # "claude-sonnet-4-5"
```

The router automatically detects the task type and picks the right model.

---

## Understanding Task Types

Syrin routes based on these task types:

| Task Type | What It Matches | Example Prompts |
|-----------|----------------|-----------------|
| `GENERAL` | Simple conversations | "Hi", "What's the weather?" |
| `CODE` | Code generation, debugging | "Write a function", "Fix this bug" |
| `REASONING` | Logic, math, analysis | "Solve this equation", "Analyze this" |
| `CREATIVE` | Writing, brainstorming | "Write a story", "Brainstorm ideas" |
| `VISION` | Image understanding | "What's in this image?" |
| `PLANNING` | Task decomposition | "How do I build this?" |
| `TRANSLATION` | Language conversion | "Translate to Spanish" |

---

## Routing Modes

How does the router decide? It depends on the mode:

### AUTO Mode (Default)

Balances cost and capability. Uses the cheapest *capable* model.

```python
agent = Agent(
    model=[...],
    model_router=RoutingConfig(routing_mode=RoutingMode.AUTO),
)
```

**When to use:** Most cases. Good balance of cost and quality.

### COST_FIRST Mode

Always picks the cheapest capable model, regardless of quality differences.

```python
agent = Agent(
    model=[...],
    model_router=RoutingConfig(routing_mode=RoutingMode.COST_FIRST),
)
```

**When to use:** Strict budget, high volume, cost-sensitive applications.

### QUALITY_FIRST Mode

Always picks the highest-priority capable model.

```python
agent = Agent(
    model=[...],
    model_router=RoutingConfig(routing_mode=RoutingMode.QUALITY_FIRST),
)
```

**When to use:** Quality is critical, budget is not a concern.

---

## A Real Example: Customer Support Agent

Let's build a customer support agent that routes intelligently:

```python
from syrin import Agent, Budget
from syrin.model import Model
from syrin.router import RoutingConfig, RoutingMode, TaskType

class SupportAgent(Agent):
    model = [
        # Fast and cheap for simple questions
        Model.OpenAI(
            "gpt-4o-mini",
            api_key="your-key",
            profile_name="simple",
            strengths=[TaskType.GENERAL],
            priority=80,
        ),
        # Powerful for complex issues
        Model.OpenAI(
            "gpt-4o",
            api_key="your-key",
            profile_name="complex",
            strengths=[TaskType.REASONING, TaskType.CODE],
            priority=100,
        ),
    ]
    
    model_router = RoutingConfig(
        routing_mode=RoutingMode.AUTO,
        budget=Budget(max_cost=5.00),  # Stop at $5
    )
    
    system_prompt = "You are a helpful customer support agent."

agent = SupportAgent()

# Simple question → GPT-4o-mini (fast, cheap)
r = agent.run("Where's my order?")
print(f"Model: {r.model_used}, Cost: ${r.cost:.4f}")
# Output: Model: gpt-4o-mini, Cost: $0.0012

# Complex issue → GPT-4o (capable)
r = agent.run("My code isn't working and I need to debug a complex algorithm")
print(f"Model: {r.model_used}, Cost: ${r.cost:.4f}")
# Output: Model: gpt-4o, Cost: $0.0234
```

**Result:** Simple questions cost fractions of a cent. Complex issues get the best model.

---

## Budget-Aware Routing

Here's where it gets smart. When your budget runs low, routing can automatically prefer cheaper models:

```python
agent = Agent(
    model=[
        Model.OpenAI("gpt-4o", api_key="key", profile_name="premium"),
        Model.OpenAI("gpt-4o-mini", api_key="key", profile_name="budget"),
    ],
    model_router=RoutingConfig(
        routing_mode=RoutingMode.AUTO,
        budget_optimisation=True,
        prefer_cheaper_below_budget_ratio=0.20,  # When 20% budget left, prefer cheap
        force_cheapest_below_budget_ratio=0.10,  # When 10% budget left, force cheap
    ),
    budget=Budget(max_cost=1.00),  # $1 budget
)
```

| Budget Remaining | Behavior |
|-----------------|----------|
| > 20% | Normal routing (best capable) |
| 10-20% | Prefer cheaper models |
| < 10% | Force cheapest capable model |

---

## Vision Routing

When a user sends an image, route to a vision-capable model:

```python
from syrin.enums import Media
from syrin.router import RoutingConfig, TaskType

agent = Agent(
    model=[
        # Text-only model
        Model.OpenAI(
            "gpt-4o-mini",
            api_key="key",
            strengths=[TaskType.GENERAL],
            input_media={Media.TEXT},
        ),
        # Vision model
        Model.OpenAI(
            "gpt-4o",
            api_key="key",
            strengths=[TaskType.VISION, TaskType.GENERAL],
            input_media={Media.TEXT, Media.IMAGE},
        ),
    ],
    model_router=RoutingConfig(routing_mode=RoutingMode.AUTO),
)
```

**How it works:**
1. User sends message with image
2. ModalityDetector finds images in the message
3. Router picks a model that supports `Media.IMAGE`

---

## Manual Task Override

Sometimes the router gets it wrong. Override the task type manually:

```python
# The user says "Fix this" - ambiguous: code or general?
# Tell the router it's a CODE task
r = agent.run("Fix this syntax error", task_type=TaskType.CODE)
```

**When to use:**
- Ambiguous prompts
- User intent is clear but phrasing isn't
- Debugging routing decisions

---

## Custom Routing Logic

Need special rules? Use a routing callback:

```python
def my_routing(prompt: str, task_type: TaskType, profile_names: list[str]) -> str | None:
    # VIP users always get premium model
    if "VIP" in prompt:
        return "premium"
    
    # A/B test: half of "write code" goes to preview model
    if task_type == TaskType.CODE and "preview" in profile_names:
        return "preview" if hash(prompt) % 2 == 0 else None
    
    # Let router decide
    return None

agent = Agent(
    model=[...],
    model_router=RoutingConfig(routing_rule_callback=my_routing),
)
```

---

## Understanding Routing Decisions

Every routed response tells you why it chose that model:

```python
r = agent.run("Write a sorting function")

# Routing reason explains the decision
print(r.routing_reason.selected_model)   # "claude-code"
print(r.routing_reason.task_type)         # TaskType.CODE
print(r.routing_reason.reason)             # "Matched CODE, highest priority capable"
print(r.routing_reason.cost_estimate)    # 0.0034
print(r.routing_reason.classification_confidence)  # 0.89
```

---

## Force a Specific Model

Want to bypass routing for debugging or special cases?

```python
# Always use Claude, ignore routing
agent = Agent(
    model=[...],
    model_router=RoutingConfig(
        force_model=Model.Anthropic("claude-opus", api_key="key"),
    ),
)
```

---

## OpenRouter: One API Key, Many Providers

OpenRouter lets you use OpenAI, Anthropic, Google, and more with a single API key:

```python
from syrin.model import Model, OpenRouterBuilder

builder = OpenRouterBuilder(api_key="your-openrouter-key")

# Now use any provider with one key
claude = builder.model("anthropic/claude-sonnet-4-5")
gpt = builder.model("openai/gpt-4o-mini")
gemini = builder.model("google/gemini-2.0-flash")

agent = Agent(
    model=[claude, gpt, gemini],
    model_router=RoutingConfig(routing_mode=RoutingMode.AUTO),
)
```

**Benefits:**
- Single API key for all providers
- Unified billing
- Automatic fallback between providers

---

## Complete Example: Smart Agent

Here's everything together:

```python
from syrin import Agent, Budget
from syrin.enums import Media
from syrin.model import Model
from syrin.router import RoutingConfig, RoutingMode, TaskType

class SmartAgent(Agent):
    model = [
        # The powerhouse for complex tasks
        Model.Anthropic(
            "claude-opus-4-5",
            api_key="your-key",
            profile_name="premium",
            strengths=[TaskType.CODE, TaskType.REASONING, TaskType.PLANNING],
            priority=100,
        ),
        # Great for code too, slightly cheaper
        Model.Anthropic(
            "claude-sonnet-4-5",
            api_key="your-key",
            profile_name="code",
            strengths=[TaskType.CODE, TaskType.REASONING],
            priority=90,
        ),
        # Fast and cheap for general tasks
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
        budget=Budget(max_cost=10.00),
        budget_optimisation=True,
        prefer_cheaper_below_budget_ratio=0.20,
        force_cheapest_below_budget_ratio=0.10,
    )
    
    system_prompt = "You are a helpful AI assistant."

# Use it
agent = SmartAgent()

# Routes based on task
r = agent.run("Hello!")
r = agent.run("Write a quicksort")
r = agent.run("Analyze this image", media={Media.IMAGE})

# See what happened
print(f"Model used: {r.model_used}")
print(f"Task type: {r.task_type}")
print(f"Cost: ${r.cost:.6f}")
```

---

## What Just Happened?

Here's the routing flow:

```
1. User sends message
       ↓
2. ModalityDetector checks for images/video
       ↓
3. PromptClassifier determines task type (CODE, GENERAL, etc.)
       ↓
4. Router filters models by:
   - Does it support the task? (strengths)
   - Does it support the media? (input_media)
   - Does it support tools? (supports_tools)
       ↓
5. Router selects from capable models based on:
   - Routing mode (AUTO, COST_FIRST, QUALITY_FIRST)
   - Budget remaining
   - Priority
       ↓
6. Selected model handles the request
```

---

## What's Next?

- [Providers](/core/models-providers) - All supported models
- [Custom Models](/core/models-custom) - Add your own models
- [Budget](/core/budget) - Control your spending

## See Also

- [Structured Output](/agent/structured-output) - Get typed responses
- [Tools](/agent/tools) - Give your agent abilities
- [Prompts](/core/prompts) - Get the best from your model
