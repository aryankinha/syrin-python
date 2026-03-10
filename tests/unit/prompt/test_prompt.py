"""Tests for prompt system (prompt.py) - Native Python f-string prompts."""

from __future__ import annotations

import pytest

from syrin.prompt import PromptVersion, prompt, validated


def test_prompt_basic() -> None:
    """Test basic prompt with f-string."""

    @prompt
    def greet(name: str) -> str:
        return f"Hello, {name}!"

    result = greet(name="World")
    assert result == "Hello, World!"


def test_prompt_with_defaults() -> None:
    """Test prompt with default parameters."""

    @prompt
    def system_prompt(domain: str = "general", tone: str = "professional") -> str:
        return f"You are an expert in {domain}. Be {tone}."

    # Test with defaults
    result = system_prompt()
    assert result == "You are an expert in general. Be professional."

    # Test with overrides
    result = system_prompt(domain="AI", tone="friendly")
    assert result == "You are an expert in AI. Be friendly."


def test_prompt_metadata() -> None:
    """Test prompt metadata access."""

    @prompt
    def expert_prompt(domain: str) -> str:
        """Expert system prompt."""
        return f"You are a {domain} expert."

    assert expert_prompt.name == "expert_prompt"
    assert expert_prompt.description == "Expert system prompt."
    assert len(expert_prompt.variables) == 1
    assert expert_prompt.variables[0].name == "domain"
    assert expert_prompt.variables[0].type_hint is str


def test_prompt_string_annotations_safe_types() -> None:
    """String annotations str, int, float, bool resolved via safe dict (no eval)."""

    @prompt
    def typed_prompt(a: str, b: int, c: float, d: bool) -> str:
        return f"{a} {b} {c} {d}"

    assert typed_prompt.variables[0].type_hint is str
    assert typed_prompt.variables[1].type_hint is int
    assert typed_prompt.variables[2].type_hint is float
    assert typed_prompt.variables[3].type_hint is bool


def test_prompt_validation() -> None:
    """Test prompt parameter validation."""

    @prompt
    def config_prompt(temperature: float = 0.7) -> str:
        return f"Temperature: {temperature}"

    # Valid float
    result = config_prompt(temperature=0.5)
    assert result == "Temperature: 0.5"

    # String that can be converted to float
    result = config_prompt(temperature="0.8")
    assert result == "Temperature: 0.8"


def test_prompt_validate_method() -> None:
    """Test explicit validation without rendering."""

    @prompt
    def test_prompt(value: str) -> str:
        return f"Value: {value}"

    # Should pass
    assert test_prompt.validate(value="test") is True

    # Should fail - missing required param
    with pytest.raises(ValueError, match="Required parameter"):
        test_prompt.validate()


def test_prompt_caching() -> None:
    """Test prompt caching."""
    call_count = 0

    @prompt
    def cached_prompt(name: str) -> str:
        nonlocal call_count
        call_count += 1
        return f"Hello, {name}!"

    # First call
    result1 = cached_prompt(name="World")
    assert result1 == "Hello, World!"
    assert call_count == 1

    # Second call (should use cache)
    result2 = cached_prompt(name="World")
    assert result2 == "Hello, World!"
    assert call_count == 1  # Not incremented

    # Different parameter (new cache entry)
    result3 = cached_prompt(name="Syrin")
    assert result3 == "Hello, Syrin!"
    assert call_count == 2

    # Check cache stats
    stats = cached_prompt.get_cache_stats()
    assert stats["size"] == 2


def test_prompt_partial() -> None:
    """Test partial application of prompts."""

    @prompt
    def full_prompt(domain: str, tone: str, style: str) -> str:
        return f"Domain: {domain}, Tone: {tone}, Style: {style}"

    # Create partial prompt
    base_prompt = full_prompt.partial(domain="AI")
    result = base_prompt(tone="friendly", style="concise")
    assert result == "Domain: AI, Tone: friendly, Style: concise"


def test_prompt_compose() -> None:
    """Test prompt composition."""

    @prompt
    def system_prompt(domain: str) -> str:
        return f"You are a {domain} expert."

    @prompt
    def guidelines() -> str:
        return "Always be helpful and accurate."

    @prompt
    def safety() -> str:
        return "Never generate harmful content."

    # Compose prompts
    full_prompt = system_prompt.compose(guidelines, safety)
    result = full_prompt(domain="AI")

    assert "You are a AI expert." in result
    assert "Always be helpful and accurate." in result
    assert "Never generate harmful content." in result


def test_prompt_version() -> None:
    """Test prompt versioning."""

    @prompt(version=PromptVersion(2, 1, 0))
    def versioned_prompt(name: str) -> str:
        return f"Hello, {name}!"

    assert str(versioned_prompt.version) == "2.1.0"

    # Test version bumping
    new_version = versioned_prompt.version.bump_minor()
    assert str(new_version) == "2.2.0"


def test_prompt_test_render() -> None:
    """Test prompt test_render method."""

    @prompt
    def test_prompt(name: str) -> str:
        return f"Hello, {name}! Welcome to the system."

    result = test_prompt.test_render(name="World")

    assert result["output"] == "Hello, World! Welcome to the system."
    assert result["length"] == 36
    assert result["estimated_tokens"] == 36 // 4
    assert result["parameters"] == {"name": "World"}
    assert "version" in result
    assert "hash" in result


