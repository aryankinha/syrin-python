# Model

> **Full guide:** For built-in models, Model.Custom, inheritance, and standalone `model.complete()`, see [Models Guide](../models.md).

How agents use models: the `model` param, `switch_model()`, and integration with budget and rate limiting.

---

## Basic Usage

The model is **required**. Pass it at construction or set it on the class:

```python
from syrin import Agent
from syrin.model import Model

agent = Agent(model=Model.OpenAI("gpt-4o-mini"))

# Or on a class
class MyAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini")
    system_prompt = "You are helpful."
```

See [Constructor](constructor.md) for the full `model` parameter reference.

---

## Supported Models

The agent accepts any `Model` or `ModelConfig`:

- `Model.OpenAI()`, `Model.Anthropic()`, `Model.Google()`, `Model.Ollama()`, `Model.LiteLLM()`
- `Model.Custom()` for third-party OpenAI-compatible APIs
- Custom models via inheritance

All provider-specific options (temperature, max_tokens, api_key, etc.) are described in [Models Guide](../models.md).

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
    model=Model.OpenAI("gpt-4o"),
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
    model = Model.OpenAI("gpt-4o")

class CheaperAgent(BaseAgent):
    model = Model.OpenAI("gpt-4o-mini")  # Overrides parent
```

See [Creating Agents](creating-agents.md) for full inheritance rules.

---

## See Also

- [Models Guide](../models.md) — Built-ins, custom models, standalone `complete()`
- [Constructor](constructor.md) — Full `model` parameter reference
- [Budget](budget.md) — Budget thresholds and switch-model
- [Rate Limiting](rate-limiting.md) — Rate-limit thresholds and switch-model
- [Properties](properties.md) — `switch_model()` method
