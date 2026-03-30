---
title: Custom Model
description: Implement your own LLM providers for any API
weight: 210
---

## When Built-in Providers Aren't Enough

You've seen how to use `Model.OpenAI()`, `Model.Anthropic()`, and other built-in providers. But what if your organization uses a proprietary LLM? What if you need to integrate with a model not yet supported?

**The challenge:**
- Vendors ship new models constantly
- Proprietary/internal models exist in every organization
- Built-in providers can't cover every API
- You need a way to plug in any LLM without rewriting your agent logic

**The solution:** Syrin's extensible Model architecture lets you implement custom providers in minutes. The agent doesn't care where the LLM comes from—it just calls `model.complete()`.

## Architecture Overview

Syrin's model system has two layers:

1. **Model** — Configuration wrapper (model_id, settings, middleware, fallbacks)
2. **Provider** — Low-level API client (HTTP calls, response parsing)

The flow:
- Agent calls `model.complete(messages)`
- Model applies middleware and forwards to Provider
- Provider makes the actual API call

Key components:
- Model: `model_id`, `settings`, `middleware`, `fallbacks`
- Model methods: `with_params()`, `with_middleware()`, `with_output()`
- Provider methods: `complete()`, `stream()`
- Built-in providers: OpenAIProvider, AnthropicProvider, LiteLLMProvider, CustomProvider (you build)

## Approach 1: Model.Custom (Simplest)

For OpenAI-compatible APIs, you don't need to write any code:

```python
from syrin import Model

# Any OpenAI-compatible API
model = Model.Custom(
    model_id="deepseek-chat",
    api_base="https://api.deepseek.com/v1",
    api_key="your-deepseek-api-key",
)

# Grok, Mistral, Cohere, etc.
model = Model.Custom(
    model_id="grok-3-mini",
    api_base="https://api.x.ai/v1",
    api_key="your-x-api-key",
    temperature=0.7,
)
```

**What just happened:**
1. You created a Model pointing to any OpenAI-compatible endpoint
2. Syrin routes it through the OpenAI-compatible provider
3. Your agent works the same as with any other model

### Custom with LiteLLM

LiteLLM wraps 100+ providers with a unified interface:

```python
model = Model.LiteLLM(
    model_name="anthropic/claude-3-5-sonnet-20241022",
    api_key="your-litellm-key",
)
```

## Approach 2: Custom Provider (Full Control)

When you need to handle non-standard APIs, authentication, or response formats, implement a Provider:

```python
from abc import ABC, abstractmethod
from syrin.providers.base import Provider
from syrin.types import Message, ModelConfig, ProviderResponse
from syrin.tool import ToolSpec

class MyCustomProvider(Provider):
    """Provider for your internal LLM API."""
    
    async def complete(
        self,
        messages: list[Message],
        model: ModelConfig,
        tools: list[ToolSpec] | None = None,
        **kwargs,
    ) -> ProviderResponse:
        # Transform messages to your API format
        api_messages = self._transform_messages(messages)
        
        # Make the API call
        response = await self._call_api(
            url=f"{model.base_url}/chat",
            headers={"Authorization": f"Bearer {model.api_key}"},
            json={
                "model": model.model_id,
                "messages": api_messages,
                "tools": self._transform_tools(tools) if tools else None,
                **kwargs,
            },
        )
        
        # Parse response into ProviderResponse
        return ProviderResponse(
            content=response["choices"][0]["message"]["content"],
            tool_calls=self._extract_tool_calls(response),
            token_usage=self._extract_usage(response),
        )
```

### Complete Example: Internal Model Provider

Here's a real implementation for a fictional internal LLM:

