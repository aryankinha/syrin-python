"""Provider namespaces for easy model creation.

Usage:
    from syrin.model import Model

    model = Model.OpenAI("gpt-4o")
    model = Model.Anthropic("claude-sonnet-4-5")
    model = Model.Ollama("llama3")
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from syrin.model.core import Model


def _make_openai(
    model_name: str,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    max_output_tokens: int | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
    stop: list[str] | None = None,
    api_key: str | None = None,
    api_base: str | None = None,
    context_window: int | None = None,
    output: type | None = None,
    input_price: float | None = None,
    output_price: float | None = None,
    fallback: list[Model] | None = None,
    **kwargs: object,
) -> Model:
    """Create an OpenAI model.

    Usage:
        Model.OpenAI("gpt-4o")
        Model.OpenAI("gpt-4o", temperature=0.7)
        Model.OpenAI("gpt-4o", api_key="sk-...")

    Args:
        model_name: Model name (e.g., "gpt-4o", "gpt-4o-mini", "o1")
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Max output tokens
        max_output_tokens: Max output tokens
        top_p: Nucleus sampling
        top_k: Top-k sampling
        stop: Stop sequences
        api_key: API key (required; pass explicitly)
        api_base: Custom base URL
        context_window: Context window size
        output: Structured output type
        input_price: Input price per 1M tokens
        output_price: Output price per 1M tokens
        fallback: Fallback models
        **kwargs: Additional Model parameters

    Returns:
        Model instance
    """
    from syrin.model import Model

    return Model(
        model_id=f"openai/{model_name}",
        name=model_name,
        provider="openai",
        api_base=api_base or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1",
        api_key=api_key,
        context_window=context_window or 128000,
        temperature=temperature,
        max_tokens=max_tokens,
        max_output_tokens=max_output_tokens,
        top_p=top_p,
        top_k=top_k,
        stop=stop,
        output=output,
        input_price=input_price,
        output_price=output_price,
        fallback=fallback,
        **kwargs,  # type: ignore[arg-type]
    )


def _make_anthropic(
    model_name: str,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    max_output_tokens: int | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
    stop: list[str] | None = None,
    api_key: str | None = None,
    api_base: str | None = None,
    context_window: int | None = None,
    output: type | None = None,
    input_price: float | None = None,
    output_price: float | None = None,
    fallback: list[Model] | None = None,
    **kwargs: object,
) -> Model:
    """Create an Anthropic Claude model.

    Usage:
        Model.Anthropic("claude-sonnet-4-5")
        Model.Anthropic("claude-opus-4-5")

    Args:
        model_name: Model name (e.g., "claude-sonnet-4-5-20241022")
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Max output tokens
        api_key: API key (required; pass explicitly)
        api_base: Custom base URL
        context_window: Context window size
        output: Structured output type
        **kwargs: Additional Model parameters

    Returns:
        Model instance
    """
    from syrin.model import Model

    return Model(
        model_id=f"anthropic/{model_name}",
        name=model_name,
        provider="anthropic",
        api_base=api_base or os.getenv("ANTHROPIC_BASE_URL") or "https://api.anthropic.com",
        api_key=api_key,
        context_window=context_window or 200000,
        temperature=temperature,
        max_tokens=max_tokens,
        max_output_tokens=max_output_tokens,
        top_p=top_p,
        top_k=top_k,
        stop=stop,
        output=output,
        input_price=input_price,
        output_price=output_price,
        fallback=fallback,
        **kwargs,  # type: ignore[arg-type]
    )


def _make_ollama(
    model_name: str,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    max_output_tokens: int | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
    stop: list[str] | None = None,
    api_key: str | None = None,
    api_base: str | None = None,
    context_window: int | None = None,
    output: type | None = None,
    input_price: float | None = None,
    output_price: float | None = None,
    fallback: list[Model] | None = None,
    **kwargs: object,
) -> Model:
    """Create an Ollama (local) model.

    Usage:
        Model.Ollama("llama3")
        Model.Ollama("mistral")

    Args:
        model_name: Model name (e.g., "llama3", "mistral")
        api_base: Base URL (default: http://localhost:11434)
        **kwargs: Additional Model parameters

    Returns:
        Model instance
    """
    from syrin.model import Model

    return Model(
        model_id=f"ollama/{model_name}",
        name=model_name,
        provider="ollama",
        api_base=api_base or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434",
        api_key=api_key,
        context_window=context_window or 8192,
        temperature=temperature,
        max_tokens=max_tokens,
        max_output_tokens=max_output_tokens,
        top_p=top_p,
        top_k=top_k,
        stop=stop,
        output=output,
        input_price=input_price,
        output_price=output_price,
        fallback=fallback,
        **kwargs,  # type: ignore[arg-type]
    )


def _make_google(
    model_name: str,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    max_output_tokens: int | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
    stop: list[str] | None = None,
    api_key: str | None = None,
    api_base: str | None = None,
    context_window: int | None = None,
    output: type | None = None,
    input_price: float | None = None,
    output_price: float | None = None,
    fallback: list[Model] | None = None,
    **kwargs: object,
) -> Model:
    """Create a Google Gemini model.

    Usage:
        Model.Google("gemini-2.0-flash")
        Model.Google("gemini-1.5-pro")

    Args:
        model_name: Model name (e.g., "gemini-2.0-flash")
        temperature: Sampling temperature
        max_tokens: Max output tokens
        api_key: API key (required; pass explicitly)
        **kwargs: Additional Model parameters

    Returns:
        Model instance
    """
    from syrin.model import Model

    return Model(
        model_id=model_name,
        name=model_name,
        provider="google",
        api_base=api_base
        or os.getenv("GOOGLE_BASE_URL")
        or "https://generativelanguage.googleapis.com/v1beta",
        api_key=api_key,
        context_window=context_window or 1048576,
        temperature=temperature,
        max_tokens=max_tokens,
        max_output_tokens=max_output_tokens,
        top_p=top_p,
        top_k=top_k,
        stop=stop,
        output=output,
        input_price=input_price,
        output_price=output_price,
        fallback=fallback,
        **kwargs,  # type: ignore[arg-type]
    )


def _make_litellm(
    model_name: str,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    max_output_tokens: int | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
    stop: list[str] | None = None,
    api_key: str | None = None,
    api_base: str | None = None,
    context_window: int | None = None,
    output: type | None = None,
    input_price: float | None = None,
    output_price: float | None = None,
    fallback: list[Model] | None = None,
    **kwargs: object,
) -> Model:
    """Create a LiteLLM model (100+ providers).

    Usage:
        Model.LiteLLM("anthropic/claude-3-5-sonnet")
        Model.LiteLLM("openai/gpt-4o")

    Args:
        model_name: Full model ID (e.g., "anthropic/claude-3-5-sonnet")
        api_key: API key (required; pass explicitly)
        api_base: Custom base URL
        **kwargs: Additional Model parameters

    Returns:
        Model instance
    """
    from syrin.model import Model

    name = model_name.split("/")[-1] if "/" in model_name else model_name

    return Model(
        model_id=model_name,
        name=name,
        provider="litellm",
        api_base=api_base or os.getenv("LITELLM_BASE_URL") or "https://api.litellm.ai",
        api_key=api_key,
        context_window=context_window,
        temperature=temperature,
        max_tokens=max_tokens,
        max_output_tokens=max_output_tokens,
        top_p=top_p,
        top_k=top_k,
        stop=stop,
        output=output,
        input_price=input_price,
        output_price=output_price,
        fallback=fallback,
        **kwargs,  # type: ignore[arg-type]
    )


# Assign to module-level variables
OpenAI = _make_openai
Anthropic = _make_anthropic
Ollama = _make_ollama
Google = _make_google
LiteLLM = _make_litellm


def setup_provider_namespaces(model_class: type) -> None:
    """Add provider namespaces to Model class."""
    model_class.OpenAI = OpenAI  # type: ignore[attr-defined]
    model_class.Anthropic = Anthropic  # type: ignore[attr-defined]
    model_class.Ollama = Ollama  # type: ignore[attr-defined]
    model_class.Google = Google  # type: ignore[attr-defined]
    model_class.LiteLLM = LiteLLM  # type: ignore[attr-defined]


__all__ = [
    "OpenAI",
    "Anthropic",
    "Ollama",
    "Google",
    "LiteLLM",
    "setup_provider_namespaces",
]
