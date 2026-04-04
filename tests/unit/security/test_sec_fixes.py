"""Tests for SEC bug fixes — Phase 7 TDD."""

from __future__ import annotations

import time

from syrin.security.cache import SecretCache
from syrin.security.canary import CanaryTokens
from syrin.security.delimiter import DelimiterFactory
from syrin.security.export import SafeExporter

# ---------------------------------------------------------------------------
# SEC-01: Unique canary tokens per session
# ---------------------------------------------------------------------------


def test_canary_tokens_generate_returns_different_values() -> None:
    """CanaryTokens.generate() called twice returns different values."""
    t1 = CanaryTokens.generate()
    t2 = CanaryTokens.generate()
    assert t1 != t2


def test_canary_tokens_generate_returns_min_16_chars() -> None:
    """CanaryTokens.generate() returns a string of at least 16 characters."""
    token = CanaryTokens.generate()
    assert isinstance(token, str)
    assert len(token) >= 16


# ---------------------------------------------------------------------------
# SEC-02: Secret cache TTL
# ---------------------------------------------------------------------------


def test_secret_cache_is_expired_returns_true_after_ttl() -> None:
    """SecretCache(ttl_seconds=0.001) — is_expired() returns True after sleep."""
    cache = SecretCache(ttl_seconds=0.001)
    cache.set("key", "secret")
    time.sleep(0.01)
    assert cache.is_expired("key") is True


def test_secret_cache_get_returns_none_after_ttl() -> None:
    """SecretCache.get('key') returns None after TTL expires."""
    cache = SecretCache(ttl_seconds=0.001)
    cache.set("key", "secret")
    time.sleep(0.01)
    assert cache.get("key") is None


def test_secret_cache_get_returns_value_before_ttl() -> None:
    """SecretCache.get('key') returns value before TTL expires."""
    cache = SecretCache(ttl_seconds=10.0)
    cache.set("key", "my_secret")
    assert cache.get("key") == "my_secret"


# ---------------------------------------------------------------------------
# SEC-03: PII stripped from export
# ---------------------------------------------------------------------------


def test_safe_exporter_redacts_ssn_field() -> None:
    """SafeExporter.export({'ssn': '123-45-6789', 'name': 'Alice'}) → 'ssn' value replaced with '[REDACTED]'."""
    result = SafeExporter.export({"ssn": "123-45-6789", "name": "Alice"})
    assert result["ssn"] == "[REDACTED]"


def test_safe_exporter_does_not_strip_non_pii_fields() -> None:
    """SafeExporter does not strip non-PII fields."""
    result = SafeExporter.export({"ssn": "123-45-6789", "name": "Alice"})
    assert result["name"] == "Alice"


def test_safe_exporter_redacts_all_pii_field_names() -> None:
    """All known PII field names are redacted by SafeExporter."""
    data = {
        "ssn": "123-45-6789",
        "social_security": "xxx",
        "credit_card": "4532015112830366",
        "cc_number": "4532015112830366",
        "password": "hunter2",
        "secret": "top-secret",
        "token": "abcdef",
        "safe_field": "keep me",
    }
    result = SafeExporter.export(data)
    for pii_field in [
        "ssn",
        "social_security",
        "credit_card",
        "cc_number",
        "password",
        "secret",
        "token",
    ]:
        assert result[pii_field] == "[REDACTED]", f"{pii_field} should be redacted"
    assert result["safe_field"] == "keep me"


def test_safe_exporter_returns_copy_not_mutate() -> None:
    """SafeExporter.export returns a copy; original dict is not mutated."""
    original = {"ssn": "123-45-6789", "name": "Alice"}
    result = SafeExporter.export(original)
    assert original["ssn"] == "123-45-6789"  # original unchanged
    assert result["ssn"] == "[REDACTED]"


# ---------------------------------------------------------------------------
# SEC-04: Unpredictable delimiters
# ---------------------------------------------------------------------------


def test_delimiter_factory_make_differs_on_two_calls() -> None:
    """DelimiterFactory.make() returns string with random component (test two calls differ)."""
    d1 = DelimiterFactory.make()
    d2 = DelimiterFactory.make()
    assert d1 != d2


def test_delimiter_factory_make_returns_non_empty_string() -> None:
    """DelimiterFactory.make() returns non-empty string."""
    d = DelimiterFactory.make()
    assert isinstance(d, str)
    assert len(d) > 0


def test_delimiter_factory_make_with_prefix_includes_prefix() -> None:
    """DelimiterFactory.make(prefix='<<') includes the prefix."""
    d = DelimiterFactory.make(prefix="<<")
    assert d.startswith("<<")


def test_delimiter_factory_make_default_prefix() -> None:
    """DelimiterFactory.make() uses default '##' prefix."""
    d = DelimiterFactory.make()
    assert d.startswith("##")
