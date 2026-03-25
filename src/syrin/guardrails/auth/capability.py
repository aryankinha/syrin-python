"""Capability tokens for authority-based permissions.

Capability tokens provide consumable, time-bound permissions that can be
issued to users or agents. Each use of the token consumes its budget.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CapabilityToken:
    """A consumable capability token.

    Tokens represent permissions that can be used a limited number of times.
    They automatically expire after their TTL and can be scoped to specific
    actions or resources.

    Example:
        >>> token = CapabilityToken(
        ...     scope="finance:transfer",
        ...     budget=100,
        ...     ttl=3600
        ... )
        >>> token.can("finance:transfer")
        True
        >>> token.consume(1)
        True
        >>> token.budget
        99
    """

    scope: str
    """Permission scope (e.g., 'finance:transfer', 'documents:read')."""

    budget: int = 1
    """Number of uses remaining."""

    ttl: int | None = None
    """Time to live in seconds."""

    token_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    """Unique token identifier."""

    created_at: datetime = field(default_factory=datetime.now)
    """When the token was created."""

    issued_to: str | None = None
    """User or agent this token was issued to."""

    metadata: dict[str, object] = field(default_factory=dict)
    """Additional metadata."""

    def consume(self, amount: int = 1) -> bool:
        """Consume budget from the token.

        Args:
            amount: Amount to consume.

        Returns:
            True if consumption succeeded, False if insufficient budget.
        """
        if self.budget < amount:
            return False

        self.budget -= amount
        return True

    def is_expired(self) -> bool:
        """Check if token has expired.

        Returns:
            True if token has expired.
        """
        if self.ttl is None:
            return False

        elapsed = (datetime.now() - self.created_at).total_seconds()
        return elapsed > self.ttl

    def is_valid(self) -> bool:
        """Check if token is valid (not expired and has budget).

        Returns:
            True if token can be used.
        """
        return not self.is_expired() and self.budget > 0

    def can(self, action: str) -> bool:
        """Check if token allows a specific action.

        Supports wildcard scopes (e.g., 'finance:*' matches 'finance:transfer').

        Args:
            action: Action to check.

        Returns:
            True if token permits the action.
        """
        if not self.is_valid():
            return False

        # Exact match
        if self.scope == action:
            return True

        # Wildcard match
        if self.scope.endswith(":*"):
            prefix = self.scope[:-1]  # Remove the *
            return action.startswith(prefix)

        return False

    def to_dict(self) -> dict[str, object]:
        """Convert token to dictionary for serialization.

        Returns:
            Dictionary representation of the token.
        """
        return {
            "token_id": self.token_id,
            "scope": self.scope,
            "budget": self.budget,
            "ttl": self.ttl,
            "created_at": self.created_at.isoformat(),
            "issued_to": self.issued_to,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> CapabilityToken:
        """Create token from dictionary.

        Args:
            data: Dictionary with token data.

        Returns:
            Restored CapabilityToken.
        """
        return cls(
            token_id=data["token_id"],  # type: ignore[arg-type]
            scope=data["scope"],  # type: ignore[arg-type]
            budget=data["budget"],  # type: ignore[arg-type]
            ttl=data.get("ttl"),  # type: ignore[arg-type]
            created_at=datetime.fromisoformat(data["created_at"]),  # type: ignore[arg-type]
            issued_to=data.get("issued_to"),  # type: ignore[arg-type]
            metadata=data.get("metadata", {}),  # type: ignore[arg-type]
        )


class CapabilityIssuer:
    """Issues and manages capability tokens.

    Example:
        >>> issuer = CapabilityIssuer()
        >>> token = issuer.issue(
        ...     scope="finance:transfer",
        ...     budget=10,
        ...     issued_to="user123"
        ... )
    """

    def __init__(self) -> None:
        """Initialize capability issuer."""
        self._tokens: dict[str, CapabilityToken] = {}

    def issue(
        self,
        scope: str,
        budget: int = 1,
        ttl: int | None = None,
        issued_to: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> CapabilityToken:
        """Issue a new capability token.

        Args:
            scope: Permission scope.
            budget: Number of uses allowed.
            ttl: Time to live in seconds.
            issued_to: Recipient of the token.
            metadata: Additional metadata.

        Returns:
            New capability token.
        """
        token = CapabilityToken(
            scope=scope,
            budget=budget,
            ttl=ttl,
            issued_to=issued_to,
            metadata=metadata or {},
        )

        self._tokens[token.token_id] = token
        return token

    def revoke(self, token_id: str) -> bool:
        """Revoke a token.

        Args:
            token_id: Token to revoke.

        Returns:
            True if token was found and revoked.
        """
        if token_id in self._tokens:
            del self._tokens[token_id]
            return True
        return False

    def get(self, token_id: str) -> CapabilityToken | None:
        """Get a token by ID.

        Args:
            token_id: Token ID.

        Returns:
            Token if found, None otherwise.
        """
        return self._tokens.get(token_id)

    def validate(self, token_id: str, action: str) -> tuple[bool, str]:
        """Validate a token for a specific action.

        Args:
            token_id: Token ID.
            action: Action to validate.

        Returns:
            Tuple of (is_valid, reason).
        """
        token = self._tokens.get(token_id)

        if token is None:
            return False, "Token not found"

        if token.is_expired():
            return False, "Token expired"

        if token.budget <= 0:
            return False, "Token budget exhausted"

        if not token.can(action):
            return False, f"Token scope '{token.scope}' does not allow '{action}'"

        return True, "Valid"