def test_validated_decorator() -> None:
    """Test validated decorator."""

    @validated(min_length=3, max_length=10)
    def name_prompt(name: str) -> str:
        return f"Hello, {name}!"

    # Valid
    result = name_prompt(name="John")
    assert result == "Hello, John!"

    # Too short
    with pytest.raises(ValueError, match="at least 3 characters"):
        name_prompt(name="Jo")

    # Too long
    with pytest.raises(ValueError, match="at most 10 characters"):
        name_prompt(name="JonathanLongName")


def test_prompt_repr() -> None:
    """Test prompt string representation."""

    @prompt
    def my_prompt(value: str) -> str:
        return f"Value: {value}"

    repr_str = repr(my_prompt)
    assert "Prompt" in repr_str
    assert "my_prompt" in repr_str
    assert "variables=1" in repr_str


# =============================================================================
# PROMPT EDGE CASES - TRY TO BREAK FUNCTIONALITY
# =============================================================================


def test_prompt_with_empty_string() -> None:
    """Prompt with empty string parameter."""

    @prompt
    def empty_prompt(value: str) -> str:
        return f"Value: {value}"

    result = empty_prompt(value="")
    assert result == "Value: "


def test_prompt_with_unicode() -> None:
    """Prompt with unicode characters."""

    @prompt
    def unicode_prompt(text: str) -> str:
        return f"Text: {text}"

    result = unicode_prompt(text="Hello 🌍 你好 🔥")
    assert "🌍" in result


def test_prompt_with_very_long_string() -> None:
    """Prompt with very long string."""

    @prompt
    def long_prompt(text: str) -> str:
        return f"Text: {text[:100]}"

    long_text = "x" * 10000
    result = long_prompt(text=long_text)
    assert len(result) == 106  # "Text: " + 100 chars


def test_prompt_with_special_characters() -> None:
    """Prompt with special characters."""

    @prompt
    def special_prompt(text: str) -> str:
        return f"Text: {text}"

    special = "!@#$%^&*()\n\t\r\"'"
    result = special_prompt(text=special)
    assert "!" in result


def test_prompt_with_numbers() -> None:
    """Prompt with numeric parameters."""

    @prompt
    def calc_prompt(a: int, b: int) -> str:
        return f"{a} + {b} = {a + b}"

    result = calc_prompt(a=5, b=3)
    assert result == "5 + 3 = 8"


def test_prompt_with_floats() -> None:
    """Prompt with float parameters."""

    @prompt
    def float_prompt(value: float) -> str:
        return f"Value: {value:.2f}"

    result = float_prompt(value=3.14159)
    assert result == "Value: 3.14"


def test_prompt_with_booleans() -> None:
    """Prompt with boolean parameters."""

    @prompt
    def bool_prompt(enabled: bool) -> str:
        return f"Enabled: {enabled}"

    assert bool_prompt(enabled=True) == "Enabled: True"
    assert bool_prompt(enabled=False) == "Enabled: False"


def test_prompt_with_lists() -> None:
    """Prompt with list parameters - lists are not hashable so may fail with caching."""

    @prompt
    def list_prompt(items: list) -> str:
        return f"Items: {len(items)}"

    # Lists are not hashable - this tests the edge case
    try:
        result = list_prompt(items=[1, 2, 3])
        assert "Items: 3" in result
    except TypeError:
        # Expected - lists not hashable for caching
        pass


def test_prompt_with_dicts() -> None:
    """Prompt with dict parameters - dicts are not hashable so may fail with caching."""

    @prompt
    def dict_prompt(data: dict) -> str:
        return f"Keys: {len(data)}"

    # Dicts are not hashable - this tests the edge case
    try:
        result = dict_prompt(data={"key": "value"})
        assert "Keys: 1" in result
    except TypeError:
        # Expected - dicts not hashable for caching
        pass


def test_prompt_no_parameters() -> None:
    """Prompt with no parameters."""

    @prompt
    def static_prompt() -> str:
        return "Static message"

    result = static_prompt()
    assert result == "Static message"


def test_prompt_many_parameters() -> None:
    """Prompt with many parameters."""

    @prompt
    def many_prompt(a: str, b: str, c: str, d: str, e: str) -> str:
        return f"{a} {b} {c} {d} {e}"

    result = many_prompt(a="1", b="2", c="3", d="4", e="5")
    assert result == "1 2 3 4 5"


def test_prompt_cache_clear() -> None:
    """Test prompt cache clearing."""

    @prompt
    def cache_test(name: str) -> str:
        return f"Hello, {name}!"

    cache_test(name="World")
    cache_test(name="Syrin")

    stats = cache_test.get_cache_stats()
    assert stats["size"] == 2

    cache_test.clear_cache()
    stats = cache_test.get_cache_stats()
    assert stats["size"] == 0


def test_prompt_validate_custom() -> None:
    """Test custom validation - basic validation only."""

    @prompt
    def custom_prompt(value: int) -> str:
        return f"Value: {value}"

    # Should pass
    assert custom_prompt.validate(value=5) is True

    # No custom validation is applied by default
    # This tests the edge case
    assert custom_prompt.validate(value=-1) is True
