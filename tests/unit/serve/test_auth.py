"""Tests for AuthMiddleware protocol and BearerTokenAuth."""

from __future__ import annotations

from dataclasses import dataclass

from syrin.serve.auth import BearerTokenAuth
from syrin.serve.config import ServeConfig


@dataclass
class MockRequest:
    """Minimal request-like object for testing auth."""

    headers: dict[str, str]


def test_bearer_token_auth_valid_token() -> None:
    """BearerTokenAuth returns identity when token matches."""
    auth = BearerTokenAuth(token="secret-123")
    request = MockRequest(headers={"Authorization": "Bearer secret-123"})
    identity = auth.authenticate(request)
    assert identity == "secret-123"


def test_bearer_token_auth_wrong_token_returns_none() -> None:
    """BearerTokenAuth returns None when token does not match."""
    auth = BearerTokenAuth(token="secret-123")
    request = MockRequest(headers={"Authorization": "Bearer wrong-token"})
    identity = auth.authenticate(request)
    assert identity is None


def test_bearer_token_auth_missing_header_returns_none() -> None:
    """BearerTokenAuth returns None when Authorization header is missing."""
    auth = BearerTokenAuth(token="secret-123")
    request = MockRequest(headers={})
    identity = auth.authenticate(request)
    assert identity is None


def test_bearer_token_auth_invalid_format_returns_none() -> None:
    """BearerTokenAuth returns None when Authorization is not Bearer format."""
    auth = BearerTokenAuth(token="secret-123")
    request = MockRequest(headers={"Authorization": "Basic dXNlcjpwYXNz"})
    identity = auth.authenticate(request)
    assert identity is None


def test_bearer_token_auth_empty_bearer_returns_none() -> None:
    """BearerTokenAuth returns None when Bearer has no token."""
    auth = BearerTokenAuth(token="secret-123")
    request = MockRequest(headers={"Authorization": "Bearer "})
    identity = auth.authenticate(request)
    assert identity is None


def test_bearer_token_auth_case_insensitive_header() -> None:
    """BearerTokenAuth accepts authorization header (case-insensitive)."""
    auth = BearerTokenAuth(token="secret-123")
    request = MockRequest(headers={"authorization": "Bearer secret-123"})
    identity = auth.authenticate(request)
    assert identity == "secret-123"


def test_bearer_token_auth_headers_dict_like() -> None:
    """BearerTokenAuth works with headers dict (e.g. request.headers)."""
    auth = BearerTokenAuth(token="secret-123")
    request = MockRequest(headers={"Authorization": "Bearer secret-123"})
    identity = auth.authenticate(request)
    assert identity == "secret-123"


def test_serve_config_accepts_bearer_token_auth() -> None:
    """ServeConfig accepts BearerTokenAuth for auth."""
    auth = BearerTokenAuth(token="my-token")
    config = ServeConfig(auth=auth)
    assert config.auth is auth


def test_bearer_token_auth_empty_token_rejects() -> None:
    """BearerTokenAuth with empty token still validates format."""
    auth = BearerTokenAuth(token="")
    request = MockRequest(headers={"Authorization": "Bearer "})
    identity = auth.authenticate(request)
    assert identity is None