```python
import aiohttp
from typing import Any

from syrin.providers.base import Provider
from syrin.types import Message, ModelConfig, ProviderResponse
from syrin.tool import ToolSpec


class InternalLLMProvider(Provider):
    """Provider for Acme Corp's internal LLM."""
    
    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.environ.get("ACME_LLM_API_KEY")
        self._session: aiohttp.ClientSession | None = None
    
    async def complete(
        self,
        messages: list[Message],
        model: ModelConfig,
        tools: list[ToolSpec] | None = None,
        **kwargs: Any,
    ) -> ProviderResponse:
        # Ensure we have a session
        if self._session is None:
            self._session = aiohttp.ClientSession()
        
        # Transform messages to Acme format
        acme_messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]
        
        # Build request
        request_body = {
            "model": model.model_id,
            "messages": acme_messages,
            **kwargs,
        }
        
        if tools:
            request_body["tools"] = self._to_acme_tools(tools)
        
        # Make request
        async with self._session.post(
            f"{model.base_url}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=request_body,
        ) as resp:
            data = await resp.json()
        
        # Extract response
        choice = data["choices"][0]
        message = choice["message"]
        
        return ProviderResponse(
            content=message.get("content"),
            tool_calls=self._extract_tool_calls(message) if message.get("tool_calls") else [],
            token_usage={
                "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
                "total_tokens": data.get("usage", {}).get("total_tokens", 0),
            },
        )
    
    def _to_acme_tools(self, tools: list[ToolSpec]) -> list[dict]:
        """Convert ToolSpec to Acme's tool format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters_schema,
                },
            }
            for tool in tools
        ]
    
    def _extract_tool_calls(self, message: dict) -> list[dict]:
        """Extract tool calls from response."""
        calls = []
        for tc in message.get("tool_calls", []):
            calls.append({
                "id": tc["id"],
                "name": tc["function"]["name"],
                "arguments": tc["function"]["arguments"],
            })
        return calls
    
    async def close(self) -> None:
        """Clean up resources."""
        if self._session:
            await self._session.close()
            self._session = None
```

### Using Your Custom Provider

```python
from syrin import Agent, Model

# Create provider instance
provider = InternalLLMProvider(api_key="your-key")

# Create model with your provider
model = Model(
    model_id="acme-internal-v1",
    provider="internal",  # Register this provider
)

# Register the provider (one-time setup)
from syrin.providers import register_provider
register_provider("internal", InternalLLMProvider)

# Now use it
agent = Agent(model=model)
```

## Middleware: Transform Requests/Responses

Middleware lets you modify requests and responses without creating a new provider:

```python
from syrin import Model, Middleware
from syrin.types import Message, ProviderResponse

class MyMiddleware(Middleware):
    """Add logging and modify requests."""
    
    def transform_request(
        self,
        messages: list[Message],
        **kwargs,
    ) -> tuple[list[Message], dict]:
        print(f"Calling with {len(messages)} messages")
        
        # Add a system message
        messages = messages + [
            Message(role="system", content="Remember: be concise.")
        ]
        
        return messages, kwargs
    
    def transform_response(self, response: ProviderResponse) -> ProviderResponse:
        print(f"Response: {response.content[:100]}...")
        
        # Lowercase the response (example)
        if response.content:
            response.content = response.content.lower()
        
        return response

# Apply middleware
model = Model.OpenAI("gpt-4o-mini", api_key="...")
model = model.with_middleware(MyMiddleware())
```

### Middleware Use Cases

1. **Logging/Audit** — Log all requests and responses
2. **Content Filtering** — Scan responses for sensitive data
3. **Caching** — Cache responses for identical requests
4. **Rate Limiting** — Add client-side rate limiting
5. **Prompt Injection** — Inject system messages for safety/compliance

## Fallback Chains: Resilience Built-In

Configure automatic fallbacks when the primary model fails:

```python
primary = Model.OpenAI("gpt-4o", api_key="...")  # Best quality
secondary = Model.OpenAI("gpt-4o-mini", api_key="...")  # Fast fallback
tertiary = Model.Ollama("llama3")  # Local fallback

# Chain them together
model = primary.with_fallback(secondary, tertiary)

agent = Agent(model=model)
# If gpt-4o fails, tries gpt-4o-mini, then falls back to local Ollama
```

**Fallback triggers:**
- API errors (rate limits, server errors)
- Timeouts
- Custom exceptions

## Model Pricing: Budget Integration

For accurate budget tracking with custom models:

```python
from syrin import Model
from syrin.cost import ModelPricing

model = Model(
    model_id="my-internal-model",
    provider="internal",
    pricing=ModelPricing(
        input_per_1m=0.50,   # $0.50 per 1M input tokens
        output_per_1m=2.00,  # $2.00 per 1M output tokens
    ),
)

# Now budget tracking works correctly
agent = Agent(
    model=model,
    budget=Budget(max_cost=5.00),  # $5 limit
)
```

## Structured Output: Type-Safe Responses

Request JSON matching a Pydantic model:

```python
from pydantic import BaseModel
from syrin import Model

class WeatherResponse(BaseModel):
    city: str
    temperature: float
    condition: str


model = Model.OpenAI(
    "gpt-4o-mini",
    api_key="...",
).with_output(WeatherResponse)

# Agent returns parsed WeatherResponse
response = agent.run("What's the weather in Tokyo?")
result = response.parsed  # WeatherResponse instance
print(result.city, result.temperature, result.condition)
```

