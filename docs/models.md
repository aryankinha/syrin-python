# Models Guide

Complete guide to using and creating models in Syrin — from built-in providers to custom implementations.

> **Agent integration:** For the agent `model` param, `switch_model()`, and integration with budget/rate limits, see [Agent: Model](agent/model.md).

## Overview

Syrin models are the LLM backends your agents use. You can:
- Use **built-in models** (OpenAI, Anthropic, Google, Ollama, LiteLLM)
- Use **Model.OpenRouter** or **OpenRouterBuilder** — one API key for multiple providers (ideal for routing)
- **Call models directly** with `model.complete()` or `model.acomplete()` (no Agent needed)
- Use **Model.Custom** for third-party OpenAI-compatible APIs (DeepSeek, KIMI, Grok)
- Create **custom models** via inheritance or the `make_model()` factory

API keys must be passed explicitly — the library never auto-reads from environment variables.

### Model vs Agent — When to Use Which

| Use **Model** directly | Use **Agent** |
|------------------------|---------------|
| Simple completions (chat, summarization) | Tools (search, calculate, call APIs) |
| Pipelines, batch processing | Memory (remember across turns) |
| You handle prompts and tool loops yourself | Budget control (cost limits) |
| No need for structured state | Multi-turn conversations with state |

**Quick rule:** Need tools, memory, or budget? Use `Agent(model=...)`. Otherwise, `model.complete(messages)` is enough.

**Multiple models?** Pass `model=[M1, M2, M3]` plus `model_router=RoutingConfig(...)` to route per request by task, cost, and modality. See [Routing](routing.md) and [Agent: Model](agent/model.md).

