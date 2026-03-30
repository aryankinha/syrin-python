"""Top-level convenience helpers exposed from the ``syrin`` package."""

from __future__ import annotations

from syrin.budget import Budget
from syrin.config import get_config
from syrin.model import Model
from syrin.response import Response
from syrin.tool import ToolSpec


def run(
    input: str,
    model: str | Model | None = None,
    *,
    system_prompt: str | None = None,
    tools: list[ToolSpec] | None = None,
    budget: Budget | None = None,
    template_variables: dict[str, object] | None = None,
    **kwargs: object,
) -> Response[str]:
    """Run a one-shot completion with an agent.

    This is a convenience function for simple one-off LLM calls without
    needing to create an ``Agent`` instance.
    """
    from syrin.agent import Agent
    from syrin.model.core import Model as ModelClass
    from syrin.model.core import detect_provider

    if model is None:
        config = get_config()
        default = config.default_model
        if default is not None:
            model_obj = ModelClass(provider=default.provider, model_id=default.model_id)
        else:
            model_obj = ModelClass(provider="litellm", model_id="gpt-4o")
    elif isinstance(model, str):
        import os

        provider = detect_provider(model)
        api_key = None
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY") or get_config().default_api_key
        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY") or get_config().default_api_key
        elif provider == "google":
            api_key = os.getenv("GOOGLE_API_KEY") or get_config().default_api_key
        else:
            api_key = get_config().default_api_key or os.getenv("OPENAI_API_KEY")
        model_obj = ModelClass(provider=provider, model_id=model, api_key=api_key)
    else:
        model_obj = model

    agent = Agent(
        model=model_obj,
        system_prompt=system_prompt or "",
        tools=tools or [],
        budget=budget,
        **kwargs,  # type: ignore[arg-type]
    )
    return agent.run(input, template_variables=template_variables)