## Direct Model Usage: Without Agents

Use models directly for simple completions:

```python
from syrin import Model
from syrin.types import Message, MessageRole

model = Model.OpenAI("gpt-4o-mini", api_key="...")

# Sync
response = model.complete([
    Message(role=MessageRole.USER, content="Hello!"),
])
print(response.content)

# Async
response = await model.acomplete([
    Message(role=MessageRole.USER, content="Hello!"),
])

# Streaming
for chunk in model.complete(
    [Message(role=MessageRole.USER, content="Tell me a story.")],
    stream=True,
):
    print(chunk.content, end="", flush=True)
```

## Testing with Almock

Test without API calls using `Model.Almock()`:

```python
from syrin import Model, Agent

# Fast mock with no latency
mock = Model.Almock(
    latency_seconds=0.01,
    lorem_length=100,
)

# Test with different pricing tiers
cheap_mock = Model.Almock(pricing_tier="low")
expensive_mock = Model.Almock(pricing_tier="ultra_high")

agent = Agent(model=mock)
response = agent.run("Hello!")
print(f"Response: {response.content}")
print(f"Cost: ${response.cost}")  # Always 0 for Almock unless pricing tier set
```

**Almock options:**
```python
Model.Almock(
    response_mode="lorem",      # Lorem ipsum text
    custom_response="Hello!",    # Fixed response
    lorem_length=50,            # Length in chars
    latency_min=0.1,            # Min delay
    latency_max=0.5,             # Max delay
    pricing_tier="medium",      # low, medium, high, ultra_high
)
```

## Provider Interface Deep Dive

```python
class Provider(ABC):
    """Abstract base for all LLM providers."""
    
    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        model: ModelConfig,
        tools: list[ToolSpec] | None = None,
        **kwargs,
    ) -> ProviderResponse:
        """Run completion. Required method."""
        ...
    
    async def stream(
        self,
        messages: list[Message],
        model: ModelConfig,
        tools: list[ToolSpec] | None = None,
        **kwargs,
    ) -> AsyncIterator[ProviderResponse]:
        """Stream chunks. Default: yields single full response."""
        response = await self.complete(messages, model, tools, **kwargs)
        yield response
```

### ProviderResponse Structure

```python
@dataclass
class ProviderResponse:
    content: str | None           # Text response
    tool_calls: list[dict]        # [{"id": "...", "name": "...", "arguments": "..."}]
    token_usage: dict             # {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}
    stop_reason: str | None      # "stop", "length", "tool_calls", etc.
    raw_response: Any | None     # Original API response for debugging
```

## Registry: Dynamic Model Lookup

Register models for dynamic lookup:

```python
from syrin.model import ModelRegistry, Model

registry = ModelRegistry()
registry.register("gpt4", Model.OpenAI("gpt-4o", api_key="..."))
registry.register("claude", Model.Anthropic("claude-sonnet", api_key="..."))

# Later, look up by name
model = registry.get("gpt4")
```

**Use cases:**
- Config-driven model selection
- Feature flags for model rollout
- A/B testing

## Hooks for Model Observability

Track model usage with hooks:

```python
agent.events.on(Hook.LLM_REQUEST_START, lambda ctx: print(f"Calling {ctx.model_id}"))
agent.events.on(Hook.LLM_REQUEST_END, lambda ctx: print(f"Tokens: {ctx.tokens}"))
```

## Model Construction Helpers

The public model and embedding surface also includes:

- `ModelVariable` and `ModelVersion` for model metadata/versioning.
- `OutputType`, `StructuredOutput`, `create_model()`, and `make_model()` for programmatic model construction and output typing.
- `EmbeddingBackend`, `EmbeddingProvider`, `OpenAIEmbedding`, and `OllamaEmbedding` for embedding-specific integrations used by retrieval systems.

## What's Next?

- [Custom Context](/agent-kit/advanced/custom-context) — Custom context management strategies
- [Dependency Injection](/agent-kit/advanced/dependency-injection) — Testable agents with RunContext
- [Event Bus](/agent-kit/advanced/event-bus) — Domain events and handlers
- [Template Engine](/agent-kit/advanced/template-engine) — Structured generation

## See Also

- [Models Overview](/agent-kit/core/models) — Built-in model providers
- [Model Routing](/agent-kit/core/models-routing) — Dynamic model selection
- [Testing](/agent-kit/advanced/testing) — Mock models and tools
- [Middleware](/agent-kit/advanced/dependency-injection) — Request/response transformation