**No API key?** Use `Model.Almock()` to run without any provider — ideal for local development, CI, or trying the library. See [Almock (An LLM Mock)](#almock-an-llm-mock) below.

---

## Built-in Models

### Almock (An LLM Mock)

No API calls, no key required. Use for development, tests, and examples.

```python
from syrin import Agent, Model, AlmockPricing

# Default: Lorem Ipsum response, random 1–3s latency, medium pricing
model = Model.Almock()

# Fast (no delay), custom response, high pricing for budget tests
model = Model.Almock(
    latency_min=0,
    latency_max=0,
    response_mode="custom",
    custom_response="Hello, mock!",
    pricing_tier=AlmockPricing.HIGH,
)
agent = Agent(model=model, system_prompt="You are helpful.")
r = agent.response("Hi")
# r.content == "Hello, mock!"; r.cost uses the chosen pricing tier
```

Options: `pricing_tier` (low, medium, high, ultra_high), `context_window`, `response_mode` ("lorem" | "custom"), `custom_response`, `lorem_length`, `latency_min`/`latency_max` or `latency_seconds` (must be > 0).

### OpenAI

```python
import os
from syrin import Model

model = Model.OpenAI("gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
model = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))  # Cheap & fast
model = Model.OpenAI("gpt-4", api_key=os.getenv("OPENAI_API_KEY"))       # Previous
```

### Anthropic (Claude)

```python
import os
from syrin import Model

model = Model.Anthropic("claude-sonnet-4-5", api_key=os.getenv("ANTHROPIC_API_KEY"))
model = Model.Anthropic("claude-opus-4-5", api_key=os.getenv("ANTHROPIC_API_KEY"))
```

### Google (Gemini)

```python
import os
from syrin import Model

model = Model.Google("gemini-2.0-flash", api_key=os.getenv("GOOGLE_API_KEY"))
model = Model.Google("gemini-1.5-pro", api_key=os.getenv("GOOGLE_API_KEY"))
```

### Ollama (Local)

No API key needed for local models:

```python
model = Model.Ollama("llama3")
model = Model.Ollama("mistral")
```

### LiteLLM (50+ Providers)

Unified interface for many providers:

```python
import os
from syrin import Model

model = Model.LiteLLM("openai/gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
model = Model.LiteLLM("anthropic/claude-3-5-sonnet", api_key=os.getenv("ANTHROPIC_API_KEY"))
```

### OpenRouter — Single API Key for Multiple Providers

Use one API key to access Anthropic, OpenAI, Google, and many other providers. Ideal for routing across models without managing multiple keys.

```python
import os
from syrin.model import Model

model = Model.OpenRouter(
    "anthropic/claude-sonnet-4-5",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)
```

**OpenRouterBuilder** — Create multiple models with one key for Agent routing:

```python
import os
from syrin import Agent
from syrin.model import Model, OpenRouterBuilder
from syrin.router import RoutingConfig, RoutingMode

builder = OpenRouterBuilder(api_key=os.getenv("OPENROUTER_API_KEY"))
claude = builder.model("anthropic/claude-sonnet-4-5")
gpt = builder.model("openai/gpt-4o-mini")

agent = Agent(
    model=[claude, gpt],
    model_router=RoutingConfig(routing_mode=RoutingMode.COST_FIRST),
)
```

Response headers (`x-openrouter-total-cost`, `x-openrouter-model-used`) populate `response.actual_cost` and `response.model_used` when available.

See [Routing](routing.md) for full routing and Agent integration.

---

## Tweakable Properties

All model constructors accept these optional properties. Works with `Model.OpenAI`, `Model.Anthropic`, `Model.Google`, `Model.Custom`, etc.

| Property | Type | Description |
|----------|------|-------------|
| `temperature` | `float` | Sampling temperature (0.0–2.0). Higher = more creative. |
| `max_tokens` | `int` | Maximum tokens in the response. |
| `max_output_tokens` | `int` | Same as max_tokens (alias). |
| `top_p` | `float` | Nucleus sampling. |
| `top_k` | `int` | Top-k sampling. |
| `stop` | `list[str]` | Stop sequences. |
| `context_window` | `int` | Model context window size. |
| `api_key` | `str` | API key (required for most providers). |
| `api_base` | `str` | Custom API base URL. Providers also read `OPENAI_BASE_URL`, `ANTHROPIC_BASE_URL`, etc. if unset. |
| `output` | `type` | Structured output Pydantic model. |
| `input_price` | `float` | Cost per 1M input tokens (for budget). |
| `output_price` | `float` | Cost per 1M output tokens (for budget). |
| `fallback` | `list[Model]` | Fallback models on failure. |

**Common model names:** `gpt-4o`, `gpt-4o-mini`, `gpt-4` (OpenAI); `claude-sonnet-4-5`, `claude-opus-4-5` (Anthropic); `gemini-2.0-flash`, `gemini-1.5-pro` (Google); `llama3`, `mistral` (Ollama).

**Example:**

```python
import os
from syrin import Model

model = Model.OpenAI(
    "gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.7,
    max_tokens=2048,
    context_window=8192,
)
```

---

## Calling a Model Directly

You can use a model without an Agent by calling `model.complete()` (sync) or `model.acomplete()` (async). This is useful for simple completions, pipelines, or when you don't need tools or budget.

**Messages:** Pass a list of `Message` objects. Each has `role` (system, user, assistant, or tool) and `content`. Use `MessageRole` for roles.

```python
import os
from syrin import Model
from syrin.types import Message
from syrin.enums import MessageRole

model = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))

messages = [
    Message(role=MessageRole.SYSTEM, content="You are helpful."),
    Message(role=MessageRole.USER, content="What is 2+2?"),
]

# Sync
response = model.complete(messages)
print(response.content)
print(response.token_usage)

# Async
response = await model.acomplete(messages)
print(response.content)
```

`complete()` and `acomplete()` return a `ProviderResponse` with:
- `content` — The model's text response
- `tool_calls` — Tool calls (if any)
- `token_usage` — Input/output token counts
- `raw_response` — Raw provider response

If the model has an `output` type set (structured output), the response content is parsed into that Pydantic model automatically.

**Streaming:** Each iteration yields a `ProviderResponse` chunk with partial `content`. Use `complete(stream=True)` (sync), `acomplete(stream=True)` (async), or `astream()` (async only). Pick based on your event loop: sync code → `complete(stream=True)`; async code → `acomplete(stream=True)` or `astream()`.

```python
# Sync
for chunk in model.complete(messages, stream=True):
    print(chunk.content or "", end="")

# Async — via acomplete(stream=True) or explicit astream()
async for chunk in model.acomplete(messages, stream=True):
    print(chunk.content or "", end="")

# Or use astream() directly
async for chunk in model.astream(messages):
    print(chunk.content or "", end="")
```

**Function calling (tools):**

Pass `tools` when you need the model to call functions. The response may include `tool_calls`; execute them and add tool-role messages, then call the model again.

```python
import os
from syrin import Model, tool
from syrin.types import Message
from syrin.enums import MessageRole

model = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
messages = [Message(role=MessageRole.USER, content="What's the weather in Paris?")]

@tool
def get_weather(city: str) -> str:
    """Get current weather for a city."""
    return f"Weather in {city}: 72°F, sunny"

tools = [get_weather]
response = model.complete(messages, tools=tools)

# If model requested tool calls, add assistant + tool messages and call again
if response.tool_calls:
    messages.append(Message(role=MessageRole.ASSISTANT, content=response.content or "", tool_calls=response.tool_calls))
    for tc in response.tool_calls:
        spec = next(t for t in tools if t.name == tc.name)
        result = spec.func(**tc.arguments)
        messages.append(Message(role=MessageRole.TOOL, content=str(result), tool_call_id=tc.id))
    response = model.complete(messages, tools=tools)

print(response.content)
```

For multi-turn tool loops (model calls tool → you add result → model continues), repeat the pattern in a loop until `response.tool_calls` is empty. Or use an `Agent` with tools for a built-in loop.

**Output:** Plain text response, or structured data if the model has `output=MyPydanticModel`.

---

## Model.Custom — Third-Party OpenAI-Compatible APIs

Use `Model.Custom()` for providers that expose OpenAI-compatible APIs (same message format, `/v1/chat/completions` endpoint). Examples: DeepSeek, KIMI, Grok, and most third-party APIs.

**Required:** `model_id`, `api_base`  
**Default provider:** `"openai"` (uses OpenAI provider under the hood)

```python
import os
from syrin import Model

# DeepSeek
model = Model.Custom(
    "deepseek-chat",
    api_base="https://api.deepseek.com/v1",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
)

# Grok (xAI)
model = Model.Custom(
    "grok-3-mini",
    api_base="https://api.x.ai/v1",
    api_key=os.getenv("XAI_API_KEY"),
    temperature=0.7,
    max_tokens=2048,
)

# KIMI (Moonshot)
model = Model.Custom(
    "moonshot-v1-8k",
    api_base="https://api.moonshot.ai/v1",
    api_key=os.getenv("MOONSHOT_API_KEY"),
)
```

With `provider="litellm"` you can route through LiteLLM instead:

```python
model = Model.Custom(
    "custom/foobar",
    api_base="https://custom.api/v1",
    provider="litellm",
    api_key=os.getenv("CUSTOM_API_KEY"),
)
```

---

## Custom Models via Inheritance

For APIs that don't follow the OpenAI format, inherit from `Model` and override `complete()` (and `acomplete()` for async).

```python
from syrin import Model
from syrin.types import Message, ProviderResponse
from syrin.enums import MessageRole

class MyCustomModel(Model):
    """Custom model for any LLM API."""

    def __init__(self, model_name: str = "my-model", *, api_key: str | None = None, **kwargs):
        super().__init__(
            model_id=f"custom/{model_name}",
            provider="custom",
            api_key=api_key,
            **kwargs,
        )

    def complete(
        self,
        messages: list[Message],
        *,
        tools=None,
        temperature=None,
        max_tokens=None,
        stream=False,
        **kwargs,
    ) -> ProviderResponse:
        # Your implementation: call your API, map to Syrin types
        # response = your_api_client.chat(messages, temperature=temperature, max_tokens=max_tokens)
        return ProviderResponse(content="custom response", tool_calls=[])

    async def acomplete(self, messages, **kwargs) -> ProviderResponse:
        return self.complete(messages, **kwargs)

# Use the model directly (Agent uses provider, so custom complete() is for direct calls)
model = MyCustomModel("my-llm", api_key="...")
response = model.complete([Message(role=MessageRole.USER, content="Hi")])
```

**Key points:**
- `complete()` receives `list[Message]` and returns `ProviderResponse`
- `ProviderResponse(content=..., tool_calls=[], token_usage=..., raw_response=...)`
- Implement both `complete` (sync) and `acomplete` (async) for full support

---

## make_model() Factory

Create a reusable model *class* for an OpenAI-compatible API without writing boilerplate. Best when you want a named class (e.g. `KimiModel`) with fixed base URL and defaults.

```python
from syrin.model import make_model
import os

KimiModel = make_model(
    name="Kimi",
    provider="openai",  # KIMI uses OpenAI-compatible API
    default_model="kimi2.5",
    base_url="https://api.moonshot.ai/v1",
    context_window=128000,
)

# Use it
model = KimiModel(api_key=os.getenv("MOONSHOT_API_KEY"))
model = KimiModel("kimi-k2-turbo-preview", api_key=os.getenv("MOONSHOT_API_KEY"))
```

`make_model()` returns a `Model` subclass. The `provider` you pass determines which backend is used:
- `provider="openai"` — for OpenAI-compatible APIs (recommended for DeepSeek, KIMI, Grok, etc.)
- `provider="litellm"` — for LiteLLM-routed providers

For most third-party APIs, use `provider="openai"` and the custom `base_url`.

---

## Fallback Chains

Add fallback models when the primary fails:

```python
import os
from syrin import Model

model = Model.Anthropic(
    "claude-sonnet",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
).with_fallback(
    Model.OpenAI("gpt-4o", api_key=os.getenv("OPENAI_API_KEY")),
    Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY")),
    Model.Ollama("llama3"),  # Local fallback
)
```

---

## Immutable Variants: with_params, with_output, with_middleware

Models are immutable. Use these methods to get a *copy* with changes:

| Method | Purpose |
|--------|---------|
| `with_params(...)` | Copy with overridden temperature, max_tokens, context_window, etc. |
| `with_output(MyPydanticModel)` | Copy configured for structured output. |
| `with_middleware(Middleware)` | Copy with request/response transform. |

**with_params** — Create a variant without mutating the original:

```python
import os
from syrin import Model

base = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
creative = base.with_params(temperature=0.9, max_tokens=4096)
strict = base.with_params(temperature=0.0, max_tokens=512)
# base is unchanged
```

**with_output** — Shorthand for structured output:

```python
import os
from pydantic import BaseModel
from syrin import Model
from syrin.types import Message
from syrin.enums import MessageRole

class Summary(BaseModel):
    title: str
    bullets: list[str]

model = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
summarizer = model.with_output(Summary, temperature=0.3)
messages = [Message(role=MessageRole.USER, content="Summarize Python in 3 bullets")]
response = summarizer.complete(messages)
# response.content is JSON; response.raw_response is parsed Summary
```

---

## Request/Response Middleware

Transform requests before they hit the LLM, or responses after. Subclass `Middleware` and use `with_middleware()`:

```python
import os
from syrin import Model, Middleware
from syrin.types import Message, ProviderResponse
from syrin.enums import MessageRole

class LoggingMiddleware(Middleware):
    def transform_request(self, messages, **kwargs):
        print(f"Request: {len(messages)} messages")
        return messages, kwargs

    def transform_response(self, response: ProviderResponse) -> ProviderResponse:
        print(f"Response: {len(response.content or '')} chars, {response.token_usage.total_tokens} tokens")
        return response

model = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
model = model.with_middleware(LoggingMiddleware())
messages = [Message(role=MessageRole.USER, content="Hi")]
response = model.complete(messages)  # Logs before/after
```

Use cases: logging, PII redaction, prompt injection guards, response filtering.

---

## create_model() — Dynamic Model Creation

When the provider or model name comes from config, use `create_model()` instead of `Model.OpenAI`, etc.:

```python
import os
from syrin.model import create_model
from syrin.types import Message
from syrin.enums import MessageRole

# Provider and model from config
provider = "openai"
model_name = "gpt-4o-mini"
model = create_model(provider, model_name, api_key=os.getenv("OPENAI_API_KEY"))
messages = [Message(role=MessageRole.USER, content="Hello")]
response = model.complete(messages)
```

**Args:** `provider` (openai, anthropic, ollama, google, litellm), `model_name`, optional `api_key`, `base_url`, and any Model kwargs.

**Returns:** Configured `Model` instance.

Use `Model.OpenAI("gpt-4o", ...)` when the provider is known; use `create_model()` when it's dynamic.

---

## Model Properties & Utilities

Inspect a model or use it for cost/logging:

| Property/Method | Description |
|-----------------|-------------|
| `model.settings` | `ModelSettings`: temperature, max_output_tokens, context_window, top_p, stop |
| `model.metadata` | Dict: model_id, provider, name, has_fallback, context_window, etc. |
| `model.pricing` | `ModelPricing \| None` — input/output cost per 1M tokens |
| `model.get_pricing()` | Same as `pricing`; resolves from built-in table if not set |
| `model.count_tokens(text)` | Estimate token count for a string |

**Example:**

```python
import os
from syrin import Model
from syrin.types import Message
from syrin.enums import MessageRole

model = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
messages = [Message(role=MessageRole.USER, content="Hello")]
print(model.settings.temperature)      # 0.7 or None
print(model.settings.context_window)   # 128000
print(model.metadata)                  # {"model_id": "openai/gpt-4o-mini", ...}

n = model.count_tokens("Hello, world!")
print(n)  # ~4

response = model.complete(messages)
usage = response.token_usage
pricing = model.get_pricing()
if pricing and usage:
    cost = (usage.input_tokens * pricing.input_per_1m + usage.output_tokens * pricing.output_per_1m) / 1_000_000
    print(f"Est. cost: ${cost:.6f}")
```

---

## ModelRegistry — Named Model Lookup

Register models by name and look them up later. Useful when the model choice comes from config or feature flags:

```python
import os
from syrin import Model, ModelRegistry
from syrin.types import Message
from syrin.enums import MessageRole

reg = ModelRegistry()
reg.register("default", Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY")))
reg.register("premium", Model.OpenAI("gpt-4o", api_key=os.getenv("OPENAI_API_KEY")))
reg.register("local", Model.Ollama("llama3"))

# Lookup by name (e.g., from config)
model_name = "default"
model = reg.get(model_name)
messages = [Message(role=MessageRole.USER, content="Hi")]
response = model.complete(messages)

print(reg.list_names())  # ["default", "premium", "local"]
```

`ModelRegistry` is a singleton: `ModelRegistry()` returns the same instance everywhere.

---

## Structured Output

Constrain responses to a Pydantic schema:

```python
import os
from pydantic import BaseModel
from syrin import Model

class SentimentResult(BaseModel):
    sentiment: str
    confidence: float

model = Model.OpenAI(
    "gpt-4o",
    output=SentimentResult,
    api_key=os.getenv("OPENAI_API_KEY"),
)
```

See [Structured Output](structured-output.md) for details.

---

## Centralized Models

In larger projects, define models in one place and import them:

```python
# myproject/models.py
import os
from syrin import Model

gpt4 = Model.OpenAI("gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
claude = Model.Anthropic("claude-sonnet-4-5", api_key=os.getenv("ANTHROPIC_API_KEY"))
deepseek = Model.Custom(
    "deepseek-chat",
    api_base="https://api.deepseek.com/v1",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
)

# Elsewhere
from myproject.models import gpt4, claude
agent = Agent(model=gpt4, system_prompt="...")
```

See `examples/models/models.py` for a full example.

---

## Environment Variable Resolution

For `model_id`, you can use `$VAR` or `${VAR}` to resolve from environment variables. The library resolves these before provider detection:

```python
# model_id becomes the value of MY_MODEL env var, or "openai/gpt-4o-mini" if unset
model = Model(provider="openai", model_id="$MY_MODEL")
```

API keys are **not** auto-read from env; pass `api_key` explicitly. For `api_base`, providers read `OPENAI_BASE_URL`, `ANTHROPIC_BASE_URL`, `OLLAMA_BASE_URL`, `GOOGLE_BASE_URL`, `LITELLM_BASE_URL` when `api_base` is not passed.

---

## Errors & Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `ProviderError` | API call failed (rate limit, network, invalid response) | Check API key, credits, network. Use fallback models. |
| `ModelNotFoundError` | `ModelRegistry.get(name)` with unknown name | Register the model first, or use a valid name. |
| `ValueError: model_id is required` | `Model.Custom("", ...)` with empty model_id | Pass a non-empty `model_id`. |
| `ValueError: api_base is required` | `Model.Custom(..., api_base=None)` | Pass a non-empty `api_base` URL. |
| `ValueError: Provider name cannot be empty` | `create_model("", ...)` | Pass a valid provider string. |

**Common issues:**
- **Missing API key:** Pass `api_key=os.getenv("OPENAI_API_KEY")` (or your key) to the model constructor. The library does not auto-read from env.
- **Rate limits:** Add fallback models with `with_fallback()`.
- **All fallbacks failed:** `ProviderError("All fallback models failed")` — check that at least one model has valid credentials and is reachable.

---

## Quick Reference

| Approach | Use when |
|----------|----------|
| `Model.OpenAI`, `Model.Anthropic`, etc. | Using built-in providers |
| `Model.OpenRouter` / `OpenRouterBuilder` | One key for multiple providers (routing) |
| `Model.Custom` | Third-party API with OpenAI-compatible format |
| `create_model(provider, model_name)` | Provider/model from config (dynamic) |
| `make_model()` | Reusable class for an OpenAI-compatible API |
| Inherit `Model` | Custom API with different format |
| `ModelRegistry` | Lookup models by name (config-driven) |

---

## Related

- [Structured Output](structured-output.md) — Type-safe responses
- [Budget Control](budget-control.md) — Cost limits and pricing
- [Feature Reference](reference.md) — Full API reference
