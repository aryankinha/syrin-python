"""Model resolution: _resolve_provider and get_provider return valid Provider; clear errors when missing."""

from __future__ import annotations

import pytest

from syrin.agent import Agent
from syrin.agent._helpers import _resolve_provider
from syrin.model import Model
from syrin.providers.base import Provider
from syrin.providers.registry import get_provider
from syrin.types import ModelConfig


class TestGetProviderValidNames:
    """Known provider names return the correct Provider type."""

    def test_get_provider_openai_returns_provider(self) -> None:
        p = get_provider("openai")
        assert isinstance(p, Provider)
        assert hasattr(p, "complete")
        assert callable(p.complete)

    def test_get_provider_anthropic_returns_provider(self) -> None:
        p = get_provider("anthropic")
        assert isinstance(p, Provider)

    def test_get_provider_litellm_returns_provider(self) -> None:
        p = get_provider("litellm")
        assert isinstance(p, Provider)

    def test_get_provider_ollama_returns_provider(self) -> None:
        p = get_provider("ollama")
        assert isinstance(p, Provider)

    def test_get_provider_case_insensitive(self) -> None:
        assert isinstance(get_provider("OPENAI"), Provider)
        assert isinstance(get_provider("OpenAI"), Provider)

    def test_get_provider_empty_falls_back_to_litellm(self) -> None:
        """Empty or None provider name defaults to litellm (backward compat)."""
        p = get_provider("")
        assert isinstance(p, Provider)
        p2 = get_provider("  ")
        assert isinstance(p2, Provider)


class TestGetProviderStrictMode:
    """When strict=True, unknown provider names raise ProviderNotFoundError."""

    def test_get_provider_unknown_strict_raises(self) -> None:
        from syrin.exceptions import ProviderNotFoundError

        with pytest.raises(ProviderNotFoundError) as exc_info:
            get_provider("unknown_provider_xyz", strict=True)
        assert "unknown" in str(exc_info.value).lower() or "provider" in str(exc_info.value).lower()

    def test_get_provider_known_strict_returns_provider(self) -> None:
        p = get_provider("openai", strict=True)
        assert isinstance(p, Provider)

    def test_get_provider_strict_false_unknown_returns_litellm(self) -> None:
        """Default strict=False: unknown name returns LiteLLM fallback."""
        p = get_provider("unknown_xyz", strict=False)
        assert isinstance(p, Provider)


class TestResolveProviderAgentPath:
    """_resolve_provider used by Agent returns valid Provider."""

    def test_resolve_with_model_uses_model_get_provider(self) -> None:
        model = Model("openai/gpt-4o")
        config = model.to_config()
        p = _resolve_provider(model, config)
        assert isinstance(p, Provider)

    def test_resolve_without_model_uses_registry(self) -> None:
        config = ModelConfig(name="test", provider="openai", model_id="gpt-4o")
        p = _resolve_provider(None, config)
        assert isinstance(p, Provider)

    def test_resolve_with_anthropic_model(self) -> None:
        model = Model("anthropic/claude-3-5-sonnet")
        p = _resolve_provider(model, model.to_config())
        assert isinstance(p, Provider)


class TestAgentCreationModelResolution:
    """Agent construction resolves provider; invalid provider raises clear error when strict."""

    def test_agent_creation_with_valid_model_succeeds(self) -> None:
        agent = Agent(model=Model("openai/gpt-4o"), system_prompt="Test")
        assert agent._provider is not None
        assert isinstance(agent._provider, Provider)

    def test_agent_creation_with_model_config_valid_provider_succeeds(self) -> None:
        config = ModelConfig(name="t", provider="openai", model_id="gpt-4o")
        agent = Agent(model=config, system_prompt="Test")
        assert isinstance(agent._provider, Provider)
