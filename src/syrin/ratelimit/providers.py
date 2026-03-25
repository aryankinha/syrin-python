"""Provider rate limit presets and auto-detection.

This module provides:
- Known rate limit presets for major LLM providers
- Auto-detection of limits based on model/provider
- Integration with APIRateLimit for automatic configuration
"""

from dataclasses import dataclass


@dataclass
class ProviderRateLimits:
    """Known rate limits for LLM providers.

    These are typical limits - actual limits vary by tier/organization.
    Use auto_detect_limits() for accurate limits or configure manually.
    """

    provider: str
    model_pattern: str  # e.g., "gpt-4*", "claude-3*"
    rpm: int | None
    tpm: int | None
    rpd: int | None


# Known provider rate limits (typical values for tier 1)
# These are conservative defaults - users should verify their actual limits
KNOWN_PROVIDER_LIMITS = [
    # OpenAI
    ProviderRateLimits(provider="openai", model_pattern="gpt-4*", rpm=500, tpm=150000, rpd=None),
    ProviderRateLimits(provider="openai", model_pattern="gpt-3.5*", rpm=3500, tpm=90000, rpd=None),
    ProviderRateLimits(provider="openai", model_pattern="o1*", rpm=500, tpm=2000000, rpd=None),
    # Anthropic
    ProviderRateLimits(
        provider="anthropic", model_pattern="claude-3-5*", rpm=500, tpm=200000, rpd=None
    ),
    ProviderRateLimits(
        provider="anthropic", model_pattern="claude-3*", rpm=500, tpm=200000, rpd=None
    ),
    ProviderRateLimits(
        provider="anthropic", model_pattern="claude-2*", rpm=500, tpm=200000, rpd=None
    ),
    # Google
    ProviderRateLimits(
        provider="google", model_pattern="gemini-2*", rpm=2000, tpm=4000000, rpd=None
    ),
    ProviderRateLimits(
        provider="google", model_pattern="gemini-1.5*", rpm=2000, tpm=4000000, rpd=None
    ),
    # Groq
    ProviderRateLimits(provider="groq", model_pattern="*", rpm=30, tpm=6000, rpd=None),
    # Azure OpenAI
    ProviderRateLimits(provider="azure", model_pattern="gpt-4*", rpm=500, tpm=150000, rpd=None),
    ProviderRateLimits(provider="azure", model_pattern="gpt-35*", rpm=3500, tpm=90000, rpd=None),
    # Cohere
    ProviderRateLimits(provider="cohere", model_pattern="*", rpm=1000, tpm=500000, rpd=None),
    # Mistral
    ProviderRateLimits(provider="mistral", model_pattern="*", rpm=300, tpm=300000, rpd=None),
    # Together AI
    ProviderRateLimits(provider="together", model_pattern="*", rpm=3000, tpm=1000000, rpd=None),
    # Fireworks AI
    ProviderRateLimits(provider="fireworks", model_pattern="*", rpm=1000, tpm=1000000, rpd=None),
    # Perplexity
    ProviderRateLimits(provider="perplexity", model_pattern="*", rpm=500, tpm=500000, rpd=None),
    # Ollama (local - no rate limits)
    ProviderRateLimits(provider="ollama", model_pattern="*", rpm=None, tpm=None, rpd=None),
    # LiteLLM proxy (defaults)
    ProviderRateLimits(provider="litellm", model_pattern="*", rpm=1000, tpm=1000000, rpd=None),
]


def extract_provider_from_model(model_id: str) -> tuple[str, str]:
    """Extract provider and model pattern from model ID.

    Args:
        model_id: Model identifier (e.g., "openai/gpt-4o", "anthropic/claude-3-5-sonnet")

    Returns:
        (provider, model_pattern) tuple
    """
    if "/" in model_id:
        provider, model = model_id.split("/", 1)
        return provider, model

    # Try to infer from model name
    model_lower = model_id.lower()
    if "gpt" in model_lower:
        return "openai", model_id
    if "claude" in model_lower:
        return "anthropic", model_id
    if "gemini" in model_lower:
        return "google", model_id
    if "groq" in model_lower:
        return "groq", model_id

    # Default to the model_id as pattern
    return "unknown", model_id


def auto_detect_limits(model_id: str) -> dict[str, object]:
    """Auto-detect rate limits based on model ID.

    Args:
        model_id: Model identifier (e.g., "openai/gpt-4o")

    Returns:
        Dictionary with rpm, tpm, rpd values (None if unknown)
    """
    provider, model_pattern = extract_provider_from_model(model_id)

    # Find matching preset
    for preset in KNOWN_PROVIDER_LIMITS:
        if preset.provider == provider:
            # Check if model pattern matches
            if "*" in preset.model_pattern:
                import fnmatch

                if fnmatch.fnmatch(model_pattern, preset.model_pattern):
                    return {
                        "rpm": preset.rpm,
                        "tpm": preset.tpm,
                        "rpd": preset.rpd,
                    }
            elif preset.model_pattern.lower() in model_pattern.lower():
                return {
                    "rpm": preset.rpm,
                    "tpm": preset.tpm,
                    "rpd": preset.rpd,
                }

    # Return conservative defaults if not found
    return {"rpm": 100, "tpm": 10000, "rpd": None}


def suggest_limits(model_id: str, use_tier: str = "tier1") -> dict[str, int | None]:
    """Suggest rate limits based on provider and tier.

    Args:
        model_id: Model identifier
        use_tier: Tier level (tier1, tier2, tier3, enterprise)

    Returns:
        Dictionary with suggested limits
    """
    base = auto_detect_limits(model_id)

    # Tier multipliers
    tier_multipliers = {
        "tier1": 1.0,
        "tier2": 2.0,
        "tier3": 5.0,
        "enterprise": 10.0,
    }

    multiplier = tier_multipliers.get(use_tier, 1.0)

    return {
        "rpm": int(base["rpm"] * multiplier) if base["rpm"] else None,  # type: ignore[operator]
        "tpm": int(base["tpm"] * multiplier) if base["tpm"] else None,  # type: ignore[operator]
        "rpd": None,  # Daily limits typically don't scale with tier
    }


__all__ = [
    "ProviderRateLimits",
    "auto_detect_limits",
    "extract_provider_from_model",
    "suggest_limits",
    "KNOWN_PROVIDER_LIMITS",
]
