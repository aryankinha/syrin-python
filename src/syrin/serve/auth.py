"""Auth middleware for agent serving."""

from __future__ import annotations

from typing import Any, Protocol


class AuthMiddleware(Protocol):
    """Protocol for auth middleware. Implement authenticate() for custom auth."""

    def authenticate(self, request: Any) -> str | None:
        """Validate request and return identity on success, None on failure.

        Args:
            request: Request-like object with headers (e.g. Starlette Request).

        Returns:
            Identity string (e.g. user id, token) on success; None on auth failure.
        """
        ...


class BearerTokenAuth:
    """Bearer token auth. Validates Authorization: Bearer <token> header."""

    def __init__(self, token: str) -> None:
        """Create BearerTokenAuth.

        Args:
            token: Expected Bearer token. Request must have Authorization: Bearer <token>.
        """
        self._token = token

    def authenticate(self, request: Any) -> str | None:
        """Validate Bearer token. Returns token as identity on match, None otherwise."""
        headers = getattr(request, "headers", None)
        if headers is None:
            return None
        auth = headers.get("Authorization") or headers.get("authorization")
        if not auth or not isinstance(auth, str):
            return None
        if not auth.startswith("Bearer ") and not auth.startswith("bearer "):
            return None
        value = auth[7:].strip()
        if not value or value != self._token:
            return None
        return self._token
