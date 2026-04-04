"""CanaryTokens — per-session canary tokens for injection detection."""

from __future__ import annotations

import secrets


class CanaryTokens:
    """Per-session canary tokens for injection detection.

    Each call to ``generate()`` returns a cryptographically unique token.
    These tokens can be embedded in prompts to detect prompt injection
    attempts that echo back the canary.

    Example:
        >>> token1 = CanaryTokens.generate()
        >>> token2 = CanaryTokens.generate()
        >>> assert token1 != token2
        >>> assert len(token1) >= 16
    """

    @staticmethod
    def generate() -> str:
        """Generate a unique canary token.

        Returns a cryptographically random hex string of at least 16 characters.
        Every call produces a different value.

        Returns:
            A unique hex canary token string (32 hex chars = 16 bytes of entropy).
        """
        return secrets.token_hex(16)
