---
title: Custom Models
description: Create your own model providers for any LLM
weight: 12
---

## New Models Drop Every Week. Can Your Code Keep Up?

A new AI model just launched. It's faster, cheaper, and better at exactly what you need.

The old way: Wait for library updates, hope they support it, deal with breaking changes.

**The Syrin way:** Your code already supports it. One line, done.

That's the power of custom models. Syrin gives developers a structured way to integrate any AI model—today, tomorrow, whenever the next big thing drops.

---

## Why Custom Models?

Let's be real. You're a developer. You don't want to be locked into whatever the library maintainers decide to support.

Here's the situation:

- **New models launch constantly** — Mistral, DeepSeek, Grok, KIMI, and hundreds more
- **Each has unique strengths** — Different pricing, capabilities, and limitations
- **Vendor lock-in hurts** — What if OpenAI changes their pricing? What if Anthropic goes down?

Syrin's custom model system gives you **freedom**. If you can call an API, you can use that model in Syrin.

---

## Two Paths to Custom Models

Depending on your API, you have two options:

| API Type | Use This | When |
|----------|----------|-------|
| **OpenAI-Compatible** | `Model.Custom()` | API follows OpenAI's format |
| **Anything Else** | Extend `Model` class | Custom protocols, weird APIs |

### Path 1: OpenAI-Compatible APIs (The Easy Way)

Many AI providers use OpenAI's API format. If the API looks like OpenAI, just point Syrin to it:

```python
from syrin import Model

# DeepSeek - OpenAI-compatible
model = Model.Custom(
    "deepseek-chat",
    api_base="https://api.deepseek.com/v1",
    api_key="your-deepseek-key"
)

# Grok (xAI) - OpenAI-compatible
model = Model.Custom(
    "grok-3",
    api_base="https://api.x.ai/v1",
    api_key="your-xai-key"
)

# KIMI (Moonshot) - OpenAI-compatible
model = Model.Custom(
    "moonshot-v1-8k",
    api_base="https://api.moonshot.ai/v1",
    api_key="your-moonshot-key"
)
```

**That's it.** Just provide the endpoint and API key. Syrin handles the rest.

### Adding Settings

Treat it like any other model:

```python
model = Model.Custom(
    "deepseek-chat",
    api_base="https://api.deepseek.com/v1",
    api_key="your-key",
    temperature=0.7,
    max_tokens=2048,
    context_window=128000,
    input_price=0.14,    # $0.14 per 1M input tokens
    output_price=2.19,   # $2.19 per 1M output tokens
)
```

---

## Path 2: Extending the Model Class (The Powerful Way)

Sometimes the API doesn't follow any standard. Maybe it's WebSocket-based, uses a custom auth flow, or has weird quirks.

That's when you extend the `Model` class.

### Your First Custom Model

Here's a minimal custom model:

```python
from syrin import Model
from syrin.types import Message, ProviderResponse, TokenUsage

class MyModel(Model):
    """My custom AI model."""
    
    def complete(
        self,
        messages: list[Message],
        **kwargs
    ) -> ProviderResponse:
        # Your magic here
        response_text = "Hello from my custom model!"
        
        return ProviderResponse(
            content=response_text,
            token_usage=TokenUsage(
                input_tokens=100,
                output_tokens=10,
                total_tokens=110
            ),
            stop_reason="end_turn"
        )
```

**Use it like any other model:**

```python
model = MyModel("my-model")

# With an agent
class MyAgent(Agent):
    model = MyModel("my-model")
    system_prompt = "You are helpful."

agent = MyAgent()
response = agent.run("Hello!")
```

---

## A Real-World Custom Model

Let's build something that actually calls an API:

```python
import requests
from syrin import Model
from syrin.types import Message, ProviderResponse, TokenUsage

class HuggingFaceModel(Model):
    """Custom model for Hugging Face Inference API."""
    
    def __init__(self, model_name: str, api_token: str, **kwargs):
        # Initialize the parent
        super().__init__(
            model_id=f"huggingface/{model_name}",
            name=model_name,
            provider="huggingface",
            **kwargs
        )
        self._api_token = api_token
        self._api_url = f"https://api-inference.huggingface.co/models/{model_name}"
    
    def complete(
        self,
        messages: list[Message],
        **kwargs
    ) -> ProviderResponse:
        # Convert messages to prompt
        prompt = self._format_messages(messages)
        
        # Call Hugging Face API
        response = requests.post(
            self._api_url,
            headers={"Authorization": f"Bearer {self._api_token}"},
            json={
                "inputs": prompt,
                "parameters": {
                    "temperature": kwargs.get("temperature", self.settings.temperature or 0.7),
                    "max_new_tokens": kwargs.get("max_tokens", self.settings.max_output_tokens or 256),
                }
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        # Extract response
        if isinstance(data, list):
            text = data[0].get("generated_text", "")
        else:
            text = data.get("generated_text", "")
        
        # Estimate tokens (simple approximation)
        input_tokens = len(prompt) // 4
        output_tokens = len(text) // 4
        
        return ProviderResponse(
            content=text,
            token_usage=TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens
            ),
            stop_reason="end_turn",
            raw_response=data
        )
    
    def _format_messages(self, messages: list[Message]) -> str:
        """Convert messages to a single prompt string."""
        formatted = []
        for msg in messages:
            role = msg.role.value if hasattr(msg.role, 'value') else str(msg.role)
            formatted.append(f"{role}: {msg.content}")
        return "\n".join(formatted)
```

