"""Model configuration: ModelSettings removal and flat kwargs API.

ModelSettings is removed from the public API. Settings are now passed as flat kwargs
directly to Model.OpenAI(...), Model.Anthropic(...), etc.
"""

from __future__ import annotations

# =============================================================================
# ModelSettings not publicly exported
# =============================================================================


def test_model_settings_not_in_syrin_root() -> None:
    """ModelSettings must not be importable from syrin root."""
    import syrin

    assert not hasattr(syrin, "ModelSettings"), (
        "ModelSettings should be removed from syrin public API"
    )


def test_model_settings_not_in_syrin_model() -> None:
    """ModelSettings must not be importable from syrin.model."""
    import syrin.model

    assert not hasattr(syrin.model, "ModelSettings"), (
        "ModelSettings should be removed from syrin.model"
    )


def test_model_settings_not_in_model_all() -> None:
    """ModelSettings not in syrin.model.__all__."""
    import syrin.model

    assert "ModelSettings" not in syrin.model.__all__


def test_model_settings_not_in_syrin_all() -> None:
    """ModelSettings not in syrin.__all__."""
    import syrin

    assert "ModelSettings" not in syrin.__all__


# =============================================================================
# Flat params on Model factory methods
# =============================================================================


def test_openai_flat_temperature() -> None:
    """Model.OpenAI accepts temperature as flat kwarg."""
    from syrin.model import Model

    m = Model.OpenAI("gpt-4o", temperature=0.7)
    assert m.settings.temperature == 0.7


def test_openai_flat_max_tokens() -> None:
    """Model.OpenAI accepts max_tokens as flat kwarg."""
    from syrin.model import Model

    m = Model.OpenAI("gpt-4o", max_tokens=2048)
    assert m.settings.max_output_tokens == 2048


def test_openai_flat_top_p() -> None:
    """Model.OpenAI accepts top_p as flat kwarg."""
    from syrin.model import Model

    m = Model.OpenAI("gpt-4o", top_p=0.9)
    assert m.settings.top_p == 0.9


def test_openai_flat_context_window() -> None:
    """Model.OpenAI accepts context_window as flat kwarg."""
    from syrin.model import Model

    m = Model.OpenAI("gpt-4o", context_window=32000)
    assert m.settings.context_window == 32000


def test_anthropic_flat_temperature() -> None:
    """Model.Anthropic accepts temperature as flat kwarg."""
    from syrin.model import Model

    m = Model.Anthropic("claude-sonnet-4-5", temperature=0.3)
    assert m.settings.temperature == 0.3


def test_google_flat_temperature() -> None:
    """Model.Google accepts temperature as flat kwarg."""
    from syrin.model import Model

    m = Model.Google("gemini-2.0-flash", temperature=0.5)
    assert m.settings.temperature == 0.5


def test_ollama_flat_temperature() -> None:
    """Model.Ollama accepts temperature as flat kwarg."""
    from syrin.model import Model

    m = Model.Ollama("llama3", temperature=0.8)
    assert m.settings.temperature == 0.8


# =============================================================================
# model.settings property still works for introspection
# =============================================================================


def test_model_settings_property_accessible() -> None:
    """model.settings property is still accessible for introspection."""
    from syrin.model import Model

    m = Model.OpenAI("gpt-4o", temperature=0.5, max_tokens=1024, top_p=0.9)
    s = m.settings
    assert s.temperature == 0.5
    assert s.max_output_tokens == 1024
    assert s.top_p == 0.9


def test_model_settings_defaults_are_none() -> None:
    """Unset settings default to None."""
    from syrin.model import Model

    m = Model.OpenAI("gpt-4o")
    assert m.settings.temperature is None
    assert m.settings.top_p is None
    assert m.settings.top_k is None


def test_model_settings_stop_sequences() -> None:
    """Model accepts stop= as flat kwarg."""
    from syrin.model import Model

    m = Model.OpenAI("gpt-4o", stop=["END", "STOP"])
    assert m.settings.stop == ["END", "STOP"]


# =============================================================================
# Direct Model() constructor also accepts flat params
# =============================================================================


def test_model_direct_constructor_flat_params() -> None:
    """Model() constructor accepts flat settings params."""
    from syrin.model import Model

    m = Model(model_id="openai/gpt-4o", temperature=0.6, max_tokens=512)
    assert m.settings.temperature == 0.6
    assert m.settings.max_output_tokens == 512


def test_model_settings_all_flat_fields() -> None:
    """All ModelSettings fields accepted as flat kwargs on Model."""
    from syrin.model import Model

    m = Model.OpenAI(
        "gpt-4o",
        temperature=1.0,
        max_tokens=4096,
        top_p=0.95,
        top_k=50,
        stop=["<|end|>"],
        context_window=64000,
    )
    s = m.settings
    assert s.temperature == 1.0
    assert s.max_output_tokens == 4096
    assert s.top_p == 0.95
    assert s.top_k == 50
    assert s.stop == ["<|end|>"]
    assert s.context_window == 64000
