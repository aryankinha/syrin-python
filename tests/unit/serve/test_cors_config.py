"""Tests for CORSConfig dataclass."""

from __future__ import annotations

from syrin.serve import CORSConfig, ServeConfig


def test_cors_config_defaults() -> None:
    """CORSConfig has sensible defaults."""
    config = CORSConfig()
    assert config.origins == []
    assert config.allow_credentials is False
    assert config.allow_methods == ["*"]
    assert config.allow_headers == ["*"]


def test_cors_config_origins() -> None:
    """CORSConfig accepts origins list."""
    config = CORSConfig(origins=["https://myapp.com", "https://api.myapp.com"])
    assert config.origins == ["https://myapp.com", "https://api.myapp.com"]


def test_cors_config_allow_credentials() -> None:
    """CORSConfig accepts allow_credentials."""
    config = CORSConfig(origins=["https://myapp.com"], allow_credentials=True)
    assert config.allow_credentials is True


def test_cors_config_allow_methods() -> None:
    """CORSConfig accepts allow_methods."""
    config = CORSConfig(
        origins=["https://myapp.com"],
        allow_methods=["GET", "POST"],
    )
    assert config.allow_methods == ["GET", "POST"]


def test_cors_config_allow_headers() -> None:
    """CORSConfig accepts allow_headers."""
    config = CORSConfig(
        origins=["https://myapp.com"],
        allow_headers=["Authorization", "Content-Type"],
    )
    assert config.allow_headers == ["Authorization", "Content-Type"]


def test_serve_config_accepts_cors_config() -> None:
    """ServeConfig accepts CORSConfig for cors."""
    cors = CORSConfig(origins=["https://myapp.com"])
    config = ServeConfig(cors=cors)
    assert config.cors is cors


def test_cors_config_expose_headers() -> None:
    """CORSConfig accepts expose_headers."""
    config = CORSConfig(
        origins=["https://myapp.com"],
        expose_headers=["X-Request-ID"],
    )
    assert config.expose_headers == ["X-Request-ID"]
