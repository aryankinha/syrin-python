# Model

> **Full guide:** For built-in models, Model.Custom, inheritance, and standalone `model.complete()`, see [Models Guide](../models.md).

How agents use models: the `model` param (single or list for routing), `model_router`, `switch_model()`, and integration with budget and rate limiting.

---

## Basic Usage

The model is **required**. Pass it at construction or set it on the class:

```python
from syrin import Agent
from syrin.model import Model

agent = Agent(
    # model=Model.OpenAI("gpt-4o-mini"),
    model=Model.Almock(),  # No API Key needed
)

# Or on a class
class MyAgent(Agent):
    # model = Model.OpenAI("gpt-4o-mini")
    model = Model.Almock()  # No API Key needed
    system_prompt = "You are helpful."
```

See [Constructor](constructor.md) for the full `model` parameter reference.

---

## Supported Models

The agent accepts any `Model` or `ModelConfig`:

- `Model.OpenAI()`, `Model.Anthropic()`, `Model.Google()`, `Model.Ollama()`, `Model.LiteLLM()`
- `Model.OpenRouter()` / `OpenRouterBuilder` — one API key for multiple providers
- `Model.Custom()` for third-party OpenAI-compatible APIs
- Custom models via inheritance

All provider-specific options (temperature, max_tokens, api_key, etc.) are described in [Models Guide](../models.md).

## Model List + Routing

Pass a **list of models** with `model_router` to enable automatic per-request routing:

```python
from syrin import Agent, Budget
from syrin.model import Model
from syrin.router import RoutingConfig, RoutingMode

agent = Agent(
    model=[
        Model.Anthropic("claude-sonnet-4-5", api_key="..."),
        Model.OpenAI("gpt-4o-mini", api_key="..."),
    ],
    model_router=RoutingConfig(routing_mode=RoutingMode.AUTO),
    system_prompt="You are helpful.",
    budget=Budget(run=10.0),
)

# Agent routes each request by task, cost, and modality
r = agent.response("write a sorting function")  # → Claude (CODE)
r = agent.response("what is the weather?")      # → GPT-4o-mini (GENERAL)

print(r.routing_reason.selected_model, r.model_used, r.actual_cost)
```

**RoutingConfig options:** `routing_mode` (AUTO, COST_FIRST, QUALITY_FIRST), `force_model`, `classifier`, `routing_rule_callback`, budget thresholds. See [Routing](../routing.md) for full details.

---

## switch_model()

Change the model at runtime (e.g. when hitting a budget or rate limit threshold):

```python
agent.switch_model(Model.OpenAI("gpt-4o-mini"))
```

Typical uses:

- **Budget threshold** — switch to a cheaper model when approaching the limit
- **Rate limit** — switch when RPM/TPM thresholds are hit
- **Fallback** — switch when the primary model fails

---

## Model and Budget

Use `BudgetThreshold` with a callable to switch models when approaching the limit:

```python
from syrin import Agent, Budget
from syrin.model import Model
from syrin.threshold import BudgetThreshold

agent = Agent(
    # model=Model.OpenAI("gpt-4o"),
    model=Model.Almock(),  # No API Key needed
    budget=Budget(
        run=1.0,
        thresholds=[
            BudgetThreshold(at=80, action=lambda ctx: ctx.parent.switch_model(Model.OpenAI("gpt-4o-mini"))),
        ],
    ),
)
```

At 80% of the run budget, the agent switches to the cheaper model. `ctx.parent` is the agent instance.

---

## Model and Rate Limiting

When approaching provider rate limits, you can switch to a fallback model. See [Rate Limiting](rate-limiting.md) for `RateLimitAction.SWITCH_MODEL` and `switch_to_model`.

---

## Response

The model ID used for the last completion is available on the response:

```python
response = agent.response("Hello")
print(response.model)  # e.g. "gpt-4o-mini"
```

---

## Inheritance

On subclasses, `model` follows MRO merge rules: the first definition in the class hierarchy wins. Instance arguments override class attributes.

```python
class BaseAgent(Agent):
    # model = Model.OpenAI("gpt-4o")
    model = Model.Almock()  # No API Key needed

class CheaperAgent(BaseAgent):
    model = Model.OpenAI("gpt-4o-mini")  # Overrides parent (use real model when you have a key)
```

See [Creating Agents](creating-agents.md) for full inheritance rules.

---

## Provider resolution and errors

When you pass a `ModelConfig` (e.g. from a config file) with a `provider=` that the registry doesn’t know, the agent raises **`ProviderNotFoundError`** with a message listing known providers (`openai`, `anthropic`, `ollama`, `litellm`). This avoids silent fallback to a different provider.

When you use a `Model` instance (e.g. `Model.OpenAI(...)`), the provider is resolved from the model, so invalid provider names only occur when constructing an agent from a raw `ModelConfig` with a typo or unsupported provider.

For programmatic lookup with strict checking:

```python
from syrin.providers.registry import get_provider
from syrin.exceptions import ProviderNotFoundError

# strict=False (default): unknown name falls back to LiteLLM
provider = get_provider("openai")

# strict=True: unknown name raises ProviderNotFoundError
try:
    provider = get_provider("typo", strict=True)
except ProviderNotFoundError as e:
    print(e)  # Lists known providers
```

---

## See Also

- [Routing](../routing.md) — Model list, RoutingConfig, OpenRouter, task classification
- [Models Guide](../models.md) — Built-ins, custom models, standalone `complete()`
- [Constructor](constructor.md) — Full `model` parameter reference
- [Budget](budget.md) — Budget thresholds and switch-model
- [Rate Limiting](rate-limiting.md) — Rate-limit thresholds and switch-model
- [Properties](properties.md) — `switch_model()` method