**Use it:**

```python
model = HuggingFaceModel(
    "mistralai/Mistral-7B-Instruct-v0.2",
    api_token="hf_your_token",
    temperature=0.7
)

agent = MyAgent(model=model)
response = agent.run("Explain quantum computing")
```

---

## Adding Cost Tracking

Your custom model should track costs. Syrin makes this easy:

```python
from syrin import Model, ModelPricing
from syrin.types import Message, ProviderResponse, TokenUsage

class MyModel(Model):
    def __init__(self, model_id: str, input_price: float, output_price: float, **kwargs):
        super().__init__(
            model_id=model_id,
            pricing=ModelPricing(
                input_per_1m=input_price,
                output_per_1m=output_price
            ),
            **kwargs
        )
        # ... rest of init
```

**Now Syrin tracks costs automatically:**

```python
model = MyModel(
    "my-model",
    input_price=0.10,   # $0.10 per 1M tokens
    output_price=0.40   # $0.40 per 1M tokens
)

response = model.complete(messages)
print(f"This call cost: ${response.cost:.6f}")
```

---

## Complete Custom Model Template

Here's a full template you can copy:

```python
from syrin import Model, ModelPricing
from syrin.types import Message, ProviderResponse, TokenUsage

class YourCustomModel(Model):
    """Your custom AI model integration."""
    
    def __init__(
        self,
        model_name: str,
        api_key: str,
        api_base: str = "https://api.example.com",
        input_price: float = 0.0,
        output_price: float = 0.0,
        **kwargs
    ):
        super().__init__(
            model_id=f"custom/{model_name}",
            name=model_name,
            provider="custom",
            api_base=api_base,
            api_key=api_key,
            context_window=8192,
            pricing=ModelPricing(
                input_per_1m=input_price,
                output_per_1m=output_price
            ),
            **kwargs
        )
        self._api_key = api_key
        self._api_base = api_base
    
    def complete(
        self,
        messages: list[Message],
        **kwargs
    ) -> ProviderResponse:
        # 1. Prepare request
        payload = self._build_payload(messages, **kwargs)
        
        # 2. Make API call
        response = self._call_api(payload)
        
        # 3. Parse response
        return self._parse_response(response)
    
    def _build_payload(self, messages: list[Message], **kwargs) -> dict:
        """Build the API request payload."""
        # Convert messages to your API format
        formatted_messages = [self._format_message(m) for m in messages]
        
        return {
            "messages": formatted_messages,
            "temperature": kwargs.get("temperature", self.settings.temperature or 0.7),
            "max_tokens": kwargs.get("max_tokens", self.settings.max_output_tokens or 256),
        }
    
    def _format_message(self, message: Message) -> dict:
        """Format a single message for your API."""
        return {
            "role": str(message.role.value),
            "content": message.content
        }
    
    def _call_api(self, payload: dict) -> dict:
        """Make the API call. Implement your HTTP logic here."""
        import requests
        
        response = requests.post(
            f"{self._api_base}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def _parse_response(self, response: dict) -> ProviderResponse:
        """Parse the API response into ProviderResponse."""
        choice = response["choices"][0]
        message = choice["message"]
        usage = response["usage"]
        
        return ProviderResponse(
            content=message.get("content", ""),
            token_usage=TokenUsage(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0)
            ),
            stop_reason=choice.get("finish_reason", "end_turn"),
            raw_response=response
        )
```

---

## Testing Your Custom Model

Use `Almock` for testing without hitting APIs:

```python
# Replace your custom model with Almock during testing
model = Model.Almock(
    latency_min=0.1,
    latency_max=0.3,
    lorem_length=100
)

# Now run your tests
agent = MyAgent(model=model)
response = agent.run("Test message")
```

---

## Fallback Chains

What if your custom model goes down? Add fallbacks:

```python
primary = YourCustomModel("gpt-4", api_key="...")
fallback = YourCustomModel("claude", api_key="...")

model = primary.with_fallback(fallback)

# If primary fails, fallback kicks in automatically
agent = MyAgent(model=model)
```

---

## Pricing Reference for Custom Models

When setting up cost tracking, here's a quick reference:

| Model Tier | Input Price ($/1M) | Output Price ($/1M) |
|-----------|-------------------|---------------------|
| **Budget** | \$0.10 - \$0.50 | \$0.30 - \$2.00 |
| **Mid-range** | \$0.50 - \$2.00 | \$2.00 - \$15.00 |
| **Premium** | \$2.00 - \$15.00 | \$15.00 - \$75.00 |
| **Experimental** | Negotiated | Negotiated |

**Tip:** Check the provider's pricing page. Most list it as "\$X per 1M tokens".

---

## What's Next?

- [Providers Overview](/core/models-providers) - All built-in providers
- [Model Routing](/core/models-routing) - Automatically switch between models
- [Budget](/core/budget) - Control spending across models

## See Also

- [Tools](/agent/tools) - Give your custom model abilities
- [Prompts](/core/prompts) - Get the best from your model
- [Structured Output](/agent/structured-output) - Get typed responses
