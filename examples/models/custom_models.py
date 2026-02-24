"""Custom Model Examples - Creating and using models.

This file demonstrates different ways to create models and use them with Agent.
Run with: python -m examples.models.custom_models
"""

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

import syrin

# =============================================================================
# Organized Imports - By Category
# =============================================================================
# Core
# Structured Output
from syrin import Model
from syrin.types import Message, ProviderResponse

# Setup logging
logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)

# Load environment
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


# =============================================================================
# Example 1: Provider Namespaces (Simplest)
# =============================================================================


async def example_provider_namespaces():
    """Use provider namespaces - simplest approach."""
    print("\n" + "=" * 60)
    print("Example 1: Provider Namespaces")
    print("=" * 60)

    # OpenAI - pass api_key explicitly
    model = Model.OpenAI("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
    print(f"OpenAI: {model}")
    print(f"Provider: {model.provider}")

    # Anthropic
    model = Model.Anthropic("claude-sonnet-4-5", api_key=os.getenv("ANTHROPIC_API_KEY"))
    print(f"\nAnthropic: {model}")

    # Ollama
    model = Model.Ollama("llama3")
    print(f"\nOllama: {model}")

    # Google
    model = Model.Google("gemini-2.0-flash")
    print(f"\nGoogle: {model}")


# =============================================================================
# Example 2: Custom API Key and Base URL
# =============================================================================


async def example_custom_api():
    """Use custom API key and base URL."""
    print("\n" + "=" * 60)
    print("Example 2: Custom API Key and Base URL")
    print("=" * 60)

    # Custom API key and base URL - always pass api_key explicitly
    model = Model.OpenAI(
        "gpt-4o",
        api_key=os.getenv("OPENAI_API_KEY", "sk-custom-key"),
        api_base="https://custom.endpoint.com/v1",
    )
    print(f"Model: {model}")
    print(f"API Key: {model.api_key[:10]}...")
    print(f"API Base: {model.api_base}")


# =============================================================================
# Example 3: Custom Model via Inheritance
# =============================================================================


class MyCustomModel(Model):
    """Custom model adapter for any LLM API."""

    def __init__(self, model_name: str = "my-model", *, api_key: str | None = None, **kwargs):
        super().__init__(
            model_id=f"custom/{model_name}", provider="custom", api_key=api_key, **kwargs
        )
        self._api_key = api_key

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
        # Your custom implementation here!
        print(f"Custom model called with {len(messages)} messages")
        print(f"API Key: {(self.api_key or '')[:10] or 'None'}...")

        # Return a mock response for demo
        return ProviderResponse(
            content="Custom model response!",
            tool_calls=[],
        )

    async def acomplete(self, messages, **kwargs) -> ProviderResponse:
        return self.complete(messages, **kwargs)


async def example_custom_model():
    """Create custom model via inheritance."""
    print("\n" + "=" * 60)
    print("Example 3: Custom Model via Inheritance")
    print("=" * 60)

    model = MyCustomModel("my-custom-model", api_key=os.getenv("CUSTOM_API_KEY"))
    print(f"Custom model: {model}")
    print(f"Provider: {model.provider}")

    # Use with Agent
    agent = syrin.Agent(model=model, system_prompt="Say something unique.")
    response = await agent.arun("Say 'custom' in 1 word.")
    print(f"Response: {response.content}")


# =============================================================================
# Example 4: With Structured Output
# =============================================================================


from pydantic import BaseModel


class SentimentOutput(BaseModel):
    sentiment: str
    confidence: float


async def example_structured_output():
    """Use structured output for type-safe responses."""
    print("\n" + "=" * 60)
    print("Example 4: Structured Output")
    print("=" * 60)

    model = Model.OpenAI("gpt-4o-mini", output=SentimentOutput, api_key=os.getenv("OPENAI_API_KEY"))
    print(f"Model with output: {model}")
    print(f"Output type: {model.output_type}")


# =============================================================================
# Example 5: With Pricing
# =============================================================================


async def example_pricing():
    """Set custom pricing for models."""
    print("\n" + "=" * 60)
    print("Example 5: Custom Pricing")
    print("=" * 60)

    from syrin.cost import ModelPricing

    # Method 1: Using input_price/output_price
    model = Model.OpenAI(
        "gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
        input_price=0.20,
        output_price=0.80,
    )
    pricing = model.get_pricing()
    print(f"Simple pricing: ${pricing.input_per_1m}/1M in, ${pricing.output_per_1m}/1M out")

    # Method 2: Using ModelPricing object
    model = Model.OpenAI(
        "gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
        pricing=ModelPricing(input_per_1m=0.20, output_per_1m=0.80),
    )
    pricing = model.get_pricing()
    print(f"Pricing object: ${pricing.input_per_1m}/1M in, ${pricing.output_per_1m}/1M out")


# =============================================================================
# Main
# =============================================================================


async def main():
    await example_provider_namespaces()
    await example_custom_api()
    await example_custom_model()
    await example_structured_output()
    await example_pricing()


if __name__ == "__main__":
    asyncio.run(main())
