"""OpenRouterBuilder — create multiple OpenRouter models with a single API key."""

from __future__ import annotations

from typing import Any

from syrin.model import Model


class OpenRouterBuilder:
    """Builder for creating multiple OpenRouter models with one API key.

    Use when routing between models via OpenRouter. Pass the API key once,
    then create models by ID.

    Example:
        builder = OpenRouterBuilder(api_key="sk-or-...")
        claude = builder.model("anthropic/claude-sonnet-4-5")
        gpt = builder.model("openai/gpt-4o-mini")
        agent = Agent(model=[claude, gpt], model_router=RoutingConfig(...))
    """

    def __init__(self, api_key: str) -> None:
        """Create builder with OpenRouter API key.

        Args:
            api_key: OpenRouter API key. Required for all models from this builder.
        """
        if not api_key or not str(api_key).strip():
            raise ValueError(
                "OpenRouterBuilder requires api_key. Use OpenRouterBuilder(api_key='sk-or-...')"
            )
        self._api_key = api_key.strip()

    def model(
        self,
        model_id: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        max_output_tokens: int | None = None,
        top_p: float | None = None,
        stop: list[str] | None = None,
        context_window: int | None = None,
        output: type | None = None,
        input_price: float | None = None,
        output_price: float | None = None,
        **kwargs: Any,
    ) -> Model:
        """Create an OpenRouter Model with this builder's API key.

        Args:
            model_id: Full OpenRouter model ID (e.g. "anthropic/claude-sonnet-4-5").

        Returns:
            Model instance configured for OpenRouter.
        """
        return Model.OpenRouter(
            model_id=model_id,
            api_key=self._api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            max_output_tokens=max_output_tokens,
            top_p=top_p,
            stop=stop,
            context_window=context_window,
            output=output,
            input_price=input_price,
            output_price=output_price,
            **kwargs,
        )
