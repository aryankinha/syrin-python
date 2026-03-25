"""Factory functions for creating models.

Usage:
    from syrin.model import create_model, make_model

    # Quick creation (pass api_key explicitly)
    model = create_model("openai", "gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

    # Create new LLM class
    KimiModel = make_model(
        name="Kimi",
        provider="kimi",
        default_model="kimi2.5",
        base_url="https://api.moonshot.cn/v1",
    )
    model = KimiModel(api_key=os.getenv("KIMI_API_KEY"))
"""

from __future__ import annotations

from syrin.model.core import Model


def create_model(
    provider: str,
    model_name: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    **kwargs: object,
) -> Model:
    """Create a model from provider and model name. Alternative to Model.OpenAI, etc.

    Use when the provider is dynamic (e.g., from config). For static usage, prefer
    Model.OpenAI("gpt-4o", ...) for better IDE support.

    Args:
        provider: openai, anthropic, ollama, google, or litellm.
        model_name: Model name (e.g., "gpt-4o", "claude-sonnet-4-5").
        api_key: API key. Required for most providers; pass explicitly.
        base_url: Optional base URL override.
        **kwargs: Additional Model parameters (temperature, max_tokens, etc.).

    Returns:
        Model instance.

    Example:
        model = create_model("openai", "gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
    """
    if not provider or not provider.strip():
        raise ValueError("Provider name cannot be empty")

    if not model_name or not model_name.strip():
        raise ValueError("Model name cannot be empty")

    provider = provider.strip().lower()

    if provider == "openai":
        from syrin.model.providers import OpenAI

        return OpenAI(model_name, api_key=api_key, base_url=base_url, **kwargs)  # type: ignore[arg-type]
    elif provider == "anthropic":
        from syrin.model.providers import Anthropic

        return Anthropic(model_name, api_key=api_key, base_url=base_url, **kwargs)  # type: ignore[arg-type]
    elif provider == "ollama":
        from syrin.model.providers import Ollama

        return Ollama(model_name, api_key=api_key, base_url=base_url, **kwargs)  # type: ignore[arg-type]
    elif provider == "google":
        from syrin.model.providers import Google

        return Google(model_name, api_key=api_key, base_url=base_url, **kwargs)  # type: ignore[arg-type]
    elif provider == "litellm":
        from syrin.model.providers import LiteLLM

        return LiteLLM(model_name, api_key=api_key, base_url=base_url, **kwargs)  # type: ignore[arg-type]
    else:
        return Model(
            model_id=f"{provider}/{model_name}",
            name=model_name,
            api_key=api_key,
            api_base=base_url,
            _internal=True,
            **kwargs,  # type: ignore[arg-type]
        )


def make_model(
    *,
    name: str,
    provider: str,
    default_model: str,
    base_url: str,
    context_window: int | None = None,
    **defaults: object,
) -> type[Model]:
    """Create a reusable Model subclass for an OpenAI-compatible API.

    Returns a class (e.g., KimiModel) that you instantiate with api_key. Use for
    third-party APIs when you want a named class instead of Model.Custom().

    Args:
        name: Human-readable name (e.g., "Kimi"). Becomes ``{name}Model``.
        provider: "openai" for OpenAI-compatible APIs, or "litellm".
        default_model: Default model name when called with no args.
        base_url: API base URL (e.g., https://api.moonshot.ai/v1).
        context_window: Default context window size.
        **defaults: Additional default Model parameters.

    Returns:
        A Model subclass. Instantiate with ``YourModel(api_key=...)``.

    Example:
        KimiModel = make_model(
            name="Kimi", provider="openai", default_model="moonshot-v1-8k",
            base_url="https://api.moonshot.ai/v1", context_window=8192,
        )
        model = KimiModel(api_key=os.getenv("MOONSHOT_API_KEY"))
    """
    if not name or not provider or not default_model or not base_url:
        raise ValueError("name, provider, default_model, and base_url are required")

    class CustomModel(Model):
        DEFAULT_PROVIDER = provider
        DEFAULT_BASE_URL = base_url
        DEFAULT_MODEL = default_model

        def __init__(
            self,
            model_name: str = default_model,
            *,
            api_key: str | None = None,
            base_url: str | None = None,
            **model_kwargs: object,
        ) -> None:
            super().__init__(
                model_id=f"{provider}/{model_name}",
                name=model_name,
                api_base=base_url or self.DEFAULT_BASE_URL,
                api_key=api_key,
                context_window=model_kwargs.pop("context_window", context_window),  # type: ignore[arg-type]
                _internal=True,
                **defaults,  # type: ignore[arg-type]
                **model_kwargs,  # type: ignore[arg-type]
            )

    CustomModel.__name__ = f"{name}Model"
    return CustomModel


__all__ = [
    "create_model",
    "make_model",
]
